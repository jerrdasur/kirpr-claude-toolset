from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


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
