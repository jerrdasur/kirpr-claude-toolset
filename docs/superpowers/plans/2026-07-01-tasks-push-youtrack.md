# tasks-push (create YouTrack tasks with dependencies) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a script + slash-command that takes a decomposition directory (`sas-200/`) and creates the subtasks in YouTrack, wiring parent hierarchy and dependency links.

**Architecture:** Mirror the existing fetch two-layer pattern in reverse. A dumb, deterministic Python script (`create_youtrack.py`, stdlib only) consumes a structured `create-plan.json` and calls the YouTrack API to create issues and links, writing a `.created.json` mapping for idempotency. An LLM command (`/kirpr:tasks-push`) reads the decomposition markdown, builds the plan JSON, previews via `--dry-run`, confirms, then invokes the script.

**Tech Stack:** Python 3 stdlib only (`urllib`, `json`, `argparse`), `unittest` for tests. Markdown command prompt for the LLM layer.

## Global Constraints

- **Python stdlib only** — no external dependencies (matches `fetch_youtrack.py`). Copied verbatim from spec.
- **Env vars** — `YOUTRACK_URL`, `YOUTRACK_TOKEN` (same as fetch).
- **File naming** — script names English, code comments/messages may be Russian or English matching neighboring scripts; command file content in Russian (matches other `commands/kirpr/*.md`).
- **Fields on created issues** — `Summary` + `Description` only. No Estimation/Assignee/inheritance.
- **Links** — hierarchy (`Subtask` from parent) + dependencies (`Depend` from graph). Nothing else.
- **Tracker scope** — YouTrack only. Jira is out of scope.
- **Safety** — `--dry-run` preview + `.created.json` mapping make re-runs idempotent; real creation only after explicit user confirmation in the command.
- **Tests** live in top-level `tests/` (NOT copied by `install.sh`); run with `python3 tests/test_create_youtrack.py -v`.

---

### Task 1: Plan loading and validation (pure logic)

**Files:**
- Create: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `class PlanError(ValueError)`
  - `load_plan(path: str) -> dict` — read file, `json.loads`, raise `PlanError` on bad JSON.
  - `validate_plan(plan: dict) -> None` — raise `PlanError` if: `parent` missing/empty; `tasks` not a non-empty list; any task missing `key`/`summary`/`description`; duplicate `key`; any edge `from`/`to` referencing an unknown key; graph has a cycle.
  - `detect_cycle(keys: list[str], edges: list[dict]) -> list[str] | None` — return a cycle as a list of keys, or `None` if acyclic.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_create_youtrack.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import create_youtrack as cy  # noqa: E402


def make_plan(**over):
    plan = {
        "tracker": "youtrack",
        "parent": "SAS-200",
        "tasks": [
            {"key": "01-schema", "summary": "Schema", "description": "body A"},
            {"key": "02-model", "summary": "Model", "description": "body B"},
        ],
        "edges": [{"from": "01-schema", "to": "02-model"}],
    }
    plan.update(over)
    return plan


class TestValidatePlan(unittest.TestCase):
    def test_valid_plan_passes(self):
        cy.validate_plan(make_plan())  # no raise

    def test_missing_parent_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(parent=""))

    def test_empty_tasks_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=[]))

    def test_task_missing_field_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=[{"key": "x", "summary": "y"}]))

    def test_duplicate_key_raises(self):
        dup = [
            {"key": "a", "summary": "s", "description": "d"},
            {"key": "a", "summary": "s", "description": "d"},
        ]
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=dup, edges=[]))

    def test_edge_unknown_key_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=[{"from": "01-schema", "to": "ghost"}]))

    def test_cycle_raises(self):
        edges = [
            {"from": "01-schema", "to": "02-model"},
            {"from": "02-model", "to": "01-schema"},
        ]
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=edges))


