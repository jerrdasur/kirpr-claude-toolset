#!/usr/bin/env python3
"""Codex smoke run for kirpr behavior evals.

For every case directory with a codex.json next to its prompt.md: install kirpr
for Codex into a temporary HOME, run the case's fixture.sh, run
`codex exec --json` with the case prompt and check the last agent message,
created files, executed commands and the tracker request log.
One run per case, no LLM judge. Stdlib only.

Usage: python3 evals/codex_smoke.py [--evals DIR] [--case NAME]
Exit codes: 0 all checks ok, 1 some check failed, 2 codex not available or no case selected.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

CHECK_KINDS = ("last_message_regex", "files_absent", "commands_absent", "requests_log_empty")
REPO = Path(__file__).resolve().parents[1]
INSTALL_INPUT = "1\nhttps://youtrack.example.invalid\n"
MESSAGE_TYPES = {"agent_message", "assistant_message", "message"}


@dataclass
class CodexCase:
    name: str
    prompt: str
    env: dict
    checks: dict
    case_dir: Path


def load_case(case_dir: Path) -> CodexCase:
    case_dir = Path(case_dir)
    data = json.loads((case_dir / "codex.json").read_text(encoding="utf-8"))
    checks = data.get("checks") or {}
    for kind, value in checks.items():
        if kind not in CHECK_KINDS:
            raise ValueError(f"неизвестная проверка: {kind}")
        if kind == "requests_log_empty":
            valid = value is True
        else:
            valid = isinstance(value, list) and bool(value) and all(isinstance(v, str) for v in value)
        if not valid:
            raise ValueError(f"{case_dir.name}: {kind}: ожидается "
                             + ("true" if kind == "requests_log_empty" else "непустой список строк"))
    if not data.get("prompt") or not checks:
        raise ValueError(f"{case_dir.name}: codex.json требует prompt и checks")
    return CodexCase(case_dir.name, data["prompt"], dict(data.get("env") or {}), checks, case_dir)


def _command_text(item: dict) -> str | None:
    command = item.get("command")
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    if isinstance(command, str):
        return command
    return None


def parse_events(jsonl: str) -> tuple[str, list[str]]:
    last_message = ""
    commands: list[str] = []
    seen: set[str] = set()
    for line in jsonl.splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict) or not str(event.get("type", "")).startswith("item."):
            continue
        item = event.get("item") or {}
        kind = item.get("type")
        if kind in MESSAGE_TYPES and event.get("type") == "item.completed":
            text = item.get("text") or item.get("content") or ""
            if isinstance(text, list):
                text = " ".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in text)
            last_message = str(text)
        command = _command_text(item)
        if command is not None:
            key = item.get("id") or command
            if key not in seen:
                seen.add(key)
                commands.append(command)
    return last_message, commands


def run_checks(case: CodexCase, last_message: str, commands: list[str], workdir: Path) -> list[tuple[str, bool, str]]:
    results = []
    checks = case.checks
    if "last_message_regex" in checks:
        missing = [p for p in checks["last_message_regex"] if not re.search(p, last_message)]
        results.append(("last_message_regex", not missing, "нет: " + ", ".join(missing) if missing else "ok"))
    if "files_absent" in checks:
        present = [p for p in checks["files_absent"] if (Path(workdir) / p).exists()]
        results.append(("files_absent", not present, "создан: " + ", ".join(present) if present else "ok"))
    if "commands_absent" in checks:
        hits = [c for c in commands for p in checks["commands_absent"] if re.search(p, c)]
        results.append(("commands_absent", not hits, "выполнено: " + "; ".join(hits) if hits else "ok"))
    if "requests_log_empty" in checks:
        log = Path(workdir) / ".eval-tracker" / "requests.log"
        text = log.read_text(encoding="utf-8").strip() if log.is_file() else ""
        results.append(("requests_log_empty", not text, text.splitlines()[0] if text else "нет записей"))
    return results


def evaluate_run(case: CodexCase, returncode: int, stdout: str, stderr: str,
                 workdir: Path) -> list[tuple[str, bool, str]]:
    """Checks only count when codex itself ran: a failed or silent run is a failure."""
    if returncode != 0:
        tail = (stderr.strip().splitlines() or ["(stderr пуст)"])[-1]
        return [("run", False, f"codex exec завершился с кодом {returncode}: {tail}")]
    last_message, commands = parse_events(stdout)
    if not last_message:
        return [("run", False, "в потоке codex нет ни одного сообщения агента")]
    return run_checks(case, last_message, commands, workdir)


def _run_case(case: CodexCase, codex_home: str) -> list[tuple[str, bool, str]]:
    with tempfile.TemporaryDirectory(prefix="kirpr-codex-") as tmp:
        home = Path(tmp) / "home"
        work = Path(tmp) / "work"
        home.mkdir()
        work.mkdir()
        base_env = {**os.environ, "HOME": str(home), "TMPDIR": tmp}
        input_file = Path(tmp) / "install-input"
        input_file.write_text(INSTALL_INPUT, encoding="utf-8")
        subprocess.run([str(REPO / "install.sh"), "--target", "codex"], check=True, capture_output=True,
                       env={**base_env, "KIRPR_INSTALL_ROOT": str(home), "KIRPR_INPUT_FILE": str(input_file)})
        fixture = case.case_dir / "fixture.sh"
        if fixture.exists():
            subprocess.run(["bash", str(fixture)], cwd=work, check=True, capture_output=True, env=base_env)
        if "EVAL_KIRPR_FIXTURES" in case.env and not (work / ".eval-tracker").exists():
            shutil.copytree(REPO / "evals" / "_fixtures" / "tracker", work / ".eval-tracker")
        proc = subprocess.run(
            ["codex", "exec", "--json", "--ephemeral", "--sandbox", "workspace-write",
             "--skip-git-repo-check", "--ignore-user-config", case.prompt],
            cwd=work, capture_output=True, text=True, timeout=900,
            env={**base_env, "CODEX_HOME": codex_home, **case.env})
        return evaluate_run(case, proc.returncode, proc.stdout, proc.stderr, work)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Codex smoke run for kirpr evals")
    parser.add_argument("--evals", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--case")
    args = parser.parse_args(argv)
    if shutil.which("codex") is None:
        print("codex не найден в PATH — дымовой прогон Codex невозможен", file=sys.stderr)
        return 2
    codex_home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    case_dirs = sorted(p.parent for p in Path(args.evals).glob("*/codex.json"))
    if args.case:
        case_dirs = [p for p in case_dirs if p.name == args.case]
    if not case_dirs:
        print(f"нет кейсов с codex.json{' по имени ' + args.case if args.case else ''} в {args.evals}",
              file=sys.stderr)
        return 2
    failed = False
    print("кейс | проверка | результат | деталь")
    for case_dir in case_dirs:
        case = load_case(case_dir)
        try:
            results = _run_case(case, codex_home)
        except (subprocess.SubprocessError, OSError) as exc:
            results = [("run", False, str(exc))]
        for name, ok, detail in results:
            failed = failed or not ok
            print(f"{case.name} | {name} | {'ok' if ok else 'fail'} | {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
