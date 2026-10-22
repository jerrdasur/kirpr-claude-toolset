import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data"
sys.path.insert(0, str(ROOT / "evals"))
import codex_smoke as cs  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workdir = self.root / "work"
        self.workdir.mkdir()

    def make_case(self, data, name="case-a"):
        case = self.root / "evals" / name
        case.mkdir(parents=True)
        (case / "prompt.md").write_text("---\ntags: [codex]\n---\n\nprompt\n", encoding="utf-8")
        (case / "codex.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return case


class TestCodexSmoke(Base):
    def test_parse_events_from_sample(self):
        msg, commands = cs.parse_events((DATA / "codex_exec_sample.jsonl").read_text(encoding="utf-8"))
        self.assertIn("workspace.md", msg)
        self.assertEqual(len(commands), 1)
        self.assertIn("refresh --dry-run", commands[0])

    def test_parse_events_ignores_garbage_lines(self):
        msg, commands = cs.parse_events('not json\n{"type":"item.completed","item":{"type":"agent_message","text":"hi"}}\n')
        self.assertEqual((msg, commands), ("hi", []))

    def test_unknown_check_kind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "неизвестная проверка: magic"):
            cs.load_case(self.make_case({"prompt": "$x", "checks": {"magic": 1}}))

    def test_checks(self):
        case = cs.load_case(self.make_case({"prompt": "$x", "checks": {
            "last_message_regex": ["Записать .*workspace\\.md"], "files_absent": [".kirpr/workspace.md"],
            "commands_absent": ["kirpr_memory\\.py refresh(?!.*--dry-run)"], "requests_log_empty": True}}))
        ok = cs.run_checks(case, "Записать .kirpr/workspace.md?", ["python3 kirpr_memory.py refresh --dry-run"], self.workdir)
        self.assertTrue(all(r[1] for r in ok), ok)
        (self.workdir / ".kirpr").mkdir()
        (self.workdir / ".kirpr/workspace.md").write_text("x", encoding="utf-8")
        bad = cs.run_checks(case, "готово", ["python3 kirpr_memory.py refresh"], self.workdir)
        self.assertEqual([r[0] for r in bad if not r[1]], ["last_message_regex", "files_absent", "commands_absent"])

    def test_requests_log_check(self):
        case = cs.load_case(self.make_case({"prompt": "$x", "checks": {"requests_log_empty": True}}))
        self.assertEqual(cs.run_checks(case, "", [], self.workdir), [("requests_log_empty", True, "нет записей")])
        (self.workdir / ".eval-tracker").mkdir()
        (self.workdir / ".eval-tracker/requests.log").write_text("DELETE /api/issues/SAS-200 \n", encoding="utf-8")
        name, ok, detail = cs.run_checks(case, "", [], self.workdir)[0]
        self.assertEqual((name, ok), ("requests_log_empty", False))
        self.assertIn("DELETE", detail)

    def test_main_without_codex_exits_2(self):
        self.make_case({"prompt": "$x", "checks": {"files_absent": ["a"]}})
        empty = self.root / "empty-bin"
        empty.mkdir()
        with mock.patch.dict(os.environ, {"PATH": str(empty)}):
            self.assertEqual(cs.main(["--evals", str(self.root / "evals")]), 2)

    def test_repository_codex_cases_load(self):
        cases = sorted((ROOT / "evals").glob("*/codex.json"))
        self.assertEqual(len(cases), 4)
        for spec in cases:
            with self.subTest(case=spec.parent.name):
                case = cs.load_case(spec.parent)
                self.assertTrue(case.prompt.startswith("$"))


class TestCodexSmokeReviewFixes(Base):
    def test_failed_codex_run_is_a_failure_even_if_checks_pass(self):
        case = cs.load_case(self.make_case({"prompt": "$x", "checks": {"files_absent": ["a"], "requests_log_empty": True}}))
        results = cs.evaluate_run(case, 2, "", "error: unexpected argument --ignore-user-config", self.workdir)
        self.assertEqual(results[0][:2], ("run", False))
        self.assertIn("unexpected argument", results[0][2])

    def test_stream_without_agent_message_is_a_failure(self):
        case = cs.load_case(self.make_case({"prompt": "$x", "checks": {"files_absent": ["a"]}}))
        results = cs.evaluate_run(case, 0, '{"type":"turn.started"}\n', "", self.workdir)
        self.assertEqual(results[0][:2], ("run", False))

    def test_good_run_reports_only_checks(self):
        case = cs.load_case(self.make_case({"prompt": "$x", "checks": {"files_absent": ["a"]}}))
        stream = '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n'
        self.assertEqual(cs.evaluate_run(case, 0, stream, "", self.workdir), [("files_absent", True, "ok")])

    def test_invalid_check_values_are_rejected(self):
        for checks in ({"requests_log_empty": False}, {"files_absent": "a"}, {"last_message_regex": [1]}):
            with self.subTest(checks=checks):
                with self.assertRaises(ValueError):
                    cs.load_case(self.make_case({"prompt": "$x", "checks": checks}, name=f"c{abs(hash(str(checks)))}"))

    def test_no_selected_cases_exits_2(self):
        self.make_case({"prompt": "$x", "checks": {"files_absent": ["a"]}})
        fake = self.root / "bin"
        fake.mkdir()
        (fake / "codex").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (fake / "codex").chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{fake}:{os.environ['PATH']}"}):
            self.assertEqual(cs.main(["--evals", str(self.root / "evals"), "--case", "typo"]), 2)


if __name__ == "__main__":
    unittest.main()
