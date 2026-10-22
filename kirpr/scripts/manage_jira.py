#!/usr/bin/env python3
"""Create, update and delete a single Jira issue via REST API v2.

Usage:
  manage_jira.py [--dry-run] create --project PROJ --summary "..." --type Task
  manage_jira.py [--dry-run] update PROJ-201 --status "In Progress"
  manage_jira.py [--dry-run] delete PROJ-201 --confirm PROJ-201

Requires JIRA_URL and JIRA_TOKEN. JIRA_EMAIL marks a Jira Cloud deployment
and switches authentication to basic auth.
"""

import argparse
import base64
import difflib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


class ArgError(ValueError):
    """Raised when CLI arguments are missing or inconsistent."""


class ApiError(RuntimeError):
    """Raised when the Jira API rejects a request."""


def _urllib_transport(method, url, headers, data):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def explain_http(status: int, method: str, path: str, raw: bytes) -> str:
    text = raw.decode("utf-8", "replace") if raw else ""
    if status in (401, 403):
        hint = " Проверь JIRA_TOKEN, JIRA_EMAIL и права пользователя."
    elif status == 404:
        hint = " Задача или проект не найден."
    elif status == 400 and method == "DELETE":
        hint = " Возможно, у задачи есть подзадачи — добавь --delete-subtasks."
    else:
        hint = ""
    return f"Jira API {method} {path} -> HTTP {status}: {text}{hint}"


