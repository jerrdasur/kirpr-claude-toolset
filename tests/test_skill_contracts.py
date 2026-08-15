from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-adr-init",
    "kirpr-adr-write", "kirpr-adr-review", "kirpr-text",
    "expert-panel", "grill-me", "kirpr-flow",
)


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"missing front matter: {path}")
    return text, match.group(1)


def assert_explicit_skill(testcase, name):
    skill = ROOT / "skills" / name / "SKILL.md"
    metadata = ROOT / "skills" / name / "agents" / "openai.yaml"
    text, frontmatter = read_frontmatter(skill)
    testcase.assertRegex(frontmatter, rf"(?m)^name: ['\"]?{re.escape(name)}['\"]?$")
    testcase.assertIn("allow_implicit_invocation: false", metadata.read_text(encoding="utf-8"))
    testcase.assertNotIn("$ARGUMENTS", text)


def assert_claude_adapter(testcase, command, skill):
    text = (ROOT / "commands" / "kirpr" / f"{command}.md").read_text(encoding="utf-8")
    testcase.assertIn(f"~/.claude/skills/{skill}/SKILL.md", text)
    testcase.assertIn("$ARGUMENTS", text)
    testcase.assertLessEqual(len(text.splitlines()), 12)


class TestTrackerCrudSkills(unittest.TestCase):
    CASES = (
        ("task-fetch", "kirpr-task-fetch"),
        ("task-create", "kirpr-task-create"),
        ("task-update", "kirpr-task-update"),
        ("task-delete", "kirpr-task-delete"),
    )

    def test_explicit_skills_exist(self):
        for _, skill in self.CASES:
            with self.subTest(skill=skill):
                assert_explicit_skill(self, skill)

    def test_claude_commands_are_thin_adapters(self):
        for command, skill in self.CASES:
            with self.subTest(command=command):
                assert_claude_adapter(self, command, skill)

    def test_create_skill_obtains_issue_link_base_url_from_runtime(self):
        runtime = (ROOT / "kirpr" / "config" / "tracker-runtime.md").read_text(encoding="utf-8")
        create_skill = (ROOT / "skills" / "kirpr-task-create" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("`URL:`", runtime)
        self.assertIn("запомни его как базовый URL", runtime)
        self.assertIn("базовый URL был определён при выполнении runtime-инструкции", create_skill)


class TestDecompositionSkills(unittest.TestCase):
    CASES = (
        ("tasks-decompose", "kirpr-tasks-decompose"),
        ("tasks-review", "kirpr-tasks-review"),
        ("tasks-adapt", "kirpr-tasks-adapt"),
        ("tasks-push", "kirpr-tasks-push"),
    )

    def test_explicit_skills_exist(self):
        for _, skill in self.CASES:
            with self.subTest(skill=skill):
                assert_explicit_skill(self, skill)

    def test_claude_commands_are_thin_adapters(self):
        for command, skill in self.CASES:
            with self.subTest(command=command):
                assert_claude_adapter(self, command, skill)


class TestAdrAndTextSkills(unittest.TestCase):
    CASES = (
        ("adr-init", "kirpr-adr-init"),
        ("adr-write", "kirpr-adr-write"),
        ("adr-review", "kirpr-adr-review"),
        ("text", "kirpr-text"),
    )

    def test_explicit_skills_exist(self):
        for _, skill in self.CASES:
            with self.subTest(skill=skill):
                assert_explicit_skill(self, skill)

    def test_claude_commands_are_thin_adapters(self):
        for command, skill in self.CASES:
            with self.subTest(command=command):
                assert_claude_adapter(self, command, skill)


class TestAdrInitCalibrationCatalogue(unittest.TestCase):
    def setUp(self):
        self.skill = (ROOT / "skills" / "kirpr-adr-init" / "SKILL.md").read_text(
            encoding="utf-8"
        )

    def test_greenfield_catalogue_has_canonical_source_urls(self):
        for url in (
            "https://raw.githubusercontent.com/arachne-framework/architecture/master/adr-NNN.md",
            "https://raw.githubusercontent.com/backstage/backstage/master/docs/architecture-decisions/adrNNN.md",
            "https://raw.githubusercontent.com/alphagov/govuk-aws/main/docs/architecture/decisions/NNNN-*.md",
            "https://raw.githubusercontent.com/nationalarchives/tdr-dev-documentation/master/architecture-decision-records/NNNN-*.md",
        ):
            with self.subTest(url=url):
                self.assertIn(url, self.skill)

    def test_calibration_examples_keep_distinct_local_and_external_formats(self):
        for detail in (
            "Для **внешних** ADR (из интернета):",
            "Источник: {URL}",
            "К5 Codebase & ADR Alignment: **N/A** — внешний ADR",
            "Для **локальных** ADR (из репозитория):",
            "Файл: `{path}` (существующий ADR {ID})",
            "К5 Codebase & ADR Alignment: **{0-10 / N/A}**",
            "К6 Conciseness & Density",
        ):
            with self.subTest(detail=detail):
                self.assertIn(detail, self.skill)
