#!/usr/bin/env python3
"""kirpr project memory: workspace map and per-repository memory files.

The only writer of `.kirpr/workspace.md` and `.kirpr/memory.md`.
Commands: refresh, lesson add|amend, lint, stale. Every command accepts --dry-run.
Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

SECTIONS = ("## Как проверять", "## Ловушки", "## Уроки")
LESSONS_SECTION = SECTIONS[2]
MAX_LINES = 150
MAX_BYTES = 15360

LESSON_RE = re.compile(
    r"^- \[L-(?P<number>\d{3})\] (?P<text>.+?) "
    r"\((?P<task>[A-Z][A-Z0-9_]+-\d+); (?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:; refs: (?P<refs>[^)]+))?\)$"
)


@dataclass
class Lesson:
    number: int
    text: str
    task: str
    date: str
    refs: list[str] = field(default_factory=list)


@dataclass
class Memory:
    title: str
    sections: dict[str, list[str]]
    lessons: list[Lesson]


def parse_lesson(line: str) -> Lesson | None:
    m = LESSON_RE.match(line)
    if not m:
        return None
    refs = [r.strip() for r in m.group("refs").split(",")] if m.group("refs") else []
    return Lesson(int(m.group("number")), m.group("text"), m.group("task"), m.group("date"), refs)


def format_lesson(lesson: Lesson) -> str:
    meta = f"{lesson.task}; {lesson.date}"
    if lesson.refs:
        meta += "; refs: " + ", ".join(lesson.refs)
    return f"- [L-{lesson.number:03d}] {lesson.text} ({meta})"


def _is_heading(line: str, in_code: bool) -> bool:
    return line.startswith("## ") and not in_code


def parse_memory(text: str) -> Memory:
    title = ""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if line.startswith("# ") and not title and current is None:
            title = line[2:].strip()
            continue
        if _is_heading(line, in_code):
            current = line.rstrip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    lessons = []
    for line in sections.get(LESSONS_SECTION, []):
        lesson = parse_lesson(line)
        if lesson is not None:
            lessons.append(lesson)
    return Memory(title, sections, lessons)


def lint_memory(text: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        errors.append(f"превышен бюджет: {len(lines)} строк из {MAX_LINES}")
    size = len(text.encode("utf-8"))
    if size > MAX_BYTES:
        errors.append(f"превышен бюджет: {size} байт из {MAX_BYTES}")
    headings = []
    in_code = False
    for l in lines:
        if l.lstrip().startswith("```"):
            in_code = not in_code
        if _is_heading(l, in_code):
            headings.append(l.rstrip())
    for name in SECTIONS:
        if name not in headings:
            errors.append(f"нет секции `{name}`")
    present = [h for h in headings if h in SECTIONS]
    if present != [s for s in SECTIONS if s in present]:
        errors.append("нарушен порядок секций: " + ", ".join(present))
    seen: set[int] = set()
    in_lessons = False
    in_code = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if _is_heading(line, in_code):
            in_lessons = line.rstrip() == LESSONS_SECTION
            continue
        if not in_lessons or not line.strip():
            continue
        lesson = parse_lesson(line)
        if lesson is None:
            errors.append(f"строка {i}: не соответствует формату урока")
            m = re.match(r"^- \[L-(\d{3})\]", line)
            lesson_number = int(m.group(1)) if m else None
        else:
            lesson_number = lesson.number
        if lesson_number is not None:
            if lesson_number in seen:
                errors.append(f"L-{lesson_number:03d}: дублирующийся id")
            seen.add(lesson_number)
    return errors


def write_atomic(path: Path, text: str) -> None:
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=".kirpr-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
    return " ".join(cleaned.split())


def find_duplicate(lessons: list[Lesson], text: str, refs: list[str]) -> Lesson | None:
    wanted = normalize(text)
    wanted_refs = set(refs)
    for lesson in lessons:
        if normalize(lesson.text) == wanted or (wanted_refs & set(lesson.refs)):
            return lesson
    return None


MISSING = "memory.md не найден: {path} — создайте его командой `init` или запустите kirpr-onboard"


def _read(path: Path) -> tuple[str | None, str]:
    path = Path(path)
    if not path.is_file():
        return None, MISSING.format(path=path)
    return path.read_text(encoding="utf-8"), ""


def _lessons_span(lines: list[str]) -> tuple[int, int] | None:
    """Return (start, end) line indexes of the «Уроки» section body, or None."""
    start = None
    in_code = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if _is_heading(line, in_code):
            if start is not None:
                return start, i
            if line.rstrip() == LESSONS_SECTION:
                start = i + 1
    return (start, len(lines)) if start is not None else None


def _validate_and_write(path: Path, new_text: str, dry_run: bool) -> list[str]:
    errors = lint_memory(new_text)
    if errors:
        return errors
    if not dry_run:
        write_atomic(Path(path), new_text)
    return []


def add_lesson(path: Path, text: str, task: str, refs: list[str], today_str: str, dry_run: bool) -> tuple[int, str]:
    original, err = _read(path)
    if original is None:
        return 1, err
    errors = lint_memory(original)
    if errors:
        return 1, "файл памяти не прошёл проверку:\n" + "\n".join(errors)
    mem = parse_memory(original)
    number = max((l.number for l in mem.lessons), default=0) + 1
    line = format_lesson(Lesson(number, text, task, today_str, list(refs)))
    if parse_lesson(line) is None or "\n" in line:
        return 1, f"значения не укладываются в формат урока: {line!r}"
    dup = find_duplicate(mem.lessons, text, refs)
    if dup is not None:
        return 2, f"похоже на L-{dup.number:03d} — уточните его: `lesson amend L-{dup.number:03d}`\n  {format_lesson(dup)}"
    lines = original.split("\n")
    span = _lessons_span(lines)
    start, end = span
    insert_at = end
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, line)
    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    errors = _validate_and_write(path, new_text, dry_run)
    if errors:
        return 1, "запись отменена, файл не прошёл бы проверку:\n" + "\n".join(errors)
    prefix = "[dry-run] " if dry_run else ""
    return 0, f"{prefix}добавить в {path}:\n  {line}"


def amend_lesson(path: Path, number: int, text: str, today_str: str, dry_run: bool) -> tuple[int, str]:
    original, err = _read(path)
    if original is None:
        return 1, err
    errors = lint_memory(original)
    if errors:
        return 1, "файл памяти не прошёл проверку:\n" + "\n".join(errors)
    lines = original.split("\n")
    start, end = _lessons_span(lines)
    for i in range(start, end):
        target = parse_lesson(lines[i])
        if target is not None and target.number == number:
            break
    else:
        return 1, f"L-{number:03d} не найден в {path}"
    new_line = format_lesson(Lesson(target.number, text, target.task, today_str, list(target.refs)))
    if parse_lesson(new_line) is None or "\n" in new_line:
        return 1, f"значения не укладываются в формат урока: {new_line!r}"
    lines[i] = new_line
    errors = _validate_and_write(path, "\n".join(lines), dry_run)
    if errors:
        return 1, "запись отменена, файл не прошёл бы проверку:\n" + "\n".join(errors)
    prefix = "[dry-run] " if dry_run else ""
    return 0, f"{prefix}уточнить L-{number:03d} в {path}:\n  было: {format_lesson(target)}\n  станет: {new_line}"


def _parse_lesson_id(value: str) -> int:
    m = re.fullmatch(r"L-(\d{3})", value)
    if not m:
        raise argparse.ArgumentTypeError("ожидается id вида L-NNN")
    return int(m.group(1))


def cmd_lesson(args: argparse.Namespace) -> int:
    if args.action == "add":
        refs = [r.strip() for r in args.refs.split(",") if r.strip()] if args.refs else []
        code, report = add_lesson(Path(args.file), args.text, args.task, refs, args.date or today(), args.dry_run)
    else:
        code, report = amend_lesson(Path(args.file), args.id, args.text, args.date or today(), args.dry_run)
    print(report)
    return code


def stale_refs(path: Path, repo_root: Path) -> list[tuple[Lesson, str]]:
    mem = parse_memory(Path(path).read_text(encoding="utf-8"))
    missing = []
    for lesson in mem.lessons:
        for ref in lesson.refs:
            if not (Path(repo_root) / ref).exists():
                missing.append((lesson, ref))
    return missing


def cmd_stale(args: argparse.Namespace) -> int:
    file = Path(args.file).resolve()
    if not file.is_file():
        print(MISSING.format(path=file))
        return 1
    repo = Path(args.repo).resolve() if args.repo else file.parent.parent
    result = stale_refs(file, repo)
    for lesson, ref in result:
        print(f"⚠ stale L-{lesson.number:03d}: {ref}")
    print(f"{len(result)} устаревших ссылок")
    return 0


@dataclass
class Service:
    name: str
    path: str
    branch: str
    tracker: str
    role: str = ""
    status: str = ""


STATUS_RE = re.compile(r"^(?P<name>.+?) \((?P<status>новый|не найден)\)$")
TRACKER_RE = re.compile(r"^([A-Z][A-Z0-9]+)-\d+")
_SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = (
    _SCRIPT_DIR.parent / "config"
    if (_SCRIPT_DIR.parent / "config" / "workspace.md.template").exists()
    else Path.home() / ".local" / "share" / "kirpr" / "config"
)


def _git(repo: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def _default_branch(repo: Path) -> str:
    ref = _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ref.startswith("refs/remotes/origin/"):
        return ref[len("refs/remotes/origin/"):]
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return "" if branch == "HEAD" else branch


def _tracker_prefix(repo: Path) -> str:
    counts: dict[str, int] = {}
    for subject in _git(repo, "log", "-50", "--format=%s").splitlines():
        m = TRACKER_RE.match(subject)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    if not counts:
        return ""
    return max(sorted(counts), key=lambda k: counts[k])


def scan_workspace(root: Path) -> list[Service]:
    root = Path(root)
    services = []
    for child in sorted(root.iterdir(), key=lambda c: c.name):
        if child.is_dir() and (child / ".git").exists():
            services.append(Service(child.name, f"./{child.name}", _default_branch(child), _tracker_prefix(child)))
    return services


def parse_workspace(text: str) -> list[Service]:
    services = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 5 or cells[0] == "Сервис" or all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        cells = cells[:4] + [" | ".join(cells[4:])]
        name, status = cells[0], ""
        m = STATUS_RE.match(name)
        if m:
            name, status = m.group("name"), m.group("status")
        services.append(Service(name, cells[1], cells[2], cells[3], cells[4], status))
    return services


def merge_services(scanned: list[Service], existing: list[Service]) -> list[Service]:
    by_name = {s.name: s for s in existing}
    merged = []
    for s in scanned:
        old = by_name.pop(s.name, None)
        if old is None:
            merged.append(Service(s.name, s.path, s.branch, s.tracker, "", "новый"))
        else:
            merged.append(Service(s.name, s.path, old.branch or s.branch, s.tracker or old.tracker, old.role, ""))
    for old in by_name.values():
        merged.append(Service(old.name, old.path, old.branch, old.tracker, old.role, "не найден"))
    return merged


def _template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def render_workspace(name: str, services: list[Service], today_str: str) -> str:
    rows = []
    for s in services:
        label = f"{s.name} ({s.status})" if s.status else s.name
        rows.append(f"| {label} | {s.path} | {s.branch} | {s.tracker} | {s.role} |")
    return _template("workspace.md.template").format(name=name, rows="\n".join(rows), today=today_str)


def refresh_workspace(workspace: Path, today_str: str, dry_run: bool) -> tuple[int, str]:
    workspace = Path(workspace).resolve()
    target = workspace / ".kirpr" / "workspace.md"
    scanned = scan_workspace(workspace)
    existing = parse_workspace(target.read_text(encoding="utf-8")) if target.exists() else []
    if not scanned and not target.exists():
        return 1, "сервисы не найдены: в каталоге нет подкаталогов с .git"
    services = merge_services(scanned, existing) if target.exists() else scanned
    text = render_workspace(workspace.name, services, today_str)
    prefix = "[dry-run] " if dry_run else ""
    report = f"{prefix}{target}:\n{text}"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, text)
    return 0, report


def init_memory(path: Path, name: str, check: list[str], traps: list[str], dry_run: bool) -> tuple[int, str]:
    path = Path(path)
    if path.exists():
        return 1, f"{path} уже существует — секции дополняются через правку файла после `lint`, уроки — через `lesson add`"
    bullets = lambda items: "\n".join(f"- {i}" for i in items)
    text = _template("memory.md.template").format(name=name, check=bullets(check), traps=bullets(traps))
    text = re.sub(r"\n{3,}", "\n\n", text)
    errors = lint_memory(text)
    if errors:
        return 1, "шаблон не прошёл проверку:\n" + "\n".join(errors)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(path, text)
    prefix = "[dry-run] " if dry_run else ""
    return 0, f"{prefix}{path}:\n{text}"


def cmd_init(args: argparse.Namespace) -> int:
    code, report = init_memory(Path(args.file), args.name, args.check or [], args.traps or [], args.dry_run)
    print(report)
    return code


def set_role(workspace: Path, service: str, role: str, today_str: str, dry_run: bool) -> tuple[int, str]:
    target = Path(workspace).resolve() / ".kirpr" / "workspace.md"
    if not target.is_file():
        return 1, f"{target} не найден — сначала `refresh`"
    services = parse_workspace(target.read_text(encoding="utf-8"))
    match = next((s for s in services if s.name == service), None)
    if match is None:
        return 1, f"сервис {service} не найден в {target}"
    match.role = role
    text = render_workspace(target.parent.parent.name, services, today_str)
    if not dry_run:
        write_atomic(target, text)
    prefix = "[dry-run] " if dry_run else ""
    return 0, f"{prefix}{service}: роль «{role}»"


def cmd_role(args: argparse.Namespace) -> int:
    code, report = set_role(Path(args.workspace or os.getcwd()), args.service, args.role, args.date or today(), args.dry_run)
    print(report)
    return code


def cmd_refresh(args: argparse.Namespace) -> int:
    code, report = refresh_workspace(Path(args.workspace or os.getcwd()), args.date or today(), args.dry_run)
    print(report)
    return code


def cmd_lint(args: argparse.Namespace) -> int:
    text, err = _read(args.file)
    if text is None:
        print(err)
        return 1
    errors = lint_memory(text)
    if errors:
        print("\n".join(errors))
        return 1
    print("ok")
    return 0


def today() -> str:
    return _dt.date.today().isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="kirpr project memory")
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="Проверить memory.md.")
    lint.add_argument("--file", required=True)
    lint.add_argument("--dry-run", action="store_true", help="Принимается для единообразия; lint ничего не пишет.")
    lint.set_defaults(func=cmd_lint)

    lesson = sub.add_parser("lesson", help="Уроки: add | amend.")
    lsub = lesson.add_subparsers(dest="action", required=True)
    add = lsub.add_parser("add", help="Добавить урок.")
    add.add_argument("--file", required=True)
    add.add_argument("--text", required=True)
    add.add_argument("--task", required=True)
    add.add_argument("--refs", default="")
    add.add_argument("--date")
    add.add_argument("--dry-run", action="store_true")
    add.set_defaults(func=cmd_lesson)
    amend = lsub.add_parser("amend", help="Уточнить урок.")
    amend.add_argument("id", type=_parse_lesson_id)
    amend.add_argument("--file", required=True)
    amend.add_argument("--text", required=True)
    amend.add_argument("--date")
    amend.add_argument("--dry-run", action="store_true")
    amend.set_defaults(func=cmd_lesson)
    stale = sub.add_parser("stale", help="Проверить, что refs уроков существуют.")
    stale.add_argument("--file", required=True)
    stale.add_argument("--repo")
    stale.add_argument("--dry-run", action="store_true", help="Принимается для единообразия; stale ничего не пишет.")
    stale.set_defaults(func=cmd_stale)
    refresh = sub.add_parser("refresh", help="Пересобрать карту рабочего пространства.")
    refresh.add_argument("--workspace")
    refresh.add_argument("--date")
    refresh.add_argument("--dry-run", action="store_true")
    refresh.set_defaults(func=cmd_refresh)
    role = sub.add_parser("role", help="Задать роль сервиса в workspace.md.")
    role.add_argument("--workspace")
    role.add_argument("--service", required=True)
    role.add_argument("--role", required=True)
    role.add_argument("--date")
    role.add_argument("--dry-run", action="store_true")
    role.set_defaults(func=cmd_role)
    init = sub.add_parser("init", help="Создать memory.md из шаблона.")
    init.add_argument("--file", required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--check", action="append", help="Строка секции «Как проверять» (повторяемый).")
    init.add_argument("--traps", action="append", help="Строка секции «Ловушки» (повторяемый).")
    init.add_argument("--dry-run", action="store_true")
    init.set_defaults(func=cmd_init)
    return parser


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
