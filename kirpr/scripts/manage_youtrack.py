#!/usr/bin/env python3
"""Create, update and delete a single YouTrack issue.

Usage:
  manage_youtrack.py [--dry-run] create --project SAS --summary "..."
  manage_youtrack.py [--dry-run] update SAS-201 --command "State In Progress"
  manage_youtrack.py [--dry-run] delete SAS-201 --confirm SAS-201

Requires YOUTRACK_URL and YOUTRACK_TOKEN environment variables.
"""

import argparse
import difflib
import json
import os
import sys
import urllib.error
import urllib.request


class ArgError(ValueError):
    """Raised when CLI arguments are missing or inconsistent."""


class ApiError(RuntimeError):
    """Raised when the YouTrack API rejects a request."""


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
        hint = " Проверь YOUTRACK_TOKEN и права пользователя."
    elif status == 404:
        hint = " Задача или проект не найден."
    else:
        hint = ""
    return f"YouTrack API {method} {path} -> HTTP {status}: {text}{hint}"


class YouTrackClient:
    def __init__(self, base_url: str, token: str, transport=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._transport = transport or _urllib_transport

    def _request(self, method: str, path: str, body=None):
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8") if body is not None else None
        status, raw = self._transport(method, url, headers, data)
        if status >= 400:
            raise ApiError(explain_http(status, method, path, raw))
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def resolve_project_id(self, short_name: str) -> str:
        data = self._request("GET", "/api/admin/projects?fields=id,shortName")
        for project in data or []:
            if project.get("shortName") == short_name:
                return project["id"]
        known = ", ".join(p.get("shortName") or "?" for p in data or [])
        raise ArgError(f"Проект {short_name!r} не найден. Доступны: {known}.")

    def resolve_project_id_from_issue(self, issue_id: str) -> str:
        data = self._request(
            "GET", f"/api/issues/{issue_id}?fields=project(id,shortName)")
        project_id = ((data or {}).get("project") or {}).get("id")
        if not project_id:
            raise ApiError(f"Не удалось определить проект задачи {issue_id}.")
        return project_id

    def create_issue(self, project_id: str, summary: str,
                     description: str) -> str:
        body = {"project": {"id": project_id}, "summary": summary,
                "description": description}
        data = self._request("POST", "/api/issues?fields=idReadable,id", body)
        issue_id = (data or {}).get("idReadable")
        if not issue_id:
            raise ApiError(f"Задача создана, но idReadable не вернулся: {data!r}")
        return issue_id

    def run_command(self, issue_id: str, query: str) -> None:
        body = {"query": query, "issues": [{"idReadable": issue_id}]}
        self._request("POST", "/api/commands", body)

    def add_comment(self, issue_id: str, text: str) -> None:
        self._request("POST", f"/api/issues/{issue_id}/comments", {"text": text})

    def fetch_issue(self, issue_id: str) -> dict:
        fields = "idReadable,summary,description"
        return self._request(
            "GET", f"/api/issues/{issue_id}?fields={fields}") or {}

    def update_issue(self, issue_id: str, fields: dict) -> None:
        self._request("POST", f"/api/issues/{issue_id}", fields)

    def fetch_delete_preview(self, issue_id: str) -> dict:
        fields = ("idReadable,summary,reporter(login,name),comments(id),"
                  "links(linkType(name),direction,issues(idReadable))")
        return self._request(
            "GET", f"/api/issues/{issue_id}?fields={fields}") or {}

    def delete_issue(self, issue_id: str) -> None:
        self._request("DELETE", f"/api/issues/{issue_id}")


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
        args.command,
        args.comment,
    ]
    if not any(c is not None and c != [] for c in changes):
        raise ArgError(
            "update требует хотя бы один из флагов: --summary, --description, "
            "--description-file, --command, --comment."
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


def render_description_diff(old, new):
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    diff = difflib.ndiff(old_lines, new_lines)
    return [line for line in diff if not line.startswith("? ")]


DRY_RUN_FOOTER = "_dry-run: сетевых записей не выполнено._"


def _commands_section(commands):
    if not commands:
        return []
    lines = ["## Команды", ""]
    for query in commands:
        lines.append(f"- `{query}`")
    lines.append("")
    return lines


def _comment_section(comment):
    if not comment:
        return []
    return ["## Комментарий", "", comment, ""]


def render_dry_run_create(project, summary, description, parent, commands,
                          comment):
    lines = ["# Dry-run: создание задачи", ""]
    lines.append(f"**Проект:** {project}")
    lines.append(f"**Заголовок:** {summary}")
    if parent:
        lines.append(f"**Родитель:** subtask of {parent}")
    lines.append("")
    if description:
        lines.extend(["## Описание", "", description, ""])
    lines.extend(_commands_section(commands))
    lines.extend(_comment_section(comment))
    lines.append(DRY_RUN_FOOTER)
    return "\n".join(lines)


def render_dry_run_update(current, summary, description, commands, comment):
    issue_id = current.get("idReadable") or "?"
    lines = [f"# Dry-run: обновление {issue_id}", ""]
    lines.append(f"**Задача:** {current.get('summary') or '—'}")
    lines.append("")
    if summary:
        lines.append("| поле | было | станет |")
        lines.append("|------|------|--------|")
        lines.append(f"| summary | {current.get('summary') or '—'} | {summary} |")
        lines.append("")
    if description is not None:
        lines.append("## Описание")
        lines.append("")
        lines.extend(render_description_diff(current.get("description"),
                                             description))
        lines.append("")
    lines.extend(_commands_section(commands))
    lines.extend(_comment_section(comment))
    lines.append(DRY_RUN_FOOTER)
    return "\n".join(lines)


def render_delete_preview(preview):
    issue_id = preview.get("idReadable") or "?"
    reporter = preview.get("reporter") or {}
    author = reporter.get("name") or reporter.get("login") or "—"
    comments = preview.get("comments") or []
    links = preview.get("links") or []
    lines = [f"# Dry-run: удаление {issue_id}", ""]
    lines.append(f"**Задача:** {preview.get('summary') or '—'}")
    lines.append(f"**Автор:** {author}")
    lines.append(f"**Комментариев:** {len(comments)}")
    lines.append("")
    related = []
    for link in links:
        name = (link.get("linkType") or {}).get("name") or "link"
        for issue in link.get("issues") or []:
            if issue.get("idReadable"):
                related.append(f"- {name}: {issue['idReadable']}")
    if related:
        lines.append("## Связи")
        lines.append("")
        lines.extend(related)
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
        except ApiError as e:
            return applied, f"{label}: {e}"
        applied.append(label)
    return applied, None


def build_parser():
    parser = argparse.ArgumentParser(
        description="Создание, обновление и удаление задачи в YouTrack."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Предпросмотр; без сетевых записей.")
    sub = parser.add_subparsers(dest="action", required=True)

    create = sub.add_parser("create", help="Создать задачу.")
    create.add_argument("--project", required=True, help="Короткое имя проекта.")
    create.add_argument("--summary", required=True)
    create.add_argument("--description")
    create.add_argument("--description-file")
    create.add_argument("--parent", help="Задача-родитель (subtask of).")
    create.add_argument("--command", action="append", default=[],
                        help="Команда YouTrack, можно повторять.")
    create.add_argument("--comment")

    update = sub.add_parser("update", help="Обновить задачу.")
    update.add_argument("issue")
    update.add_argument("--summary")
    update.add_argument("--description")
    update.add_argument("--description-file")
    update.add_argument("--command", action="append", default=[])
    update.add_argument("--comment")

    delete = sub.add_parser("delete", help="Удалить задачу безвозвратно.")
    delete.add_argument("issue")
    delete.add_argument("--confirm", help="Номер задачи, введённый повторно.")

    return parser


def make_client():
    base_url = os.environ.get("YOUTRACK_URL")
    token = os.environ.get("YOUTRACK_TOKEN")
    if not base_url or not token:
        raise ArgError("YOUTRACK_URL и YOUTRACK_TOKEN должны быть заданы.")
    return YouTrackClient(base_url, token)


def _resolve_create_project(args, client):
    try:
        return client.resolve_project_id(args.project)
    except ApiError:
        if not args.parent:
            raise
        return client.resolve_project_id_from_issue(args.parent)


def run_create(args, client, dry_run):
    description = resolve_description(args)
    project_id = _resolve_create_project(args, client)
    if dry_run:
        return render_dry_run_create(args.project, args.summary, description,
                                     args.parent, args.command,
                                     args.comment), 0
    issue_id = client.create_issue(project_id, args.summary, description or "")
    steps = []
    for query in args.command:
        steps.append((f"выполнена команда `{query}`",
                      lambda q=query: client.run_command(issue_id, q)))
    if args.parent:
        parent_query = f"subtask of {args.parent}"
        steps.append((f"проставлена связь `{parent_query}`",
                      lambda: client.run_command(issue_id, parent_query)))
    if args.comment is not None:
        steps.append(("добавлен комментарий",
                      lambda: client.add_comment(issue_id, args.comment)))
    applied, failed = apply_steps(steps)
    applied.insert(0, f"создана задача {issue_id}")
    return render_report(f"Задача {issue_id} создана", applied, failed), \
        (1 if failed else 0)


def run_update(args, client, dry_run):
    validate_update(args)
    description = resolve_description(args)
    current = client.fetch_issue(args.issue)
    if dry_run:
        return render_dry_run_update(current, args.summary, description,
                                     args.command, args.comment), 0
    fields = {}
    if args.summary is not None:
        fields["summary"] = args.summary
    if description is not None:
        fields["description"] = description
    steps = []
    if fields:
        label = f"обновлены поля: {', '.join(sorted(fields))}"
        steps.append((label, lambda: client.update_issue(args.issue, fields)))
    for query in args.command:
        steps.append((f"выполнена команда `{query}`",
                      lambda q=query: client.run_command(args.issue, q)))
    if args.comment is not None:
        steps.append(("добавлен комментарий",
                      lambda: client.add_comment(args.issue, args.comment)))
    applied, failed = apply_steps(steps)
    return render_report(f"Задача {args.issue} обновлена", applied, failed), \
        (1 if failed else 0)


def run_delete(args, client, dry_run):
    if dry_run:
        return render_delete_preview(client.fetch_delete_preview(args.issue)), 0
    validate_delete(args)
    client.delete_issue(args.issue)
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
