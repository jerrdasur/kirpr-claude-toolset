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

    def test_documents_panel_composition_and_acceptance(self):
        self.assertIn("Filippo Valsorda", self.text)
        self.assertIn("NN-service.md", self.text)


class TestExpertPanelSpecHistory(unittest.TestCase):
    def test_limit_reversal_is_recorded(self):
        spec = (ROOT / "docs/superpowers/specs/2026-07-24-expert-panel-design.md").read_text(encoding="utf-8")
        self.assertIn("## Изменения", spec)
        section = spec.split("## Изменения", 1)[1]
        self.assertIn("2026-10-22", section)
        self.assertIn("лимит", section)


class TestEvalsDocs(unittest.TestCase):
    def test_readme_documents_evals(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for value in ("claude plugin eval", "evals/README.md", "codex_smoke.py",
                      "installing kirpr as a Claude Code plugin is not supported yet"):
            with self.subTest(value=value):
                self.assertIn(value, text)

    def test_evals_readme_has_run_cost_results_codex_and_first_run(self):
        text = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
        for heading in ("## Запуск", "## Стоимость", "## Чтение отчёта", "## Codex",
                        "## Как устроен прогон", "## Первый прогон"):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)


class TestEvalsCommand(unittest.TestCase):
    def test_full_run_command_allows_full_bash_and_search(self):
        for path in (ROOT / "README.md", ROOT / "evals" / "README.md"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertIn("--allow-tools Bash Read Glob Grep Write Edit Agent Skill", text)
                self.assertNotIn('--allow-tools "Bash(git *)" Read Write Edit Agent Skill', text)

    def test_first_run_lists_open_questions_honestly(self):
        text = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
        for needle in ("--allow-tools", "EVAL_*", "tracker-runtime.md"):
            self.assertIn(needle, text.split("## Как устроен прогон", 1)[1])
        self.assertNotIn("через `$CLAUDE_PLUGIN_ROOT`", text)