class JiraClient:
    def __init__(self, base_url: str, token: str, email=None, transport=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email or None
        self._transport = transport or _urllib_transport

    @property
    def is_cloud(self) -> bool:
        return bool(self.email)

    def _auth_header(self) -> str:
        if self.is_cloud:
            raw = f"{self.email}:{self.token}".encode("utf-8")
            return f"Basic {base64.b64encode(raw).decode('ascii')}"
        return f"Bearer {self.token}"

    def _request(self, method: str, path: str, body=None):
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8") if body is not None else None
        status, raw = self._transport(method, url, headers, data)
        if status >= 400:
            raise ApiError(explain_http(status, method, path, raw))
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def list_transitions(self, key: str):
        data = self._request("GET", f"/rest/api/2/issue/{key}/transitions")
        return (data or {}).get("transitions") or []

    def do_transition(self, key: str, transition_id: str) -> None:
        self._request("POST", f"/rest/api/2/issue/{key}/transitions",
                      {"transition": {"id": transition_id}})

    def search_user(self, query: str):
        encoded = urllib.parse.quote(query)
        data = self._request(
            "GET", f"/rest/api/2/user/search?query={encoded}")
        return data or []

    def fetch_issue(self, key: str) -> dict:
        fields = ("summary,description,status,assignee,priority,labels,"
                  "duedate")
        return self._request(
            "GET", f"/rest/api/2/issue/{key}?fields={fields}") or {}

    def fetch_project(self, key: str) -> dict:
        return self._request("GET", f"/rest/api/2/project/{key}") or {}

    def create_issue(self, fields: dict) -> str:
        data = self._request("POST", "/rest/api/2/issue", {"fields": fields})
        key = (data or {}).get("key")
        if not key:
            raise ApiError(f"Задача создана, но key не вернулся: {data!r}")
        return key

    def update_issue(self, key: str, fields: dict) -> None:
        self._request("PUT", f"/rest/api/2/issue/{key}", {"fields": fields})

    def add_comment(self, key: str, body: str) -> None:
        self._request("POST", f"/rest/api/2/issue/{key}/comment",
                      {"body": body})

    def fetch_delete_preview(self, key: str) -> dict:
        fields = "summary,reporter,comment,subtasks,issuelinks"
        return self._request(
            "GET", f"/rest/api/2/issue/{key}?fields={fields}") or {}

    def delete_issue(self, key: str, delete_subtasks: bool) -> None:
        flag = "true" if delete_subtasks else "false"
        self._request(
            "DELETE", f"/rest/api/2/issue/{key}?deleteSubtasks={flag}")


def resolve_description(args):
    inline = getattr(args, "description", None)
    path = getattr(args, "description_file", None)
    if inline is not None and path is not None:
        raise ArgError("--description и --description-file взаимоисключающие.")
    if path is not None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            raise ArgError(f"Не читается --description-file: {e}")
    return inline


def validate_update(args) -> None:
    changes = [
        args.summary,
        args.description,
        args.description_file,
        args.status,
        args.assignee,
        args.priority,
        args.labels,
        args.duedate,
        args.comment,
    ]
    if not any(c is not None for c in changes):
        raise ArgError(
            "update требует хотя бы один из флагов: --summary, --description, "
            "--description-file, --status, --assignee, --priority, --labels, "
            "--duedate, --comment."
        )


def validate_delete(args) -> None:
    if not args.confirm:
        raise ArgError(
            f"delete требует --confirm {args.issue}. Удаление необратимо."
        )
    if args.confirm != args.issue:
        raise ArgError(
            f"--confirm {args.confirm!r} не совпадает с задачей {args.issue!r}."
        )


def parse_labels(value: str):
    return [item.strip() for item in value.split(",") if item.strip()]


UNASSIGN = "-1"


def find_transition(transitions, target_status: str):
    wanted = (target_status or "").strip().lower()
    for transition in transitions:
        name = ((transition.get("to") or {}).get("name") or "").strip().lower()
        if name == wanted:
            return transition
    available = sorted({
        (t.get("to") or {}).get("name")
        for t in transitions
        if (t.get("to") or {}).get("name")
    })
    listed = ", ".join(available) if available else "—"
    raise ArgError(
        f"Из текущего статуса нет перехода в {target_status!r}. "
        f"Доступны: {listed}."
    )


def resolve_assignee(client, value: str):
    if value == UNASSIGN:
        return None
    if not client.is_cloud:
        return {"name": value}
    users = client.search_user(value)
    if not users:
        raise ArgError(f"Пользователь {value!r} не найден в Jira.")
    if len(users) > 1:
        names = ", ".join(
            u.get("displayName") or u.get("emailAddress") or u.get("accountId")
            or "?" for u in users
        )
        raise ArgError(
            f"Запрос {value!r} совпал с несколькими пользователями: {names}. "
            "Уточни запрос."
        )
    account_id = users[0].get("accountId")
    if not account_id:
        raise ArgError(f"У пользователя {value!r} нет accountId.")
    return {"accountId": account_id}


def build_fields(args, client, description, for_create: bool) -> dict:
    fields = {}
    if for_create:
        fields["project"] = {"key": args.project}
        fields["summary"] = args.summary
        fields["issuetype"] = {"name": args.type}
        if args.parent:
            fields["parent"] = {"key": args.parent}
    elif args.summary is not None:
        fields["summary"] = args.summary
    if description is not None:
        fields["description"] = description
    if args.priority is not None:
        fields["priority"] = {"name": args.priority}
    if args.labels is not None:
        fields["labels"] = parse_labels(args.labels)
    if getattr(args, "duedate", None) is not None:
        fields["duedate"] = args.duedate
    if args.assignee is not None:
        fields["assignee"] = resolve_assignee(client, args.assignee)
    return fields


def render_description_diff(old, new):
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    return [line for line in difflib.ndiff(old_lines, new_lines)
            if not line.startswith("? ")]


DRY_RUN_FOOTER = "_dry-run: сетевых записей не выполнено._"


def _comment_section(comment):
    if not comment:
        return []
    return ["## Комментарий", "", comment, ""]


def render_dry_run_create(args, description):
    lines = ["# Dry-run: создание задачи", ""]
    lines.append(f"**Проект:** {args.project}")
    lines.append(f"**Тип:** {args.type}")
    lines.append(f"**Заголовок:** {args.summary}")
    if args.parent:
        lines.append(f"**Родитель:** {args.parent}")
    for label, value in (("Статус", args.status), ("Исполнитель", args.assignee),
                         ("Приоритет", args.priority), ("Метки", args.labels)):
        if value is not None:
            lines.append(f"**{label}:** {value}")
    lines.append("")
    if description:
        lines.extend(["## Описание", "", description, ""])
    lines.extend(_comment_section(args.comment))
    lines.append(DRY_RUN_FOOTER)
    return "\n".join(lines)


def render_dry_run_update(current, changes, description_diff, comment):
    key = current.get("key") or "?"
    fields = current.get("fields") or {}
    lines = [f"# Dry-run: обновление {key}", ""]
    lines.append(f"**Задача:** {fields.get('summary') or '—'}")
    lines.append("")
    if changes:
        lines.append("| поле | было | станет |")
        lines.append("|------|------|--------|")
        for name, before, after in changes:
            lines.append(f"| {name} | {before} | {after} |")
        lines.append("")
    if description_diff is not None:
        lines.append("## Описание")
        lines.append("")
        lines.extend(description_diff)
        lines.append("")
    lines.extend(_comment_section(comment))
    lines.append(DRY_RUN_FOOTER)
    return "\n".join(lines)


def render_delete_preview(preview):
    key = preview.get("key") or "?"
    fields = preview.get("fields") or {}
    reporter = fields.get("reporter") or {}
    author = reporter.get("displayName") or reporter.get("name") or "—"
    comments = ((fields.get("comment") or {}).get("comments")) or []
    subtasks = fields.get("subtasks") or []
    links = fields.get("issuelinks") or []
    lines = [f"# Dry-run: удаление {key}", ""]
    lines.append(f"**Задача:** {fields.get('summary') or '—'}")
    lines.append(f"**Автор:** {author}")
    lines.append(f"**Комментариев:** {len(comments)}")
    lines.append("")
    if subtasks:
        lines.append("## Подзадачи")
        lines.append("")
        for sub in subtasks:
            lines.append(f"- {sub.get('key') or '?'}")
        lines.append("")
        lines.append("Без `--delete-subtasks` Jira откажет в удалении.")
        lines.append("")
    if links:
        lines.append("## Связи")
        lines.append("")
        for link in links:
            name = (link.get("type") or {}).get("name") or "link"
            other = link.get("outwardIssue") or link.get("inwardIssue") or {}
            lines.append(f"- {name}: {other.get('key') or '?'}")
        lines.append("")
    lines.append("**Удаление необратимо:** задача исчезнет вместе с "
                 "комментариями, связями и историей.")
    lines.append("")
    lines.append(DRY_RUN_FOOTER)
    return "\n".join(lines)


def render_report(title, applied, failed):
    lines = [f"# {title}", ""]
    if applied:
        lines.append("## Выполнено")
        lines.append("")
        for item in applied:
            lines.append(f"- {item}")
    else:
        lines.append("_ничего не выполнено_")
    if failed:
        lines.append("")
        lines.append("## Прервано")
        lines.append("")
        lines.append(failed)
        lines.append("")
        lines.append("_Откат не выполняется. Повторный запуск безопасен._")
    return "\n".join(lines)


def apply_steps(steps):
    applied = []
    for label, action in steps:
        try:
            action()
        except (ApiError, ArgError) as e:
            return applied, f"{label}: {e}"
        applied.append(label)
    return applied, None


def build_parser():
    parser = argparse.ArgumentParser(
        description="Создание, обновление и удаление задачи в Jira."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Предпросмотр; без сетевых записей.")
    sub = parser.add_subparsers(dest="action", required=True)

    create = sub.add_parser("create", help="Создать задачу.")
    create.add_argument("--project", required=True, help="Ключ проекта.")
    create.add_argument("--summary", required=True)
    create.add_argument("--type", required=True, help="Тип задачи, например Task.")
    create.add_argument("--description")
    create.add_argument("--description-file")
    create.add_argument("--parent")
    create.add_argument("--status")
    create.add_argument("--assignee")
    create.add_argument("--priority")
    create.add_argument("--labels", help="Через запятую; заменяет набор целиком.")
    create.add_argument("--comment")

    update = sub.add_parser("update", help="Обновить задачу.")
    update.add_argument("issue")
    update.add_argument("--summary")
    update.add_argument("--description")
    update.add_argument("--description-file")
    update.add_argument("--status")
    update.add_argument("--assignee", help="Логин или имя; -1 снимает исполнителя.")
    update.add_argument("--priority")
    update.add_argument("--labels", help="Через запятую; заменяет набор целиком.")
    update.add_argument("--duedate", help="Дата в формате YYYY-MM-DD.")
    update.add_argument("--comment")

    delete = sub.add_parser("delete", help="Удалить задачу безвозвратно.")
    delete.add_argument("issue")
    delete.add_argument("--confirm", help="Ключ задачи, введённый повторно.")
    delete.add_argument("--delete-subtasks", action="store_true")

    return parser


def make_client():
    from kirpr_fixture_transport import FIXTURE_BASE_URL, FIXTURE_TOKEN, transport_from_env
    transport = transport_from_env()
    if transport is not None:
        return JiraClient(FIXTURE_BASE_URL, FIXTURE_TOKEN, email=None, transport=transport)
    base_url = os.environ.get("JIRA_URL")
    token = os.environ.get("JIRA_TOKEN")
    if not base_url or not token:
        raise ArgError("JIRA_URL и JIRA_TOKEN должны быть заданы.")
    return JiraClient(base_url, token, email=os.environ.get("JIRA_EMAIL"))


def _current_value(fields: dict, name: str) -> str:
    value = fields.get(name)
    if value is None:
        return "—"
    if isinstance(value, dict):
        return (value.get("name") or value.get("displayName")
                or value.get("key") or "—")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "—"
    return str(value)


def collect_changes(current, args, client):
    fields = current.get("fields") or {}
    changes = []
    if args.summary is not None:
        changes.append(("summary", _current_value(fields, "summary"),
                        args.summary))
    if args.status is not None:
        find_transition(client.list_transitions(current.get("key")),
                        args.status)
        changes.append(("status", _current_value(fields, "status"),
                        args.status))
    if args.assignee is not None:
        after = "—" if args.assignee == UNASSIGN else args.assignee
        changes.append(("assignee", _current_value(fields, "assignee"), after))
    if args.priority is not None:
        changes.append(("priority", _current_value(fields, "priority"),
                        args.priority))
    if args.labels is not None:
        after = ", ".join(parse_labels(args.labels)) or "—"
        changes.append(("labels", _current_value(fields, "labels"), after))
    if getattr(args, "duedate", None) is not None:
        changes.append(("duedate", _current_value(fields, "duedate"),
                        args.duedate))
    return changes


def _status_step(client, key, status):
    def action():
        transition = find_transition(client.list_transitions(key), status)
        client.do_transition(key, transition["id"])

    return (f"статус переведён в `{status}`", action)


def run_create(args, client, dry_run):
    description = resolve_description(args)
    if dry_run:
        # Ранняя проверка проекта: опечатка в --project должна вскрыться
        # до подтверждения, а не после.
        client.fetch_project(args.project)
        return render_dry_run_create(args, description), 0
    fields = build_fields(args, client, description, for_create=True)
    key = client.create_issue(fields)
    steps = []
    if args.status is not None:
        steps.append(_status_step(client, key, args.status))
    if args.comment is not None:
        steps.append(("добавлен комментарий",
                      lambda: client.add_comment(key, args.comment)))
    applied, failed = apply_steps(steps)
    applied.insert(0, f"создана задача {key}")
    return render_report(f"Задача {key} создана", applied, failed), \
        (1 if failed else 0)


def run_update(args, client, dry_run):
    validate_update(args)
    description = resolve_description(args)
    current = client.fetch_issue(args.issue)
    current.setdefault("key", args.issue)
    if dry_run:
        changes = collect_changes(current, args, client)
        diff = None
        if description is not None:
            diff = render_description_diff(
                (current.get("fields") or {}).get("description"), description)
        return render_dry_run_update(current, changes, diff, args.comment), 0
    fields = build_fields(args, client, description, for_create=False)
    steps = []
    if fields:
        label = f"обновлены поля: {', '.join(sorted(fields))}"
        steps.append((label, lambda: client.update_issue(args.issue, fields)))
    if args.status is not None:
        steps.append(_status_step(client, args.issue, args.status))
    if args.comment is not None:
        steps.append(("добавлен комментарий",
                      lambda: client.add_comment(args.issue, args.comment)))
    applied, failed = apply_steps(steps)
    return render_report(f"Задача {args.issue} обновлена", applied, failed), \
        (1 if failed else 0)


def run_delete(args, client, dry_run):
    if dry_run:
        preview = client.fetch_delete_preview(args.issue)
        preview.setdefault("key", args.issue)
        return render_delete_preview(preview), 0
    validate_delete(args)
    client.delete_issue(args.issue, args.delete_subtasks)
    return render_report(f"Задача {args.issue} удалена",
                         [f"удалена задача {args.issue}"], None), 0


def run(args, client=None):
    if client is None:
        client = make_client()
    if args.action == "create":
        return run_create(args, client, args.dry_run)
    if args.action == "update":
        return run_update(args, client, args.dry_run)
    if args.action == "delete":
        return run_delete(args, client, args.dry_run)
    raise ArgError(f"Неизвестное действие: {args.action}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output, code = run(args)
    except (ArgError, ApiError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
