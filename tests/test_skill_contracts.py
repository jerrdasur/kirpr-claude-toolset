from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-text",
    "expert-panel", "grill-me", "kirpr-onboard",
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

    def test_decompose_description_promises_self_contained_subtasks(self):
        _, frontmatter = read_frontmatter(ROOT / "skills" / "kirpr-tasks-decompose" / "SKILL.md")
        self.assertIn("self-contained implementation subtasks", frontmatter)

    def test_create_skill_obtains_issue_link_base_url_from_runtime(self):
        runtime = (ROOT / "kirpr" / "config" / "tracker-runtime.md").read_text(encoding="utf-8")
        create_skill = (ROOT / "skills" / "kirpr-task-create" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("`URL:`", runtime)
        self.assertIn("remember it as the base URL", runtime)
        self.assertIn("the base URL was determined while running the runtime instruction", create_skill)

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
        ("onboard", "kirpr-onboard"),
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
        self.assertIn("for any task", text.lower())
        self.assertIn("do not start editing", text)
        destination = text.index("Куда сохранить результат?")
        editing = text.index("Before editing")
        execution = text.index("Do the task")
        self.assertLess(destination, editing)
        self.assertLess(destination, execution)


class TestExistingSkillPortability(unittest.TestCase):
    def test_expert_panel_agents_answer_in_russian(self):
        text = (ROOT / "skills" / "expert-panel" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Language: every field of every finding and the good-decisions list is in Russian.", text)

    def test_russian_trigger_phrases_present(self):
        for name in ("expert-panel", "grill-me"):
            _, frontmatter = read_frontmatter(ROOT / "skills" / name / "SKILL.md")
            with self.subTest(skill=name):
                self.assertRegex(frontmatter, r"Triggers \([^)]*explicit call[^)]*\):[^\n]*[А-Яа-яЁё]")

    def test_grill_me_discovers_both_project_guidance_files(self):
        lenses = (ROOT / "skills" / "grill-me" / "phases" / "lenses.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("CLAUDE.md", lenses)
        self.assertIn("AGENTS.md", lenses)


class TestMemoryWriters(unittest.TestCase):
    def test_review_and_adapt_write_lessons_via_script_with_hitl(self):
        for name, phase in (("kirpr-tasks-review", "Phase 6"), ("kirpr-tasks-adapt", "Phase F")):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn(phase, text)
                self.assertIn("kirpr_memory.py lesson add", text)
                self.assertIn("--dry-run", text)
                self.assertIn("Do not write a lesson without", text)
                self.assertNotIn("Edit memory.md", text)

    def test_onboard_writes_only_through_the_script(self):
        text = (ROOT / "skills/kirpr-onboard/SKILL.md").read_text(encoding="utf-8")
        for needle in ("kirpr_memory.py init", "kirpr_memory.py role", "refresh --dry-run"):
            self.assertIn(needle, text)
        self.assertNotIn("editing the «Роль» cells", text)

    def test_hitl_block_describes_amend_path(self):
        for name in ("kirpr-tasks-review", "kirpr-tasks-adapt"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn("lesson amend L-NNN --file", text)
                self.assertIn("kirpr_memory.py init", text)

    def test_review_has_lessons_category(self):
        text = (ROOT / "skills/kirpr-tasks-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("#### Category 5: Lessons", text)


PANEL = ROOT / "skills" / "expert-panel"


def panel_text(*parts):
    return (PANEL.joinpath(*parts)).read_text(encoding="utf-8")


class TestExpertPanelCalibration(unittest.TestCase):
    def test_no_display_limit_and_no_below_threshold_section(self):
        for parts in (("SKILL.md",), ("modes", "diff.md"), ("modes", "spec.md")):
            text = panel_text(*parts)
            with self.subTest(file="/".join(parts)):
                self.assertNotIn("Ниже порога", text)
                self.assertNotIn("no more than 3 `blocker`", text)

    def test_finding_schema_has_confidence_and_diff_block(self):
        text = panel_text("SKILL.md")
        for field in ("`уверенность`", "`инвариант`", "`ломающий вход`", "`тест`"):
            with self.subTest(field=field):
                self.assertIn(field, text)
        self.assertIn("worst case", text)

    def test_severity_calibration_says_what_is_not_blocker(self):
        text = panel_text("SKILL.md")
        self.assertIn("Not `blocker` or `major`", text)
        self.assertIn("excluded by the contract", text)

    def test_doubt_goes_to_confidence_not_severity(self):
        text = panel_text("SKILL.md")
        self.assertNotIn("picks the higher one", text)
        self.assertIn("doubt is expressed in `уверенность`", text)

    def test_dedup_merges_locations_not_bugs(self):
        text = panel_text("SKILL.md")
        self.assertIn("one finding with a list of", text)
        self.assertIn("Different bugs are not merged", text)


PERSONA_BLOCKS = ("> \"", "**Кто.**", "**Как ревьюит.**", "**Характерные вопросы:**",
                  "**В спеке проверяет:**", "**В diff проверяет:**")


class TestExpertPanelCore(unittest.TestCase):
    def test_valsorda_persona_has_all_blocks(self):
        text = panel_text("experts", "valsorda.md")
        for block in PERSONA_BLOCKS:
            with self.subTest(block=block):
                self.assertIn(block, text)
        for topic in ("IDOR", "injection", "secrets"):
            self.assertIn(topic, text)

    def test_core_lists_valsorda_with_prefix_v(self):
        text = panel_text("SKILL.md")
        self.assertIn("`experts/valsorda.md`", text)
        self.assertIn("`valsorda`", text)
        self.assertIn("Valsorda — `V`", text)
        self.assertIn("«Панель: Pike, Cheney, Ford, Stonebraker, Valsorda»", text)

    def test_overlay_with_core_name_replaces_core_persona(self):
        text = panel_text("SKILL.md")
        self.assertIn("replaces that core expert", text)

    def test_template_samples_hashimoto_and_lists_valsorda_id(self):
        text = (ROOT / "kirpr" / "config" / "custom-experts.md.template").read_text(encoding="utf-8")
        self.assertNotIn("## Filippo Valsorda", text)
        self.assertIn("## Mitchell Hashimoto — тесты", text)
        self.assertIn("`valsorda`", text)
        self.assertEqual(text.count("<!-- BEGIN EXPERTS -->"), 1)
        self.assertTrue(text.rstrip().endswith("<!-- BEGIN EXPERTS -->"))


class TestExpertPanelAcceptance(unittest.TestCase):
    def setUp(self):
        self.diff = panel_text("modes", "diff.md")

    def test_orchestrator_acceptance_step_before_panel(self):
        self.assertIn("## Phase 1.5. Acceptance and generated code", self.diff)
        self.assertLess(self.diff.index("## Phase 1.5."), self.diff.index("## Phase 2. Panel"))
        for needle in ("ACCEPTANCE:", "- met:", "- unmet:", "`NN-service.md`", "«Проверить»", "scope creep"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.diff)

    def test_agents_no_longer_duplicate_spec_checks(self):
        self.assertNotIn("every agent additionally checks", self.diff)

    def test_missing_spec_is_declared_as_blind_spot(self):
        self.assertIn("критерии приёмки не проверялись", self.diff)

    def test_regeneration_check_and_memory(self):
        self.assertIn("//go:generate", self.diff)
        self.assertIn("не перегенерирована", self.diff)
        self.assertIn(".kirpr/memory.md", self.diff)
        self.assertIn("## Как проверять", self.diff)
        self.assertIn(".kirpr/memory.md", panel_text("modes", "spec.md"))

    def test_prefix_a_reserved_for_orchestrator(self):
        self.assertIn("`A` is reserved", panel_text("SKILL.md"))


class TestExpertPanelReviewFixes(unittest.TestCase):
    def setUp(self):
        self.skill = panel_text("SKILL.md")
        self.diff = panel_text("modes", "diff.md")
        self.spec = panel_text("modes", "spec.md")
        self.valsorda = panel_text("experts", "valsorda.md")

    def test_generated_check_is_narrow_and_low_by_default(self):
        for needle in ("`-destination`", "Code generated by", "categories 1 and 2 of «File filtering»",
                       "default: `minor`, `уверенность` `low`", "direct match"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.diff)
        self.assertNotIn("contains a `//go:generate` directive, or `.kirpr/memory.md` names a changed file", self.diff)

    def test_low_confidence_major_does_not_force_request_changes(self):
        self.assertIn("A `major` with `уверенность` `low` does not by itself", self.diff)

    def test_agents_receive_severity_section(self):
        prompt = self.skill.split("The agent prompt includes:", 1)[1].split("## Finding schema", 1)[0]
        self.assertIn("the «Severity» section", prompt)

    def test_calibration_is_scoped_by_mode(self):
        severity = self.skill.split("## Severity", 1)[1].split("## Synthesis", 1)[0]
        self.assertIn("In diff mode:", severity)
        self.assertIn("In spec mode:", severity)

    def test_downgrade_rule_spares_a_findings_and_fills_block(self):
        self.assertIn("`A` findings are exempt", self.skill)
        self.assertIn("fills the block itself", self.skill)
        self.assertIn("one step", self.skill)
        self.assertNotIn("is downgraded to `minor` during synthesis", self.skill)

    def test_unverified_criteria(self):
        self.assertIn("- unverified:", self.diff)

    def test_criteria_confirmed_in_phase_1(self):
        phase1 = self.diff.split("## Phase 1. Context", 1)[1].split("## Phase 1.5", 1)[0]
        self.assertIn("which sections this diff covers", phase1)
        self.assertIn("A file with a «Проверить» list is a task file", phase1)

    def test_walkthrough_batch_forms_and_unmentioned(self):
        for needle in ("accept all except", "accept blocker,major", "reject nit — причина", "без решения"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.spec)
        self.assertNotIn("both fall outside the format", self.spec)
        self.assertIn("compact table", self.skill)

    def test_minor_consistency_fixes(self):
        self.assertIn("`уверенность` of the finding whose severity was kept", self.skill)
        self.assertIn("(custom)", self.skill)
        self.assertIn("for intent only", self.diff)
        self.assertIn("criterion instead of `file:line`", self.diff)
        self.assertIn("and adds the test from `тест`", self.diff)
        self.assertIn("Pike, Cheney, Ford, Stonebraker, Valsorda", self.spec)
        self.assertIn("`AGENTS.md`", self.spec)
        for text in (self.diff, self.spec):
            self.assertIn("kirpr-onboard", text)

    def test_valsorda_covers_ssrf_tls_and_avoids_invented_cves(self):
        for needle in ("SSRF", "InsecureSkipVerify", "govulncheck", "`replace`", "Not a finding"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.valsorda)
        self.assertNotIn("unpinned versions", self.valsorda)
