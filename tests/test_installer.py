from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-adr-init",
    "kirpr-adr-write", "kirpr-adr-review", "kirpr-text",
    "expert-panel", "grill-me", "kirpr-flow",
)


class InstallerCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input_file = self.root / "input"
        self.input_file.write_text("3\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, script, *args, check=True, extra_env=None, with_input=True):
        env = os.environ.copy()
        env["KIRPR_INSTALL_ROOT"] = str(self.root)
        if with_input:
            env["KIRPR_INPUT_FILE"] = str(self.input_file)
        else:
            env["KIRPR_INPUT_FILE"] = str(self.root / "missing-input")
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(ROOT / script), *args], cwd=ROOT, env=env,
            text=True, capture_output=True, check=check,
        )


class TestCleanInstall(InstallerCase):
    def assert_skills(self, base):
        for name in ALL_SKILLS:
            self.assertTrue((base / name / "SKILL.md").is_file(), name)
            self.assertTrue((base / name / "agents" / "openai.yaml").is_file(), name)

    def manifest_records(self):
        manifest = self.root / ".config" / "kirpr" / "install-manifest"
        return {tuple(line.split("\t")) for line in manifest.read_text(encoding="utf-8").splitlines()}

    def test_codex_target(self):
        self.run_script("install.sh", "--target", "codex")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assertFalse((self.root / ".claude" / "skills").exists())
        self.assertFalse((self.root / ".claude" / "commands" / "kirpr").exists())
        records = self.manifest_records()
        self.assertIn(("target", "codex"), records)
        self.assertIn(("path", "codex", str(self.root / ".agents" / "skills")), records)
        self.assertIn(("path", "shared", str(self.root / ".local" / "share" / "kirpr")), records)
        self.assertFalse(any(record[1] == "claude" for record in records if len(record) > 1))

    def test_claude_target(self):
        self.run_script("install.sh", "--target", "claude")
        self.assert_skills(self.root / ".claude" / "skills")
        self.assertEqual(len(list((self.root / ".claude" / "commands" / "kirpr").glob("*.md"))), 12)
        self.assertFalse((self.root / ".agents" / "skills").exists())
        records = self.manifest_records()
        self.assertIn(("target", "claude"), records)
        self.assertIn(("path", "claude", str(self.root / ".claude" / "skills")), records)
        self.assertIn(("path", "claude", str(self.root / ".claude" / "commands" / "kirpr")), records)
        self.assertFalse(any(record[1] == "codex" for record in records if len(record) > 1))

    def test_all_target(self):
        self.run_script("install.sh", "--target", "all")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assert_skills(self.root / ".claude" / "skills")
        self.assertTrue((self.root / ".local" / "share" / "kirpr" / "scripts" / "manage_jira.py").is_file())

    def test_interactive_target_selection(self):
        self.input_file.write_text("2\n3\n", encoding="utf-8")
        self.run_script("install.sh")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assertFalse((self.root / ".claude" / "skills").exists())

    def test_no_target_without_input_terminal_fails(self):
        result = self.run_script("install.sh", check=False, with_input=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target", result.stderr)
        self.assertFalse((self.root / ".agents").exists())

    def test_tracker_input_failure_leaves_no_destinations(self):
        result = self.run_script(
            "install.sh", "--target", "codex", check=False, with_input=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".config").exists())
        self.assertFalse((self.root / ".local").exists())
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".claude").exists())
        self.assertFalse((self.root / ".config" / "kirpr" / "install-manifest").exists())

    def test_unknown_target_fails_without_writes(self):
        result = self.run_script("install.sh", "--target", "other", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".agents").exists())
        self.assertIn("claude|codex|all", result.stderr)

    def test_tracker_choice_writes_shared_user_configuration(self):
        self.input_file.write_text(
            "1\n1\nhttps://youtrack.example.test\n", encoding="utf-8"
        )
        self.run_script("install.sh")
        tracker = self.root / ".config" / "kirpr" / "tracker.md"
        self.assertTrue(tracker.is_file())
        text = tracker.read_text(encoding="utf-8")
        self.assertTrue("Трекер: YouTrack" in text)
        self.assertTrue("fetch_youtrack.py" in text)
        self.assertFalse("fetch_tracker.py" in text)
