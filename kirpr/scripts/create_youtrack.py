#!/usr/bin/env python3
"""Create YouTrack issues from a decomposition plan, wiring hierarchy and dependencies.

Usage: python3 scripts/create_youtrack.py --plan sas-200/create-plan.json [--dry-run]

Requires YOUTRACK_URL and YOUTRACK_TOKEN environment variables.
"""

import json


class PlanError(ValueError):
    """Raised when create-plan.json is malformed or inconsistent."""


def load_plan(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except FileNotFoundError:
        raise PlanError(f"Plan file not found: {path}")
    except json.JSONDecodeError as e:
        raise PlanError(f"Invalid JSON in {path}: {e}")


def detect_cycle(keys, edges):
    adj = {k: [] for k in keys}
    for e in edges:
        adj[e["from"]].append(e["to"])
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in keys}
    stack = []

    def dfs(node):
        color[node] = GRAY
        stack.append(node)
        for nxt in adj[node]:
            if color[nxt] == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == WHITE:
                found = dfs(nxt)
                if found:
                    return found
        color[node] = BLACK
        stack.pop()
        return None

    for k in keys:
        if color[k] == WHITE:
            found = dfs(k)
            if found:
                return found
    return None


def validate_plan(plan: dict) -> None:
    if not isinstance(plan, dict):
        raise PlanError("Plan must be a JSON object.")
    if not plan.get("parent"):
        raise PlanError("Plan is missing a non-empty 'parent'.")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise PlanError("Plan 'tasks' must be a non-empty list.")
    keys = []
    for t in tasks:
        if not isinstance(t, dict):
            raise PlanError(f"Task must be an object: {t!r}")
        for field in ("key", "summary", "description"):
            if not t.get(field):
                raise PlanError(f"Task is missing '{field}': {t!r}")
        if t["key"] in keys:
            raise PlanError(f"Duplicate task key: {t['key']}")
        keys.append(t["key"])
    edges = plan.get("edges") or []
    keyset = set(keys)
    for e in edges:
        if not isinstance(e, dict):
            raise PlanError(f"Edge must be an object: {e!r}")
        for field in ("from", "to"):
            if e.get(field) not in keyset:
                raise PlanError(f"Edge references unknown key '{e.get(field)}': {e!r}")
    cycle = detect_cycle(keys, edges)
    if cycle:
        raise PlanError(f"Dependency graph has a cycle: {' -> '.join(cycle)}")


def render_dry_run(plan: dict, existing: dict) -> str:
    parent = plan["parent"]
    lines = ["# Dry-run: план создания задач", ""]
    lines.append(f"**Родитель:** {parent}")
    lines.append("")
    lines.append("## Задачи")
    lines.append("")
    lines.append("| key | summary | статус |")
    lines.append("|-----|---------|--------|")
    for t in plan["tasks"]:
        if t["key"] in existing:
            status = f"уже создана ({existing[t['key']]})"
        else:
            status = "будет создана"
        lines.append(f"| {t['key']} | {t['summary']} | {status} |")
    lines.append("")
    lines.append("## Связи иерархии (Subtask)")
    lines.append("")
    for t in plan["tasks"]:
        lines.append(f"- {t['key']} → subtask of {parent}")
    edges = plan.get("edges") or []
    if edges:
        lines.append("")
        lines.append("## Связи зависимостей (Depend)")
        lines.append("")
        for e in edges:
            lines.append(f"- {e['to']} depends on {e['from']}")
    lines.append("")
    lines.append("_dry-run: сетевых записей не выполнено._")
    return "\n".join(lines)


def render_report(plan: dict, mapping: dict, created_links: list) -> str:
    lines = ["# Задачи созданы", ""]
    lines.append("| key | issue |")
    lines.append("|-----|-------|")
    for t in plan["tasks"]:
        lines.append(f"| {t['key']} | {mapping.get(t['key'], '—')} |")
    lines.append("")
    lines.append("## Проставленные связи")
    lines.append("")
    if created_links:
        for link in created_links:
            lines.append(f"- {link}")
    else:
        lines.append("_нет новых связей (все уже существовали)_")
    lines.append("")
    lines.append(f"**Итого:** {len(mapping)} задач, {len(created_links)} новых связей.")
    return "\n".join(lines)


def load_mapping(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_mapping(path: str, mapping: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(mapping, ensure_ascii=False, indent=2))