class TestDetectCycle(unittest.TestCase):
    def test_acyclic_returns_none(self):
        self.assertIsNone(cy.detect_cycle(["a", "b"], [{"from": "a", "to": "b"}]))

    def test_cycle_returns_path(self):
        cyc = cy.detect_cycle(["a", "b"], [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
        self.assertIsNotNone(cyc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'create_youtrack'` (file does not exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `kirpr/scripts/create_youtrack.py`:

```python
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
    if not plan.get("parent"):
        raise PlanError("Plan is missing a non-empty 'parent'.")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise PlanError("Plan 'tasks' must be a non-empty list.")
    keys = []
    for t in tasks:
        for field in ("key", "summary", "description"):
            if not t.get(field):
                raise PlanError(f"Task is missing '{field}': {t!r}")
        if t["key"] in keys:
            raise PlanError(f"Duplicate task key: {t['key']}")
        keys.append(t["key"])
    edges = plan.get("edges") or []
    keyset = set(keys)
    for e in edges:
        for field in ("from", "to"):
            if e.get(field) not in keyset:
                raise PlanError(f"Edge references unknown key '{e.get(field)}': {e!r}")
    cycle = detect_cycle(keys, edges)
    if cycle:
        raise PlanError(f"Dependency graph has a cycle: {' -> '.join(cycle)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): plan loading and validation for tasks-push"
```

---

### Task 2: Dry-run and report rendering (pure logic)

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: `validate_plan` (Task 1).
- Produces:
  - `render_dry_run(plan: dict, existing: dict) -> str` — markdown preview. `existing` is a `key -> idReadable` mapping of already-created tasks. Lists tasks that WOULD be created (skipping those in `existing`), the parent-subtask links, and the dependency links.
  - `render_report(plan: dict, mapping: dict, created_links: list[str]) -> str` — final markdown: table `key -> id`, list of links applied, totals.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_create_youtrack.py` (before the `if __name__` block):

```python
class TestRenderDryRun(unittest.TestCase):
    def test_lists_new_tasks_and_links(self):
        out = cy.render_dry_run(make_plan(), existing={})
        self.assertIn("01-schema", out)
        self.assertIn("02-model", out)
        self.assertIn("SAS-200", out)          # parent hierarchy mentioned
        self.assertIn("01-schema", out)         # dependency edge endpoint
        self.assertIn("dry-run", out.lower())

    def test_skips_already_created(self):
        out = cy.render_dry_run(make_plan(), existing={"01-schema": "SAS-201"})
        self.assertIn("SAS-201", out)           # shows it as existing
        self.assertIn("02-model", out)          # still to be created


class TestRenderReport(unittest.TestCase):
    def test_report_has_ids_and_totals(self):
        mapping = {"01-schema": "SAS-201", "02-model": "SAS-202"}
        out = cy.render_report(make_plan(), mapping, ["SAS-201 subtask of SAS-200"])
        self.assertIn("SAS-201", out)
        self.assertIn("SAS-202", out)
        self.assertIn("subtask of SAS-200", out)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `AttributeError: module 'create_youtrack' has no attribute 'render_dry_run'`.

- [ ] **Step 3: Write minimal implementation**

Append to `kirpr/scripts/create_youtrack.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): dry-run preview and final report rendering"
```

---

### Task 3: Mapping file I/O

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `load_mapping(path: str) -> dict` — return parsed `key -> idReadable` dict, or `{}` if file missing.
  - `save_mapping(path: str, mapping: dict) -> None` — write pretty JSON (UTF-8, `ensure_ascii=False`).

- [ ] **Step 1: Write the failing tests**

Append before `if __name__`:

```python
import tempfile  # add near the other imports at top; shown here for context


class TestMappingIO(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(cy.load_mapping("/nonexistent/path/.created.json"), {})

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".created.json")
            cy.save_mapping(p, {"01-schema": "SAS-201"})
            self.assertEqual(cy.load_mapping(p), {"01-schema": "SAS-201"})
```

Move `import tempfile` to the top import block (next to `import os`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `AttributeError: module 'create_youtrack' has no attribute 'load_mapping'`.

- [ ] **Step 3: Write minimal implementation**

Append to `kirpr/scripts/create_youtrack.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): .created.json mapping load/save"
```

---

### Task 4: YouTrackClient — request construction

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `LINK_TYPE_SUBTASK = "Subtask"`, `LINK_TYPE_DEPEND = "Depend"` (module constants).
  - `class YouTrackClient` with:
    - `__init__(self, base_url: str, token: str, transport=None)` — `transport` is a callable `(method, url, headers: dict, data: bytes | None) -> (status: int, body: bytes)`; defaults to `_urllib_transport`.
    - `resolve_project_id(self, issue_id: str) -> str` — GET the parent issue, return `project.id`.
    - `create_issue(self, project_id: str, summary: str, description: str) -> str` — POST, return `idReadable`.
    - `existing_link_targets(self, issue_id: str, link_type_name: str) -> set[str]` — GET links, return set of linked `idReadable` for that link type.
    - `add_link_command(self, source_id: str, query: str) -> None` — POST to `/api/commands` applying `query` to `source_id`.

  Link semantics used by later tasks: parent hierarchy = apply `f"subtask of {parent}"` to each child; dependency edge `from → to` = apply `f"depends on {from_id}"` to `to_id`.

- [ ] **Step 1: Write the failing tests**

Append before `if __name__`:

```python
class FakeTransport:
    """Records requests and returns canned (status, body) responses."""

    def __init__(self, responses):
        self.responses = list(responses)   # list of (status, dict-or-list)
        self.calls = []

    def __call__(self, method, url, headers, data):
        self.calls.append({"method": method, "url": url, "headers": headers, "data": data})
        status, payload = self.responses.pop(0)
        return status, json.dumps(payload).encode("utf-8")


class TestYouTrackClient(unittest.TestCase):
    def test_resolve_project_id(self):
        tr = FakeTransport([(200, {"project": {"id": "0-5", "shortName": "SAS"}})])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        self.assertEqual(c.resolve_project_id("SAS-200"), "0-5")
        self.assertEqual(tr.calls[0]["method"], "GET")
        self.assertIn("/api/issues/SAS-200", tr.calls[0]["url"])
        self.assertEqual(tr.calls[0]["headers"]["Authorization"], "Bearer tok")

    def test_create_issue_posts_body(self):
        tr = FakeTransport([(200, {"idReadable": "SAS-201"})])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        self.assertEqual(c.create_issue("0-5", "Schema", "body"), "SAS-201")
        call = tr.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertIn("/api/issues", call["url"])
        body = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(body["project"]["id"], "0-5")
        self.assertEqual(body["summary"], "Schema")
        self.assertEqual(body["description"], "body")

    def test_existing_link_targets_filters_by_type(self):
        links = [
            {"linkType": {"name": "Subtask"}, "direction": "INWARD",
             "issues": [{"idReadable": "SAS-200"}]},
            {"linkType": {"name": "Depend"}, "direction": "OUTWARD",
             "issues": [{"idReadable": "SAS-202"}]},
        ]
        tr = FakeTransport([(200, links)])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        self.assertEqual(c.existing_link_targets("SAS-201", "Subtask"), {"SAS-200"})

    def test_add_link_command_posts_query(self):
        tr = FakeTransport([(200, {})])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        c.add_link_command("SAS-201", "subtask of SAS-200")
        call = tr.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertIn("/api/commands", call["url"])
        body = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(body["query"], "subtask of SAS-200")
        self.assertEqual(body["issues"][0]["idReadable"], "SAS-201")

    def test_http_error_raises(self):
        tr = FakeTransport([(404, {"error": "Not Found"})])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        with self.assertRaises(RuntimeError):
            c.resolve_project_id("SAS-999")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `AttributeError: module 'create_youtrack' has no attribute 'YouTrackClient'`.

- [ ] **Step 3: Write minimal implementation**

Add `import urllib.request`, `import urllib.error`, and `import urllib.parse` to the top import block, then append:

```python
LINK_TYPE_SUBTASK = "Subtask"
LINK_TYPE_DEPEND = "Depend"


def _urllib_transport(method, url, headers, data):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


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
            text = raw.decode("utf-8", "replace") if raw else ""
            raise RuntimeError(f"YouTrack API {method} {path} -> HTTP {status}: {text}")
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def resolve_project_id(self, issue_id: str) -> str:
        data = self._request("GET", f"/api/issues/{issue_id}?fields=project(id,shortName)")
        project = (data or {}).get("project") or {}
        pid = project.get("id")
        if not pid:
            raise RuntimeError(f"Could not resolve project for {issue_id}")
        return pid

    def create_issue(self, project_id: str, summary: str, description: str) -> str:
        body = {"project": {"id": project_id}, "summary": summary, "description": description}
        data = self._request("POST", "/api/issues?fields=idReadable,id", body)
        issue_id = (data or {}).get("idReadable")
        if not issue_id:
            raise RuntimeError(f"Issue created but no idReadable returned: {data!r}")
        return issue_id

    def existing_link_targets(self, issue_id: str, link_type_name: str) -> set:
        fields = "linkType(name),direction,issues(idReadable)"
        data = self._request("GET", f"/api/issues/{issue_id}/links?fields={fields}") or []
        targets = set()
        for link in data:
            if (link.get("linkType") or {}).get("name") == link_type_name:
                for issue in link.get("issues") or []:
                    if issue.get("idReadable"):
                        targets.add(issue["idReadable"])
        return targets

    def add_link_command(self, source_id: str, query: str) -> None:
        body = {"query": query, "issues": [{"idReadable": source_id}]}
        self._request("POST", "/api/commands", body)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (19 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): YouTrackClient with request construction"
```

---

### Task 5: Orchestration — two-pass create + link

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: `validate_plan`, `render_dry_run`, `render_report`, `load_mapping`, `save_mapping`, `YouTrackClient`, link constants.
- Produces:
  - `run(plan_path: str, dry_run: bool, client=None, mapping_path: str | None = None) -> str` — returns the markdown output (preview or report). When `client is None`, builds a real `YouTrackClient` from env (tested separately in Task 6 via `main`). `mapping_path` defaults to `.created.json` next to `plan_path`.
  - Behavior: validate → resolve project → load mapping → **pass 1** create only tasks not already in mapping, saving mapping after each creation → **pass 2** apply `subtask of parent` to each child (skip if already linked) and `depends on {from}` to each `to` (skip if already linked), collecting a human-readable list of links applied. Dry-run stops after building the preview (no creation, no links).

- [ ] **Step 1: Write the failing tests**

Append before `if __name__`:

```python
class FakeClient:
    def __init__(self):
        self.created = []       # (project_id, summary, description)
        self.links = []         # (source_id, query)
        self.existing = {}      # (issue_id, link_type) -> set
        self._counter = 200

    def resolve_project_id(self, issue_id):
        return "0-5"

    def create_issue(self, project_id, summary, description):
        self._counter += 1
        issue_id = f"SAS-{self._counter}"
        self.created.append((project_id, summary, description))
        return issue_id

    def existing_link_targets(self, issue_id, link_type_name):
        return self.existing.get((issue_id, link_type_name), set())

    def add_link_command(self, source_id, query):
        self.links.append((source_id, query))


class TestRun(unittest.TestCase):
    def _write_plan(self, d, plan):
        p = os.path.join(d, "create-plan.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(plan))
        return p

    def test_dry_run_makes_no_writes(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            out = cy.run(p, dry_run=True, client=fc)
            self.assertIn("dry-run", out.lower())
            self.assertEqual(fc.created, [])
            self.assertEqual(fc.links, [])

    def test_full_run_creates_and_links(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            out = cy.run(p, dry_run=False, client=fc)
            # two issues created
            self.assertEqual(len(fc.created), 2)
            # mapping persisted
            mapping = cy.load_mapping(os.path.join(d, ".created.json"))
            self.assertEqual(set(mapping.keys()), {"01-schema", "02-model"})
            # subtask links for both children + one dependency link
            queries = [q for _, q in fc.links]
            self.assertTrue(any(q == "subtask of SAS-200" for q in queries))
            self.assertTrue(any(q.startswith("depends on") for q in queries))
            self.assertIn("Задачи созданы", out)

    def test_resume_skips_already_created(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            cy.save_mapping(os.path.join(d, ".created.json"), {"01-schema": "SAS-201"})
            fc = FakeClient()
            cy.run(p, dry_run=False, client=fc)
            # only the not-yet-created task is created
            self.assertEqual(len(fc.created), 1)
            self.assertEqual(fc.created[0][1], "Model")

    def test_idempotent_links_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            # pretend 01-schema already a subtask of SAS-200
            def existing(issue_id, link_type):
                if link_type == cy.LINK_TYPE_SUBTASK:
                    return {"SAS-200"}
                return set()
            fc.existing_link_targets = existing
            cy.run(p, dry_run=False, client=fc)
            # no "subtask of" command should be issued since both children already linked
            self.assertFalse(any(q == "subtask of SAS-200" for _, q in fc.links))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `AttributeError: module 'create_youtrack' has no attribute 'run'`.

- [ ] **Step 3: Write minimal implementation**

Append to `kirpr/scripts/create_youtrack.py`:

```python
import os  # ensure present in top import block


def _mapping_path_for(plan_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(plan_path)), ".created.json")


def run(plan_path: str, dry_run: bool, client=None, mapping_path=None) -> str:
    plan = load_plan(plan_path)
    validate_plan(plan)
    if mapping_path is None:
        mapping_path = _mapping_path_for(plan_path)
    mapping = load_mapping(mapping_path)

    if dry_run:
        return render_dry_run(plan, mapping)

    if client is None:
        base_url = os.environ.get("YOUTRACK_URL")
        token = os.environ.get("YOUTRACK_TOKEN")
        if not base_url or not token:
            raise RuntimeError("YOUTRACK_URL and YOUTRACK_TOKEN must be set.")
        client = YouTrackClient(base_url.rstrip("/"), token)

    parent = plan["parent"]
    project_id = client.resolve_project_id(parent)

    # Pass 1: create issues (skip already-created), persist mapping incrementally.
    for t in plan["tasks"]:
        if t["key"] in mapping:
            continue
        issue_id = client.create_issue(project_id, t["summary"], t["description"])
        mapping[t["key"]] = issue_id
        save_mapping(mapping_path, mapping)

    created_links = []

    # Pass 2a: hierarchy (each child subtask of parent).
    for t in plan["tasks"]:
        child_id = mapping[t["key"]]
        if parent in client.existing_link_targets(child_id, LINK_TYPE_SUBTASK):
            continue
        client.add_link_command(child_id, f"subtask of {parent}")
        created_links.append(f"{child_id} subtask of {parent}")

    # Pass 2b: dependencies (edge from -> to means `to depends on from`).
    for e in plan.get("edges") or []:
        from_id = mapping[e["from"]]
        to_id = mapping[e["to"]]
        if from_id in client.existing_link_targets(to_id, LINK_TYPE_DEPEND):
            continue
        client.add_link_command(to_id, f"depends on {from_id}")
        created_links.append(f"{to_id} depends on {from_id}")

    return render_report(plan, mapping, created_links)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (23 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): two-pass orchestration with idempotent create and links"
```

---

### Task 6: CLI entrypoint `main()`

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Consumes: `run`, `PlanError`.
- Produces:
  - `main(argv=None) -> int` — parse `--plan PATH` (required) and `--dry-run` (flag) via `argparse`, call `run`, print its output to stdout, return `0`. On `PlanError` or `RuntimeError`, print `Error: ...` to stderr and return `1`.
  - `if __name__ == "__main__": sys.exit(main())`.

- [ ] **Step 1: Write the failing tests**

Append before `if __name__`:

```python
import io
import contextlib


class TestMain(unittest.TestCase):
    def test_dry_run_via_main(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "create-plan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps(make_plan()))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cy.main(["--plan", p, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("dry-run", buf.getvalue().lower())

    def test_bad_plan_returns_1(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "create-plan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{ not json")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = cy.main(["--plan", p, "--dry-run"])
            self.assertEqual(rc, 1)
            self.assertIn("Error", err.getvalue())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: FAIL with `AttributeError: module 'create_youtrack' has no attribute 'main'`.

- [ ] **Step 3: Write minimal implementation**

Add `import argparse` and `import sys` to the top import block, then append:

```python
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create YouTrack issues from a decomposition plan."
    )
    parser.add_argument("--plan", required=True, help="Path to create-plan.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only; no network writes.")
    args = parser.parse_args(argv)
    try:
        output = run(args.plan, dry_run=args.dry_run)
    except (PlanError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (25 tests).

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "feat(create): CLI entrypoint with argparse and error handling"
```

---

### Task 7: The `/kirpr:tasks-push` command

**Files:**
- Create: `commands/kirpr/tasks-push.md`

**Interfaces:**
- Consumes: `create_youtrack.py` CLI (`--plan`, `--dry-run`), `~/.claude/kirpr/config/tracker.md`, the decomposition directory produced by `/kirpr:tasks-decompose`.
- Produces: created YouTrack issues (side effect); no code interface.

There is no unit test for a prompt file. Verification is manual (Task 8) plus a self-consistency read.

- [ ] **Step 1: Write the command file**

Create `commands/kirpr/tasks-push.md`:

```markdown
# Создание задач в трекере $ARGUMENTS

Ты — помощник, который берёт готовую декомпозицию задачи и создаёт подзадачи в YouTrack, проставляя иерархию и зависимости.

## Инициализация

1. Прочитай `~/.claude/kirpr/config/tracker.md` — секция `## Активный трекер`.
   - Если активный трекер **не YouTrack** — сообщи пользователю: «Команда `tasks-push` поддерживает только YouTrack» и остановись.
2. Номер задачи: **$ARGUMENTS** (например `SAS-200`). Директория декомпозиции — lowercase номер (`sas-200/`).
3. Если директории `sas-200/` нет — сообщи, что декомпозиция не найдена, предложи запустить `/kirpr:tasks-decompose $ARGUMENTS`, и остановись.

## Фаза 1: Загрузка декомпозиции

1. Прочитай `sas-200/00-overview.md` — граф зависимостей и карту файлов.
2. Прочитай все `sas-200/XX-Y-name.md` — подзадачи.
3. Из заголовка каждого файла (`## Задача X.Y — {Название} [...]`) возьми название → `summary`.
   Тело файла целиком → `description`.

## Фаза 2: Построение плана

Собери `sas-200/create-plan.json`:

- `tracker`: `"youtrack"`
- `parent`: `"$ARGUMENTS"`
- `tasks[]`: по одному объекту на файл подзадачи —
  - `key`: имя файла без расширения (например `02-1-domain-model`),
  - `summary`: название из заголовка,
  - `description`: тело файла.
- `edges[]`: рёбра из графа зависимостей в `00-overview.md`. Ребро `{"from": A, "to": B}` означает «A должна быть сделана раньше B».

Убедись, что `create-plan.json` и `.created.json` внесены в `.gitignore` проекта (это кэш-артефакты, как `.context.md`). Если нет — добавь их.

## Фаза 3: Preview (dry-run)

Запусти:

```
python3 ~/.claude/kirpr/scripts/create_youtrack.py --plan sas-200/create-plan.json --dry-run
```

Покажи пользователю вывод: таблицу создаваемых задач, связи иерархии и зависимостей. **Явно покажи граф зависимостей**, чтобы пользователь его сверил.

## Фаза 4: Подтверждение

Спроси: «Создаю N задач в проекте {PROJECT} с иерархией и зависимостями?». Предложи варианты: `да` / `нет`.

**Без явного согласия задачи не создавай.** Создание задач в трекере необратимо.

## Фаза 5: Создание

После подтверждения запусти без `--dry-run`:

```
python3 ~/.claude/kirpr/scripts/create_youtrack.py --plan sas-200/create-plan.json
```

- Если скрипт вернул ошибку — покажи её и остановись. Файл `.created.json` уже частично записан; повторный запуск досоздаст недостающее и не создаст дублей.

## Фаза 6: Отчёт

Покажи вывод скрипта: таблицу `key → созданный issue`, проставленные связи, итог. Сообщи, что маппинг сохранён в `sas-200/.created.json` и повторный вызов команды идемпотентен.

## Правила

- **Один вопрос за раз.** Не задавай несколько вопросов в одном сообщении.
- **Не создавай задачи без подтверждения пользователя.**
- **Покажи план (dry-run) перед реальным созданием.**
- **Если fetch/резолв проекта упал — прерви** и сообщи пользователю.
```

- [ ] **Step 2: Verify the command references match the script CLI**

Read the command file and confirm: script path is `~/.claude/kirpr/scripts/create_youtrack.py`, flags are `--plan` and `--dry-run`, plan path is `sas-200/create-plan.json`. These must match Task 6's `argparse` definition exactly.

- [ ] **Step 3: Commit**

```bash
git add commands/kirpr/tasks-push.md
git commit -m "feat(create): /kirpr:tasks-push command"
```

---

### Task 8: Integration — README, install verification, manual link check

**Files:**
- Modify: `README.md`
- Verify (no change expected): `install.sh`, `uninstall.sh`

**Interfaces:**
- Consumes: everything above.
- Produces: user-facing docs; confirmation that install picks up the new files.

- [ ] **Step 1: Verify install/uninstall globbing**

Run: `grep -n "scripts/\*.py\|commands/kirpr/\*.md" install.sh`
Expected: shows the two glob loops (script copy at ~line 61, command copy at ~line 35). This confirms `create_youtrack.py` and `tasks-push.md` are copied with **no install.sh change needed**. If the greps do not match, add explicit copy lines mirroring the existing loops.

- [ ] **Step 2: Add README row**

In `README.md`, in the "Декомпозиция задач" table, add a row after the `tasks-adapt` row:

```markdown
| `/kirpr:tasks-push SAS-200` | Создаёт подзадачи из декомпозиции в YouTrack: строит план → dry-run preview → подтверждение → создание с иерархией и зависимостями. Идемпотентно (`.created.json`) |
```

- [ ] **Step 3: Run the full test suite**

Run: `python3 tests/test_create_youtrack.py -v`
Expected: PASS (25 tests) — regression check that docs edits did not touch code.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(create): document /kirpr:tasks-push in README"
```

- [ ] **Step 5: Manual verification against a real YouTrack test project (REQUIRED before relying on links)**

This step is manual — it validates the one genuine unknown: the link-creation mechanism (`add_link_command` uses the YouTrack commands API with `"subtask of X"` / `"depends on X"` directed link names, which may be localized on some instances).

1. Set env vars: `export YOUTRACK_URL=...`, `export YOUTRACK_TOKEN=...`.
2. Create a throwaway plan against a real parent issue in a test project:

```bash
mkdir -p /tmp/yt-smoke/test-1
cat > /tmp/yt-smoke/test-1/create-plan.json <<'JSON'
{
  "tracker": "youtrack",
  "parent": "<REAL-PARENT-ID>",
  "tasks": [
    {"key": "a", "summary": "smoke A", "description": "test A"},
    {"key": "b", "summary": "smoke B", "description": "test B"}
  ],
  "edges": [{"from": "a", "to": "b"}]
}
JSON
python3 kirpr/scripts/create_youtrack.py --plan /tmp/yt-smoke/test-1/create-plan.json --dry-run
python3 kirpr/scripts/create_youtrack.py --plan /tmp/yt-smoke/test-1/create-plan.json
```

3. In YouTrack, confirm: both issues exist, both are subtasks of the parent, and B depends on A.
4. Re-run the create command; confirm no duplicate issues or links are created (idempotency).
5. **If the link commands are rejected** (e.g. localized link names), adjust the query strings in `YouTrackClient.add_link_command` call sites in `run()` (the `f"subtask of {parent}"` / `f"depends on {from_id}"` strings) to match the instance's directed link-type names, update the Task 4/5 tests accordingly, and re-run steps 2–4.
6. Delete the throwaway smoke issues in YouTrack.

No commit for this step unless step 5 required a code change.

---

## Notes for the implementer

- The whole `create_youtrack.py` module is built incrementally across Tasks 1–6. Each task appends to the same file; the top import block accumulates `json`, `os`, `sys`, `tempfile` (test-only), `argparse`, `urllib.request`, `urllib.error`, `urllib.parse`. Keep all imports at the top.
- The `tests/` directory is a dev artifact and is intentionally NOT copied by `install.sh` (it only globs `kirpr/scripts/*.py`, `commands/kirpr/*.md`, `kirpr/config/*.md`, `kirpr/prompts/*.md`).
- Style anchor: keep `create_youtrack.py` consistent with `fetch_youtrack.py` (stdlib, `urllib`, Bearer auth headers, plain functions + a small client class where it aids testing).
