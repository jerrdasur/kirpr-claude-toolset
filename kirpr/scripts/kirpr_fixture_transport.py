#!/usr/bin/env python3
"""Fixture transport for kirpr tracker scripts (behavior evals).

When EVAL_KIRPR_FIXTURES=<dir> is set, tracker scripts read issues from
<dir>/<ISSUE>.json and log writes to <dir>/requests.log instead of calling the
network. Without the variable nothing changes. Stdlib only.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path
from typing import Callable, Mapping

ENV_VAR = "EVAL_KIRPR_FIXTURES"
FIXTURE_BASE_URL = "https://fixtures.invalid"
FIXTURE_TOKEN = "fixture"
NOT_FOUND = b'{"error":"not found"}'
ISSUE_PATH = re.compile(r"/(?:issues|issue)/([A-Z][A-Z0-9_]+-\d+)(?:/([\w-]+))?/?$")

Transport = Callable[[str, str, dict, "bytes | None"], "tuple[int, bytes]"]


def fixture_transport(base_dir: Path) -> Transport:
    base_dir = Path(base_dir)

    def transport(method: str, url: str, headers: dict, data):
        path = urllib.parse.urlsplit(url).path
        if method.upper() != "GET":
            body = data.decode("utf-8") if data else ""
            with open(base_dir / "requests.log", "a", encoding="utf-8") as log:
                log.write(f"{method.upper()} {path} {body}\n")
            return 200, b"{}"
        m = ISSUE_PATH.search(path)
        if not m:
            return 404, NOT_FOUND
        key, sub = m.group(1), m.group(2)
        if sub:
            file = base_dir / f"{key}.{sub}.json"
            return (200, file.read_bytes()) if file.is_file() else (200, b"[]")
        file = base_dir / f"{key}.json"
        return (200, file.read_bytes()) if file.is_file() else (404, NOT_FOUND)

    return transport


def transport_from_env(environ: Mapping[str, str] = os.environ) -> Transport | None:
    value = environ.get(ENV_VAR)
    if not value:
        return None
    directory = Path(value)
    if not directory.is_absolute():
        # Агент может перейти в подкаталог (например, в репозиторий сервиса):
        # относительный путь ищется от cwd вверх, до корня файловой системы.
        cwd = Path.cwd()
        found = next((base / directory for base in (cwd, *cwd.parents) if (base / directory).is_dir()), None)
        directory = found or cwd / directory
    if not directory.is_dir():
        raise SystemExit(f"{ENV_VAR}: каталог не найден: {directory}")
    return fixture_transport(directory)
