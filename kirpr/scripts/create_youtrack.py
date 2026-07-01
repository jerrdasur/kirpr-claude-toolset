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
