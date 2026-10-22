from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "kirpr" / "config"
SKILLS = sorted((ROOT / "skills").glob("kirpr-tasks-*/SKILL.md"))
TEXTS = [CONFIG / n for n in ("workflow.md", "templates.md")] + SKILLS + [ROOT / "skills" / "kirpr-onboard" / "SKILL.md"]

LEGACY = [
    r"XX-Y", r"~\dч", r"<= 4 час", r"Параллельные потоки",
    r"граф зависимостей", r"\d\d-\d-[a-z-]+\.md",
]


def _body_without_headings(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


class TestNoLegacyFormat(unittest.TestCase):
    def test_no_legacy_markers(self):
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pat in LEGACY:
                with self.subTest(file=f"{path.parent.name}/{path.name}", marker=pat):
                    self.assertIsNone(re.search(pat, text, re.IGNORECASE))


class TestPhaseReferences(unittest.TestCase):
    def test_skill_phase_numbers_exist_in_workflow(self):
        workflow = (CONFIG / "workflow.md").read_text(encoding="utf-8")
        defined = set(re.findall(r"^## Phase (\d+)", workflow, re.MULTILINE))
        referenced = set()
        for path in SKILLS + [CONFIG / "templates.md"]:
            body = _body_without_headings(path.read_text(encoding="utf-8"))
            referenced |= set(re.findall(r"Phase (\d+)", body))
        self.assertTrue(referenced <= defined, referenced - defined)


class TestContextLoading(unittest.TestCase):
    def test_loading_section_mentions_all_artifacts(self):
        text = (CONFIG / "templates.md").read_text(encoding="utf-8")
        section = text.split("## Loading decomposition context", 1)[1].split("\n---", 1)[0]
        for name in ("source.md", "research.md", "SOLUTION.md", "00-overview.md"):
            with self.subTest(name=name):
                self.assertIn(name, section)


class TestTemplates(unittest.TestCase):
    def test_solution_template_has_problem_section(self):
        text = (CONFIG / "templates.md").read_text(encoding="utf-8")
        section = text.split("## SOLUTION.md template", 1)[1].split("\n---", 1)[0]
        self.assertIn("## Проблема", section)  # template body stays Russian

    def test_overview_template_has_external_dependencies(self):
        text = (CONFIG / "templates.md").read_text(encoding="utf-8")
        section = text.split("## 00-overview.md template", 1)[1].split("\n---", 1)[0]
        self.assertIn("## Внешние зависимости", section)


class TestProjectMemory(unittest.TestCase):
    def setUp(self):
        self.text = (CONFIG / "templates.md").read_text(encoding="utf-8")

    def test_loading_section_mentions_memory_files(self):
        section = self.text.split("## Loading decomposition context", 1)[1].split("\n---", 1)[0]
        for name in ("workspace.md", "memory.md", "kirpr-onboard"):
            with self.subTest(name=name):
                self.assertIn(name, section)

    def test_memory_section_has_format_and_hitl(self):
        section = self.text.split("## Project memory", 1)[1].split("\n---", 1)[0]
        for needle in ("### Lesson format", "[L-NNN]", "### Writing lessons (HITL)", "--dry-run", "150"):
            with self.subTest(needle=needle):
                self.assertIn(needle, section)

    def test_context_template_has_memory_version(self):
        section = self.text.split("## .context.md template", 1)[1].split("\n---", 1)[0]
        self.assertIn("**Версия памяти:**", section)


class TestDecomposeReadsMemory(unittest.TestCase):
    def test_workflow_phases_reference_memory(self):
        wf = (CONFIG / "workflow.md").read_text(encoding="utf-8")
        p1 = wf.split("## Phase 1", 1)[1].split("## Phase 2", 1)[0]
        p5 = wf.split("## Phase 5", 1)[1].split("## Phase 6", 1)[0]
        self.assertIn("workspace.md", p1)
        self.assertIn("memory.md", p1)
        self.assertIn("L-", p5)
        skill = (ROOT / "skills/kirpr-tasks-decompose/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Project memory", skill)


if __name__ == "__main__":
    unittest.main()
