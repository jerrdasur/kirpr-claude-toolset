from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-text",
    "expert-panel", "grill-me",
)


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"missing front matter: {path}")
    return text, match.group(1)


def read_metadata(path):
    result = {}
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if not line.startswith(" "):
            if not line.endswith(":"):
                raise AssertionError(f"invalid top-level metadata: {path}: {line}")
            section = line[:-1]
            if section in result:
                raise AssertionError(f"duplicate metadata section: {path}: {section}")
            result[section] = {}
            continue
        match = re.fullmatch(r"  ([a-z_]+):\s+(.+)", line)
        if section is None or not match:
            raise AssertionError(f"invalid nested metadata: {path}: {line}")
        key, value = match.groups()
        if key in result[section]:
            raise AssertionError(f"duplicate metadata field: {path}: {key}")
        result[section][key] = value.strip('"')
    return result


def assert_explicit_skill(testcase, name):
    skill = ROOT / "skills" / name / "SKILL.md"
    metadata = ROOT / "skills" / name / "agents" / "openai.yaml"
    text, frontmatter = read_frontmatter(skill)
    testcase.assertRegex(frontmatter, rf"(?m)^name: ['\"]?{re.escape(name)}['\"]?$")
    parsed_metadata = read_metadata(metadata)
    testcase.assertEqual(set(parsed_metadata), {"interface", "policy"})
    testcase.assertEqual(
        set(parsed_metadata["interface"]),
        {"display_name", "short_description", "default_prompt"},
    )
    testcase.assertTrue(all(parsed_metadata["interface"].values()))
    testcase.assertIn(f"${name}", parsed_metadata["interface"]["default_prompt"])
    testcase.assertEqual(parsed_metadata["policy"], {"allow_implicit_invocation": "false"})
    testcase.assertNotIn("$ARGUMENTS", text)


def assert_claude_adapter(testcase, command, skill):
    text = (ROOT / "commands" / "kirpr" / f"{command}.md").read_text(encoding="utf-8")
    testcase.assertIn(f"~/.claude/skills/{skill}/SKILL.md", text)
    testcase.assertIn("$ARGUMENTS", text)
    testcase.assertLessEqual(len(text.splitlines()), 12)


OUTPUT_LANGUAGE_LINE = "Everything addressed to the user and everything written to files is in Russian."


class TestGlobalSkillContracts(unittest.TestCase):
    FORBIDDEN = ("~/.claude/kirpr", ".Codex", "AskUserQuestion", "TodoWrite")

    def test_every_skill_declares_output_language(self):
        for name in ALL_SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn(OUTPUT_LANGUAGE_LINE, text)

    def test_all_skills_are_explicit(self):
        for skill in ALL_SKILLS:
            with self.subTest(skill=skill):
                assert_explicit_skill(self, skill)

    def test_canonical_skills_have_no_platform_runtime_paths(self):
        for skill in ALL_SKILLS:
            for path in (ROOT / "skills" / skill).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for forbidden in self.FORBIDDEN:
                    with self.subTest(skill=skill, path=path, forbidden=forbidden):
                        self.assertNotIn(forbidden, text)

    def test_exact_skill_set(self):
        actual = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
        self.assertEqual(actual, set(ALL_SKILLS))


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
        self.assertIn("remember it as the base URL", runtime)
        self.assertIn("базовый URL был определён при выполнении runtime-инструкции", create_skill)

    def test_create_skill_cross_workflow_reference_shows_both_invocation_forms(self):
        create_skill = (ROOT / "skills" / "kirpr-task-create" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("$kirpr-tasks-push", create_skill)
        self.assertIn("/kirpr:tasks-push", create_skill)


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


class TestTextSkill(unittest.TestCase):
    CASES = (
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

    def test_text_requires_confirmed_destination_before_every_edit(self):
        text = (ROOT / "skills" / "kirpr-text" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Куда сохранить результат?", text)
        self.assertIn("для любой задачи", text.lower())
        self.assertIn("не начинай редактирование", text)
        destination = text.index("Куда сохранить результат?")
        editing = text.index("До редактуры")
        execution = text.index("Выполни задачу")
        self.assertLess(destination, editing)
        self.assertLess(destination, execution)


class TestExistingSkillPortability(unittest.TestCase):
    def test_grill_me_discovers_both_project_guidance_files(self):
        lenses = (ROOT / "skills" / "grill-me" / "phases" / "lenses.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("CLAUDE.md", lenses)
        self.assertIn("AGENTS.md", lenses)
