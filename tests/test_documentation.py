from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_documents_both_invocation_forms(self):
        self.assertIn("/kirpr:task-fetch", self.text)
        self.assertIn("$kirpr-task-fetch", self.text)
        self.assertIn("$expert-panel", self.text)

    def test_documents_targets_and_shared_paths(self):
        for value in ("--target claude", "--target codex", "--target all",
                      "~/.config/kirpr", "~/.local/share/kirpr"):
            with self.subTest(value=value):
                self.assertIn(value, self.text)

    def test_runtime_is_documented_as_installer_managed(self):
        self.assertIn("installer-managed runtime", self.text)
        self.assertNotIn("read-only runtime", self.text)

    def test_documents_project_memory(self):
        for value in ("/kirpr:onboard", "$kirpr-onboard", ".kirpr/workspace.md", ".kirpr/memory.md", "kirpr_memory.py"):
            with self.subTest(value=value):
                self.assertIn(value, self.text)
