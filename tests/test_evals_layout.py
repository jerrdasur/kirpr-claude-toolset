import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
ALLOWED = {"name", "description", "tags", "plugins", "runs", "model", "max_turns",
           "timeout_seconds", "allowed_tools", "append_system_prompt", "env"}
GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
CHECK_KINDS = {"last_message_regex", "files_absent", "commands_absent", "requests_log_empty"}


def read_frontmatter_keys(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return set(), set()
    keys, env, in_env = set(), set(), False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        top = re.match(r"^([a-z_]+):", line)
        if top:
            keys.add(top.group(1))
            in_env = top.group(1) == "env"
            continue
        nested = re.match(r"^\s+([A-Za-z0-9_]+):", line)
        if in_env and nested:
            env.add(nested.group(1))
    return keys, env


def case_dirs():
    if not EVALS.is_dir():
        return []
    return sorted(p for p in EVALS.iterdir()
                  if p.is_dir() and p.name not in ("_fixtures", "results") and (p / "prompt.md").is_file())


class TestPluginManifest(unittest.TestCase):
    def test_manifest_is_name_only(self):
        self.assertEqual(json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")),
                         {"name": "kirpr"})

    def test_results_are_ignored(self):
        self.assertIn("evals/results/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_installer_does_not_ship_evals(self):
        lib = (ROOT / "installer/lib.sh").read_text(encoding="utf-8")
        self.assertNotIn("evals", lib)
        self.assertNotIn(".claude-plugin", lib)


class TestEvalCases(unittest.TestCase):
    def test_frontmatter_parser(self):
        keys, env = read_frontmatter_keys("---\nmax_turns: 5\ntags: [a]\nenv:\n  EVAL_X: y\n---\nbody")
        self.assertEqual((keys, env), ({"max_turns", "tags", "env"}, {"EVAL_X"}))

    def test_every_case_is_well_formed(self):
        for case in case_dirs():
            with self.subTest(case=case.name):
                keys, env = read_frontmatter_keys((case / "prompt.md").read_text(encoding="utf-8"))
                self.assertLessEqual(keys, ALLOWED, f"{case.name}: {keys - ALLOWED}")
                for k in env:
                    self.assertRegex(k, r"^EVAL_[A-Z0-9_]*$", f"{case.name}: env {k}")
                graders = sorted((case / "graders").glob("*.md"))
                self.assertTrue(graders, f"{case.name}: нет грейдеров")
                for g in graders:
                    m = re.search(r"^type:\s*(\S+)", g.read_text(encoding="utf-8"), re.M)
                    self.assertTrue(m and m.group(1) in GRADER_TYPES, f"{case.name}/{g.name}: type")
                fixture = case / "fixture.sh"
                if fixture.exists():
                    self.assertTrue(os.access(fixture, os.X_OK), f"{case.name}: fixture.sh не исполняемый")

    def test_codex_specs_are_valid(self):
        for spec in sorted(EVALS.glob("*/codex.json")):
            with self.subTest(case=spec.parent.name):
                data = json.loads(spec.read_text(encoding="utf-8"))
                self.assertTrue(data.get("prompt"))
                self.assertTrue(data.get("checks"))
                self.assertLessEqual(set(data["checks"]), CHECK_KINDS)


def grader_files():
    return sorted(EVALS.glob("*/graders/*.md"))


class TestEvalReviewFixes(unittest.TestCase):
    def test_no_eval_file_is_git_ignored(self):
        files = [str(p.relative_to(ROOT)) for p in EVALS.rglob("*")
                 if p.is_file() and "results" not in p.parts and "__pycache__" not in p.parts]
        ignored = subprocess.run(["git", "check-ignore", "--no-index", *files], cwd=ROOT,
                                 capture_output=True, text=True).stdout.split()
        self.assertEqual(ignored, [], f"git игнорирует файлы evals: {ignored}")

    def test_skill_matchers_do_not_depend_on_json_serialization(self):
        for g in grader_files():
            text = g.read_text(encoding="utf-8")
            with self.subTest(grader=str(g.relative_to(EVALS))):
                self.assertNotIn('"skill"', text)

    def test_skill_graders_are_scored_in_both_arms(self):
        for g in grader_files():
            text = g.read_text(encoding="utf-8")
            if re.search(r"^tool:\s*Skill\s*$", text, re.M):
                with self.subTest(grader=str(g.relative_to(EVALS))):
                    self.assertRegex(text, r"(?m)^arm:\s*both\s*$")

    def test_fixtures_do_not_rely_on_plugin_root_and_panel_is_self_contained(self):
        for f in sorted(EVALS.glob("*/fixture.sh")):
            text = f.read_text(encoding="utf-8")
            with self.subTest(fixture=f.parent.name):
                self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)
                if f.parent.name.startswith("panel-"):
                    self.assertNotIn("_fixtures", text)
                if re.search(r"\bg init\b|git init", text):
                    self.assertIn("require-git", text) if "_fixtures" in text else self.assertIn("xcrun", text)
        runtime = (EVALS / "_fixtures" / "install-runtime.sh").read_text(encoding="utf-8")
        self.assertNotIn("require-git", runtime)

    def test_runtime_scaffold_leaves_no_personal_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, work = Path(tmp, "home"), Path(tmp, "work")
            home.mkdir(); work.mkdir()
            env = {"PATH": os.environ["PATH"], "HOME": str(home), "TMPDIR": tmp, "TERM": "dumb"}
            subprocess.run(["bash", str(EVALS / "hitl-task-delete-preview-first" / "fixture.sh")],
                           cwd=work, env=env, check=True, capture_output=True)
            self.assertTrue((home / ".local/share/kirpr/scripts/manage_youtrack.py").is_file())
            self.assertTrue((home / ".config/kirpr/tracker.md").is_file())
            self.assertEqual(sorted(p.name for p in (home / ".claude/skills").glob("*")) if (home / ".claude/skills").exists() else [], [])
            self.assertFalse((home / ".claude/commands/kirpr").exists())


if __name__ == "__main__":
    unittest.main()
