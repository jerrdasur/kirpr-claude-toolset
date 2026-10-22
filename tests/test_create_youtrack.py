import json
import os
import sys
import tempfile
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

    def test_reserved_key_raises(self):
        tasks = [{"key": cy.SOLUTION_KEY, "summary": "s", "description": "d"}]
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=tasks, edges=[]))

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


class TestLoadPlan(unittest.TestCase):
    def test_bad_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "plan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{ not json")
            with self.assertRaises(cy.PlanError):
                cy.load_plan(p)

    def test_missing_file_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.load_plan("/nonexistent/dir/plan.json")


class TestValidatePlanRobustness(unittest.TestCase):
    def test_non_dict_plan_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(["not", "a", "dict"])

    def test_non_dict_task_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=["not-a-dict"], edges=[]))

    def test_non_dict_edge_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=["not-a-dict"]))


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


class TestMappingIO(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(cy.load_mapping("/nonexistent/path/.created.json"), {})

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".created.json")
            cy.save_mapping(p, {"01-schema": "SAS-201"})
            self.assertEqual(cy.load_mapping(p), {"01-schema": "SAS-201"})


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

    def test_add_comment_posts_text(self):
        tr = FakeTransport([(200, {})])
        c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
        c.add_comment("SAS-200", "hello")
        call = tr.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/issues/SAS-200/comments"))
        self.assertEqual(json.loads(call["data"]), {"text": "hello"})

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


class FakeClient:
    def __init__(self):
        self.created = []       # (project_id, summary, description)
        self.links = []         # (source_id, query)
        self.existing = {}      # (issue_id, link_type) -> set
        self._counter = 200
        self.comments = []      # (issue_id, text)

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

    def add_comment(self, issue_id, text):
        self.comments.append((issue_id, text))


class TestRun(unittest.TestCase):
    def _write_plan(self, d, plan):
        p = os.path.join(d, "create-plan.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(plan))
        return p

    def _write_solution(self, d, text="mechanism"):
        p = os.path.join(d, "SOLUTION.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_solution_posted_and_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            fc = FakeClient()
            out = cy.run(p, dry_run=False, client=fc, solution_path=s, today="2026-10-22")
            self.assertEqual(fc.comments, [("SAS-200", "## Техническое решение, 2026-10-22\n\nmechanism")])
            mapping = cy.load_mapping(os.path.join(d, ".created.json"))
            self.assertEqual(mapping[cy.SOLUTION_KEY], "2026-10-22")
            self.assertIn("Решение опубликовано комментарием к SAS-200", out)

    def test_solution_skipped_when_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            cy.save_mapping(os.path.join(d, ".created.json"), {cy.SOLUTION_KEY: "2026-10-01"})
            fc = FakeClient()
            out = cy.run(p, dry_run=False, client=fc, solution_path=s, today="2026-10-22")
            self.assertEqual(fc.comments, [])
            self.assertIn("уже было опубликовано (2026-10-01)", out)
            self.assertEqual(len(fc.created), 2)

    def test_solution_with_legacy_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            cy.save_mapping(os.path.join(d, ".created.json"), {"01-schema": "SAS-201"})
            fc = FakeClient()
            cy.run(p, dry_run=False, client=fc, solution_path=s, today="2026-10-22")
            self.assertEqual(len(fc.created), 1)
            self.assertEqual(len(fc.comments), 1)
            mapping = cy.load_mapping(os.path.join(d, ".created.json"))
            self.assertEqual(mapping[cy.SOLUTION_KEY], "2026-10-22")
            self.assertEqual(mapping["01-schema"], "SAS-201")

    def test_solution_dry_run_shows_step_without_writes(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            fc = FakeClient()
            out = cy.run(p, dry_run=True, client=fc, solution_path=s)
            self.assertIn("будет опубликовано комментарием к SAS-200", out)
            self.assertEqual(fc.comments, [])
            self.assertEqual(fc.created, [])

    def test_solution_heading_stripped_from_comment(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d, "# SAS-200 — Техническое решение\n\nmechanism\n")
            fc = FakeClient()
            cy.run(p, dry_run=False, client=fc, solution_path=s, today="2026-10-22")
            self.assertEqual(fc.comments[0][1], "## Техническое решение, 2026-10-22\n\nmechanism")

    def test_empty_solution_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d, "# SAS-200 — Техническое решение\n\n")
            with self.assertRaises(cy.PlanError):
                cy.run(p, dry_run=False, client=FakeClient(), solution_path=s)

    def test_failed_comment_does_not_record_key(self):
        class FailingClient(FakeClient):
            def add_comment(self, issue_id, text):
                raise RuntimeError("boom")
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            with self.assertRaises(RuntimeError):
                cy.run(p, dry_run=False, client=FailingClient(), solution_path=s)
            mapping = cy.load_mapping(os.path.join(d, ".created.json"))
            self.assertNotIn(cy.SOLUTION_KEY, mapping)
            self.assertEqual(set(mapping), {"01-schema", "02-model"})

    def test_report_table_has_no_reserved_key_row(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            s = self._write_solution(d)
            out = cy.run(p, dry_run=False, client=FakeClient(), solution_path=s, today="2026-10-22")
            self.assertNotIn("| solution_comment", out)

    def test_missing_solution_file_raises_before_writes(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            with self.assertRaises(cy.PlanError) as ctx:
                cy.run(p, dry_run=False, client=fc, solution_path=os.path.join(d, "nope.md"))
            self.assertIn("nope.md", str(ctx.exception))
            self.assertEqual(fc.created, [])

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
            # Direction: edge from=01-schema(SAS-201) to=02-model(SAS-202)
            # means "02-model depends on 01-schema" → command applied to SAS-202.
            self.assertIn(("SAS-202", "depends on SAS-201"), fc.links)
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

    def test_idempotent_depend_link_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            # Pretend the dependency link already exists: for DEPEND type,
            # SAS-202 already depends on SAS-201 (the from_id).
            def existing(issue_id, link_type):
                if link_type == cy.LINK_TYPE_DEPEND:
                    return {"SAS-201"}
                return set()
            fc.existing_link_targets = existing
            cy.run(p, dry_run=False, client=fc)
            self.assertFalse(any(q.startswith("depends on") for _, q in fc.links))

    def test_incremental_save_persists_before_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write_plan(d, make_plan())
            fc = FakeClient()
            orig_create = fc.create_issue
            state = {"n": 0}
            def failing_create(project_id, summary, description):
                state["n"] += 1
                if state["n"] == 2:
                    raise RuntimeError("boom")
                return orig_create(project_id, summary, description)
            fc.create_issue = failing_create
            with self.assertRaises(RuntimeError):
                cy.run(p, dry_run=False, client=fc)
            mapping = cy.load_mapping(os.path.join(d, ".created.json"))
            self.assertIn("01-schema", mapping)     # first creation persisted
            self.assertNotIn("02-model", mapping)   # second never completed


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

    def test_solution_file_via_main_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "create-plan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps(make_plan()))
            s = os.path.join(d, "SOLUTION.md")
            with open(s, "w", encoding="utf-8") as f:
                f.write("mechanism")
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cy.main(["--plan", p, "--solution-file", s, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("будет опубликовано комментарием к SAS-200", buf.getvalue())

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


if __name__ == "__main__":
    unittest.main()
