# Codex Dual Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert kirpr into one canonical set of skills that works in Codex and Claude Code, add safe dual-target installers, and install both targets on the current machine.

**Architecture:** The 12 Claude command bodies move into explicit-only skills; the old Claude command files become argument-forwarding adapters. Both platforms consume one runtime under `~/.local/share/kirpr`, one user configuration under `~/.config/kirpr`, and one transactional installer implementation shared by local, remote, and uninstall entry points.

**Tech Stack:** Markdown Agent Skills, Bash 3.2-compatible shell, Python 3 standard library and `unittest`, existing tracker scripts, Codex CLI 0.147.0, Claude Code 2.1.233.

**Spec:** `docs/superpowers/specs/2026-08-15-codex-dual-compatibility-design.md`

## Global Constraints

- Preserve all 12 existing Claude Code invocations under `/kirpr:*`.
- Add exactly 12 separate Codex invocations named `$kirpr-task-fetch`, `$kirpr-task-create`, `$kirpr-task-update`, `$kirpr-task-delete`, `$kirpr-tasks-decompose`, `$kirpr-tasks-review`, `$kirpr-tasks-adapt`, `$kirpr-tasks-push`, `$kirpr-adr-init`, `$kirpr-adr-write`, `$kirpr-adr-review`, and `$kirpr-text`.
- All kirpr skills are explicit-only; every `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`.
- Installed runtime is `~/.local/share/kirpr`; mutable user configuration is `~/.config/kirpr`; project state is `.kirpr`.
- Do not change tracker API behavior, Python CLI contracts, destructive confirmation rules, or task artifact formats.
- Keep Bash compatible with macOS Bash 3.2: no associative arrays, `mapfile`, `readarray`, or Bash 4 parameter features.
- Add no third-party runtime or test dependency.
- Never print tracker token values or configuration file contents in installer logs.
- Back up pre-existing same-name skills before replacement; preserve and normalize user configuration; stop before mutation on conflicting user data.
- Do not scan or rewrite `.claude` directories across user repositories.

## File Map

### New canonical command skills

Each directory below owns one workflow and contains `SKILL.md` plus
`agents/openai.yaml`:

```text
skills/kirpr-task-fetch/
skills/kirpr-task-create/
skills/kirpr-task-update/
skills/kirpr-task-delete/
skills/kirpr-tasks-decompose/
skills/kirpr-tasks-review/
skills/kirpr-tasks-adapt/
skills/kirpr-tasks-push/
skills/kirpr-adr-init/
skills/kirpr-adr-write/
skills/kirpr-adr-review/
skills/kirpr-text/
```

### Shared runtime and adapters

- `kirpr/config/tracker-runtime.md` — canonical tracker-to-script mapping.
- `kirpr/config/tracker.md.template` — platform-neutral user configuration.
- `kirpr/config/workflow.md` — decomposition workflow with neutral runtime paths and dual invocation help.
- `kirpr/config/templates.md` — decomposition templates with neutral runtime paths and dual invocation help.
- `commands/kirpr/*.md` — twelve thin Claude adapters; no business workflow.

### Existing skills to normalize

- `skills/expert-panel/SKILL.md`, `skills/expert-panel/modes/diff.md` — shared custom panel path and `.kirpr` ignore migration.
- `kirpr/config/custom-experts.md.template` — seed for shared user configuration, moved out of the installed skill tree.
- `skills/grill-me/SKILL.md`, `skills/grill-me/phases/lenses.md`, `skills/grill-me/phases/wrapup.md` — `.kirpr` project state, shared editorial prompt, dual invocation copy.
- `skills/kirpr-flow/SKILL.md`, `skills/kirpr-flow/modes/brainstorm.md`, `skills/kirpr-flow/prompts/*.md`, `skills/kirpr-flow/core/rules.md` — dual invocation copy and relative references instead of installed Claude paths.
- `skills/{expert-panel,grill-me,kirpr-flow}/agents/openai.yaml` — explicit-only metadata.

### Installer and tests

- `installer/lib.sh` — target parsing, path calculation, staging, migration, backup, manifest, rollback, and uninstall primitives.
- `install.sh` — local install orchestration only.
- `install-remote.sh` — archive download and delegation to `install.sh`.
- `uninstall.sh` — manifest-driven removal orchestration only.
- `tests/test_skill_contracts.py` — skill, metadata, path, and Claude adapter contracts.
- `tests/test_installer.py` — isolated install, migration, rollback, and uninstall tests.
- `README.md` — dual-platform usage and lifecycle documentation.

---

### Task 1: Tracker CRUD Skills and Claude Adapters

This task establishes the skill contract and migrates the four direct tracker operations without changing their confirmation behavior.

**Files:**
- Create: `tests/test_skill_contracts.py`
- Create: `kirpr/config/tracker-runtime.md`
- Create: `skills/kirpr-task-fetch/SKILL.md`
- Create: `skills/kirpr-task-fetch/agents/openai.yaml`
- Create: `skills/kirpr-task-create/SKILL.md`
- Create: `skills/kirpr-task-create/agents/openai.yaml`
- Create: `skills/kirpr-task-update/SKILL.md`
- Create: `skills/kirpr-task-update/agents/openai.yaml`
- Create: `skills/kirpr-task-delete/SKILL.md`
- Create: `skills/kirpr-task-delete/agents/openai.yaml`
- Modify: `commands/kirpr/task-fetch.md:1-17`
- Modify: `commands/kirpr/task-create.md:1-74`
- Modify: `commands/kirpr/task-update.md:1-78`
- Modify: `commands/kirpr/task-delete.md:1-59`
- Test: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: existing command bodies and Python CLIs `manage_youtrack.py`, `manage_jira.py`, `fetch_youtrack.py`, `fetch_jira.py`.
- Produces: helper `assert_explicit_skill(testcase, name)`, helper `assert_claude_adapter(testcase, command, skill)`, and four explicit skills that later installer tests enumerate.

- [ ] **Step 1: Write the failing skill and adapter contract tests**

Create `tests/test_skill_contracts.py` with repository-relative helpers and the first four expected skills:

```python
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
```

- [ ] **Step 2: Run the contract tests and verify the missing-skill failure**

Run: `python3 -m unittest tests.test_skill_contracts.TestTrackerCrudSkills -v`

Expected: FAIL with `FileNotFoundError` for `skills/kirpr-task-fetch/SKILL.md`.

- [ ] **Step 3: Add the platform-neutral tracker runtime contract**

Create `kirpr/config/tracker-runtime.md` with these exact mappings and stop rules:

```markdown
# Выбор runtime трекера

1. Прочитай `~/.config/kirpr/tracker.md`, секцию `## Активный трекер`.
2. `Трекер: YouTrack` использует:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_youtrack.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_youtrack.py`
   - push: `python3 ~/.local/share/kirpr/scripts/create_youtrack.py`
3. `Трекер: Jira` использует:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_jira.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_jira.py`
4. Если конфигурации нет, трекер не указан или операция не поддерживается
   выбранным трекером, остановись до запуска скрипта и назови точный файл,
   который нужно настроить.
```

- [ ] **Step 4: Move each CRUD workflow into its canonical skill**

For each row, copy the complete body of the source command into the destination
after the exact front matter shown; replace every tracker/config/script lookup
with a first initialization step that reads
`~/.local/share/kirpr/config/tracker-runtime.md`, and replace `$ARGUMENTS` with
“текст после явного вызова скила”. Keep dry-run, preview, issue-number confirmation,
and partial-failure reporting verbatim.

```text
commands/kirpr/task-fetch.md  -> skills/kirpr-task-fetch/SKILL.md
commands/kirpr/task-create.md -> skills/kirpr-task-create/SKILL.md
commands/kirpr/task-update.md -> skills/kirpr-task-update/SKILL.md
commands/kirpr/task-delete.md -> skills/kirpr-task-delete/SKILL.md
```

```yaml
---
name: kirpr-task-fetch
description: "Use only when explicitly invoked to fetch one YouTrack or Jira issue with its comments, links, and history."
---
```

Use the same structure with the exact names `kirpr-task-create`,
`kirpr-task-update`, and `kirpr-task-delete`; their descriptions must begin
`Use only when explicitly invoked` and name the mutation they perform.

- [ ] **Step 5: Add explicit-only Codex metadata and exact Claude adapters**

Each `agents/openai.yaml` has this shape, with the matching display name and
default prompt:

```yaml
interface:
  display_name: "kirpr task fetch"
  short_description: "Fetch one issue from the configured tracker"
  default_prompt: "Use $kirpr-task-fetch with the arguments I provide."
policy:
  allow_implicit_invocation: false
```

Replace each source command with this exact adapter, substituting the matching
skill name only:

````markdown
# Совместимый вызов kirpr

Полностью прочитай `~/.claude/skills/kirpr-task-fetch/SKILL.md` и следуй ему.

Аргументы явного вызова:

```text
$ARGUMENTS
```
````

- [ ] **Step 6: Run the focused tests and inspect forbidden paths**

Run: `python3 -m unittest tests.test_skill_contracts.TestTrackerCrudSkills -v`

Expected: 2 tests PASS.

Run: `rg -n '~/.claude/kirpr|\.Codex|\$ARGUMENTS' skills/kirpr-task-{fetch,create,update,delete}`

Expected: no matches.

- [ ] **Step 7: Commit the CRUD skill migration**

```bash
git add tests/test_skill_contracts.py kirpr/config/tracker-runtime.md \
  skills/kirpr-task-* commands/kirpr/task-*.md
git commit -m "feat: migrate tracker commands to dual-platform skills"
```

### Task 2: Decomposition Skills and Shared Workflow References

This task migrates the four decomposition operations and makes their shared
templates independent of Claude installation paths.

**Files:**
- Modify: `tests/test_skill_contracts.py`
- Create: `kirpr/config/custom-experts.md.template`
- Delete: `skills/expert-panel/custom-experts.md`
- Create: `skills/kirpr-tasks-decompose/SKILL.md`
- Create: `skills/kirpr-tasks-decompose/agents/openai.yaml`
- Create: `skills/kirpr-tasks-review/SKILL.md`
- Create: `skills/kirpr-tasks-review/agents/openai.yaml`
- Create: `skills/kirpr-tasks-adapt/SKILL.md`
- Create: `skills/kirpr-tasks-adapt/agents/openai.yaml`
- Create: `skills/kirpr-tasks-push/SKILL.md`
- Create: `skills/kirpr-tasks-push/agents/openai.yaml`
- Modify: `commands/kirpr/tasks-decompose.md:1-28`
- Modify: `commands/kirpr/tasks-review.md:1-173`
- Modify: `commands/kirpr/tasks-adapt.md:1-116`
- Modify: `commands/kirpr/tasks-push.md:1-70`
- Modify: `kirpr/config/workflow.md:1-86`
- Modify: `kirpr/config/templates.md:1-274`
- Test: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: `assert_explicit_skill`, `assert_claude_adapter`, and `tracker-runtime.md` from Task 1.
- Produces: four explicit decomposition skills and shared runtime documents with no platform-specific command syntax.

- [ ] **Step 1: Add failing decomposition contract tests**

Append a `TestDecompositionSkills` class with these cases and reuse both helpers:

```python
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
```

- [ ] **Step 2: Verify the new tests fail**

Run: `python3 -m unittest tests.test_skill_contracts.TestDecompositionSkills -v`

Expected: FAIL for missing `skills/kirpr-tasks-decompose/SKILL.md`.

- [ ] **Step 3: Move the four workflows and add their metadata**

Move complete command bodies according to this table:

```text
tasks-decompose -> kirpr-tasks-decompose
tasks-review    -> kirpr-tasks-review
tasks-adapt     -> kirpr-tasks-adapt
tasks-push      -> kirpr-tasks-push
```

Each `SKILL.md` starts with `name` equal to the destination directory and a
description beginning `Use only when explicitly invoked`. Each
`agents/openai.yaml` contains a matching display name, a one-line description,
the matching default prompt from this list, and the policy below:

```text
Use $kirpr-tasks-decompose with the arguments I provide.
Use $kirpr-tasks-review with the arguments I provide.
Use $kirpr-tasks-adapt with the arguments I provide.
Use $kirpr-tasks-push with the arguments I provide.
```

```yaml
policy:
  allow_implicit_invocation: false
```

Each source command becomes this adapter with the destination skill name:

````markdown
# Совместимый вызов kirpr

Полностью прочитай `~/.claude/skills/kirpr-tasks-decompose/SKILL.md` и следуй ему.

Аргументы явного вызова:

```text
$ARGUMENTS
```
````

Use exact runtime paths:

```text
~/.config/kirpr/tracker.md
~/.local/share/kirpr/config/tracker-runtime.md
~/.local/share/kirpr/config/workflow.md
~/.local/share/kirpr/config/templates.md
~/.local/share/kirpr/config/style-examples.md
~/.local/share/kirpr/scripts/create_youtrack.py
```

Every error message that formerly named only `/kirpr:tasks-decompose` must now
say: “Запустите `$kirpr-tasks-decompose` в Codex или
`/kirpr:tasks-decompose` в Claude Code.”

- [ ] **Step 4: Neutralize the shared workflow and templates**

In `workflow.md` and `templates.md`, replace all runtime reads under
`~/.claude/kirpr` with `~/.local/share/kirpr`, except tracker configuration,
which becomes `~/.config/kirpr/tracker.md`. Replace help text that names one
Claude command with both explicit invocation forms. Preserve headings, scoring
rubrics, artifact filenames, and generation order.

- [ ] **Step 5: Run tests and prove no Claude runtime path remains**

Run: `python3 -m unittest tests.test_skill_contracts.TestDecompositionSkills -v`

Expected: 2 tests PASS.

Run: `rg -n '~/.claude/kirpr|\.Codex|\$ARGUMENTS' skills/kirpr-tasks-* kirpr/config/{workflow,templates}.md`

Expected: no matches.

- [ ] **Step 6: Commit the decomposition migration**

```bash
git add tests/test_skill_contracts.py skills/kirpr-tasks-* \
  commands/kirpr/tasks-*.md kirpr/config/workflow.md kirpr/config/templates.md
git commit -m "feat: migrate decomposition commands to skills"
```

### Task 3: ADR and Editorial Skills

This task completes the 12 command migrations while retaining the repository's
tracker-aware ADR behavior and mandatory output-path behavior for text editing.

**Files:**
- Modify: `tests/test_skill_contracts.py`
- Create: `skills/kirpr-adr-init/SKILL.md`
- Create: `skills/kirpr-adr-init/agents/openai.yaml`
- Create: `skills/kirpr-adr-write/SKILL.md`
- Create: `skills/kirpr-adr-write/agents/openai.yaml`
- Create: `skills/kirpr-adr-review/SKILL.md`
- Create: `skills/kirpr-adr-review/agents/openai.yaml`
- Create: `skills/kirpr-text/SKILL.md`
- Create: `skills/kirpr-text/agents/openai.yaml`
- Modify: `commands/kirpr/adr-init.md:1-291`
- Modify: `commands/kirpr/adr-write.md:1-156`
- Modify: `commands/kirpr/adr-review.md:1-134`
- Modify: `commands/kirpr/text.md:1-17`
- Test: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: Task 1 contract helpers and shared runtime paths.
- Produces: the final four command-derived skills and the complete list `ALL_SKILLS` used by installer tests.

- [ ] **Step 1: Add failing ADR/editorial contract tests**

Append:

```python
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
```

- [ ] **Step 2: Verify the test fails for the first missing ADR skill**

Run: `python3 -m unittest tests.test_skill_contracts.TestAdrAndTextSkills -v`

Expected: FAIL for missing `skills/kirpr-adr-init/SKILL.md`.

- [ ] **Step 3: Move ADR workflows into three explicit skills**

Copy each source body into its matching skill. Use these runtime paths exactly:

```text
~/.local/share/kirpr/config/adr-templates.md
~/.local/share/kirpr/config/adr-review-rubric.md
~/.local/share/kirpr/config/agent-rules.md
~/.local/share/kirpr/config/tracker-runtime.md
~/.local/share/kirpr/scripts/validate_services.py
```

When a repository has `AGENTS.md`, treat its ADR sections as the Codex-native
equivalent of the existing `CLAUDE.md` sections. If both files exist, read both
and ask only when their ADR directory, naming, or services-map values conflict.
When writing new project guidance, update the file used by the active platform;
do not mirror the same section into both automatically.

Preserve K1–K6, R1–R7, calibration limits, tracker context, services validation,
and approval gates from the source commands. Do not adopt the installed
`kirpr-adr` behavior that skips tracker context and initialization.

- [ ] **Step 4: Move the editorial workflow and preserve its file contract**

Create `skills/kirpr-text/SKILL.md` from `commands/kirpr/text.md`, point it to
`~/.local/share/kirpr/prompts/text.md`, and preserve the rule that a requested
file mutation requires a confirmed destination before writing. Incorporate only
these compatible details from the backed-up Codex-native version: inspect the
surrounding document, preserve Markdown/code identifiers, and perform a final
placeholder/contradiction read.

- [ ] **Step 5: Add metadata, adapters, and the complete skill set constant**

For each skill, add `agents/openai.yaml` with a matching `display_name`, a
one-line `short_description`, `policy.allow_implicit_invocation: false`, and one
of these exact default prompts:

```text
Use $kirpr-adr-init with the arguments I provide.
Use $kirpr-adr-write with the arguments I provide.
Use $kirpr-adr-review with the arguments I provide.
Use $kirpr-text with the arguments I provide.
```

Replace each Claude source command with the thin adapter that reads the
matching `~/.claude/skills/kirpr-*/SKILL.md` path from the `CASES` table and
passes `$ARGUMENTS` inside a `text` fence. Add this constant to
`tests/test_skill_contracts.py`:

```python
ALL_SKILLS = (
    "kirpr-task-fetch", "kirpr-task-create", "kirpr-task-update",
    "kirpr-task-delete", "kirpr-tasks-decompose", "kirpr-tasks-review",
    "kirpr-tasks-adapt", "kirpr-tasks-push", "kirpr-adr-init",
    "kirpr-adr-write", "kirpr-adr-review", "kirpr-text",
    "expert-panel", "grill-me", "kirpr-flow",
)
```

- [ ] **Step 6: Run focused and existing Python tests**

Run: `python3 -m unittest tests.test_skill_contracts.TestAdrAndTextSkills -v`

Expected: 2 tests PASS.

Run: `python3 -m unittest discover -s tests -v`

Expected: all skill-contract and existing tracker tests PASS.

- [ ] **Step 7: Commit the ADR/editorial migration**

```bash
git add tests/test_skill_contracts.py skills/kirpr-adr-* skills/kirpr-text \
  commands/kirpr/adr-*.md commands/kirpr/text.md
git commit -m "feat: add Codex-native ADR and text skills"
```

### Task 4: Normalize Existing Skills and Project-State Migration

This task makes `expert-panel`, `grill-me`, and `kirpr-flow` portable and
explicit-only without changing their workflow guarantees.

**Files:**
- Modify: `tests/test_skill_contracts.py`
- Create: `skills/expert-panel/agents/openai.yaml`
- Create: `skills/grill-me/agents/openai.yaml`
- Create: `skills/kirpr-flow/agents/openai.yaml`
- Modify: `skills/expert-panel/SKILL.md:1-83`
- Modify: `skills/expert-panel/modes/diff.md:1-97`
- Modify: `skills/grill-me/SKILL.md:1-201`
- Modify: `skills/grill-me/phases/lenses.md:1-87`
- Modify: `skills/grill-me/phases/wrapup.md:1-95`
- Modify: `skills/kirpr-flow/SKILL.md:1-67`
- Modify: `skills/kirpr-flow/core/subagents.md:1-37`
- Modify: `skills/kirpr-flow/modes/brainstorm.md:1-199`
- Modify: `skills/kirpr-flow/core/rules.md:1-123`
- Modify: `skills/kirpr-flow/prompts/code-reviewer.md:1-90`
- Modify: `skills/kirpr-flow/prompts/implementer.md:1-162`
- Modify: `skills/kirpr-flow/prompts/plan-reviewer.md:1-60`
- Modify: `skills/kirpr-flow/prompts/re-review.md:1-60`
- Modify: `skills/kirpr-flow/prompts/spec-reviewer.md:1-53`
- Modify: `skills/kirpr-flow/prompts/task-reviewer.md:1-92`
- Test: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: `ALL_SKILLS` from Task 3 and the shared paths defined by the spec.
- Produces: 15 explicit-only portable skills; `TestGlobalSkillContracts` becomes the preflight authority for installer work.

- [ ] **Step 1: Add failing global portability tests**

Append:

```python
class TestGlobalSkillContracts(unittest.TestCase):
    FORBIDDEN = ("~/.claude/kirpr", ".Codex", "AskUserQuestion", "TodoWrite")

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
```

- [ ] **Step 2: Verify failures expose missing metadata and legacy paths**

Run: `python3 -m unittest tests.test_skill_contracts.TestGlobalSkillContracts -v`

Expected: FAIL for missing `skills/expert-panel/agents/openai.yaml` and report
legacy `.claude`/`.Codex` paths if present.

- [ ] **Step 3: Make expert-panel use shared user and project configuration**

Move the repository seed from `skills/expert-panel/custom-experts.md` to
`kirpr/config/custom-experts.md.template`, and set the skill's only active
custom-expert path to `~/.config/kirpr/custom-experts.md`. In diff mode, read
`.kirpr/expert-panel-ignore`; if it is absent and `.claude/expert-panel-ignore`
exists, show the two paths, ask before copying, and treat the legacy file as
read-only until answered. Update explicit invocation examples to `$expert-panel`
for Codex and `/expert-panel` for Claude Code.

- [ ] **Step 4: Make grill-me use `.kirpr` and the shared editorial prompt**

Use `.kirpr/grill-me/lenses.md` for all new writes. On first access, implement
this exact branch:

```text
new exists                         -> read/write new
new missing, legacy missing        -> create new only after normal path approval
new missing, legacy exists         -> show both paths; ask to copy
copy approved                      -> copy once, then read/write new
copy declined                      -> read legacy; do not write legacy
```

Point wrap-up to `~/.local/share/kirpr/prompts/text.md`. Show `$kirpr-text` and
`/kirpr:text` in fallback help. Replace invocation examples with paired Codex and
Claude forms without changing the stop protocol or session artifacts.

- [ ] **Step 5: Remove installed Claude paths from kirpr-flow prompts**

In prompt templates, replace `~/.claude/skills/kirpr-flow/core/rules.md` with the
relative instruction `Прочитай ../core/rules.md относительно каталога скила
kirpr-flow`. Update references to `grill-me` and `kirpr-flow` invocations to show
both platforms. Keep the no-git contract, fresh-agent requirements, severity
rules, and artifact paths unchanged.

Add an availability branch to `core/subagents.md`: `execute` and agent-backed
`review` stop when isolated delegation is unavailable and point to
`execute --inline`; optional spec/plan reviewers are skipped with disclosure.
In `expert-panel`, unavailable delegation stops before reading expert personas.
In `grill-me`, unavailable background delegation runs fact lookup sequentially
in the current session, while unavailable wrap-up delegation performs the same
draft-to-final fidelity check inline and discloses the fallback. These are the
only allowed sequential fallbacks.

- [ ] **Step 6: Add explicit-only metadata to all three skills**

Create `agents/openai.yaml` using these exact default prompts:

```yaml
# expert-panel
default_prompt: "Use $expert-panel with the arguments I provide."
# grill-me
default_prompt: "Use $grill-me with the topic or session path I provide."
# kirpr-flow
default_prompt: "Use $kirpr-flow with the mode and arguments I provide."
```

Each file also contains its matching `display_name`, `short_description`, and:

```yaml
policy:
  allow_implicit_invocation: false
```

- [ ] **Step 7: Run global contracts and inspect the diff**

Run: `python3 -m unittest tests.test_skill_contracts.TestGlobalSkillContracts -v`

Expected: 3 tests PASS.

Run: `git diff --check && rg -n '~/.claude/kirpr|\.Codex|AskUserQuestion|TodoWrite' skills`

Expected: `git diff --check` succeeds and `rg` prints no matches.

- [ ] **Step 8: Commit portable existing skills**

```bash
git add tests/test_skill_contracts.py kirpr/config/custom-experts.md.template \
  skills/expert-panel skills/grill-me skills/kirpr-flow
git commit -m "feat: make existing skills platform neutral"
```

### Task 5: Target Selection and Clean Installation

This task replaces hard-coded copying with one Bash 3.2-compatible installer
library and proves clean installs for each target.

**Files:**
- Create: `installer/lib.sh`
- Create: `tests/test_installer.py`
- Modify: `install.sh:1-240`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: repository skill tree and `ALL_SKILLS` names from Task 3.
- Produces shell functions `parse_args`, `choose_target`, `resolve_paths`,
  `validate_bundle`, `stage_bundle`, `prepare_user_config`,
  `install_staged_bundle`, and `write_manifest`; supports internal test seams
  `KIRPR_INSTALL_ROOT` and `KIRPR_INPUT_FILE`.

- [ ] **Step 1: Write failing clean-install tests**

Create `tests/test_installer.py` with a subprocess harness that never changes
the real home directory:

```python
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
            env.pop("KIRPR_INPUT_FILE", None)
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

    def test_codex_target(self):
        self.run_script("install.sh", "--target", "codex")
        self.assert_skills(self.root / ".agents" / "skills")
        self.assertFalse((self.root / ".claude" / "commands" / "kirpr").exists())

    def test_claude_target(self):
        self.run_script("install.sh", "--target", "claude")
        self.assert_skills(self.root / ".claude" / "skills")
        self.assertEqual(len(list((self.root / ".claude" / "commands" / "kirpr").glob("*.md"))), 12)

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

    def test_unknown_target_fails_without_writes(self):
        result = self.run_script("install.sh", "--target", "other", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".agents").exists())
        self.assertIn("claude|codex|all", result.stderr)
```

- [ ] **Step 2: Run the clean-install tests and verify failure**

Run: `python3 -m unittest tests.test_installer.TestCleanInstall -v`

Expected: FAIL because the existing installer rejects `--target` semantics and
writes only Claude paths.

- [ ] **Step 3: Implement Bash 3.2 argument and path interfaces**

Create `installer/lib.sh` with indexed `KIRPR_SKILLS`, `KIRPR_COMMANDS`, and
these exact public functions:

```bash
parse_args()                 # sets KIRPR_TARGET; rejects unknown arguments
choose_target()              # maps 1=claude, 2=codex, 3=all from KIRPR_INPUT
resolve_paths()              # derives all paths from KIRPR_INSTALL_ROOT or HOME
validate_bundle()            # requires every SKILL.md, openai.yaml, command, config, prompt, script
stage_bundle()               # copies complete runtime/skills/adapters into KIRPR_STAGE_DIR
prepare_user_config()        # seeds custom experts and prompts for tracker on a clean root
install_staged_bundle()      # installs only the selected target(s)
write_manifest()             # writes version/target/path records via temp file + mv
```

Initialize the test seams without repurposing system variables:

```bash
KIRPR_ROOT="${KIRPR_INSTALL_ROOT:-$HOME}"
KIRPR_INPUT="${KIRPR_INPUT_FILE:-/dev/tty}"
KIRPR_CONFIG_DIR="$KIRPR_ROOT/.config/kirpr"
KIRPR_RUNTIME_DIR="$KIRPR_ROOT/.local/share/kirpr"
KIRPR_CODEX_SKILLS_DIR="$KIRPR_ROOT/.agents/skills"
KIRPR_CLAUDE_SKILLS_DIR="$KIRPR_ROOT/.claude/skills"
KIRPR_CLAUDE_COMMANDS_DIR="$KIRPR_ROOT/.claude/commands/kirpr"
```

The manifest format is line-oriented and never sourced as shell code:

```text
version<TAB>1
target<TAB>codex
path<TAB>codex<TAB>/absolute/managed/path
path<TAB>shared<TAB>/absolute/runtime/path
```

- [ ] **Step 4: Reduce install.sh to orchestration**

`install.sh` must source `installer/lib.sh`, parse or prompt for target, create a
temporary stage with `mktemp -d`, trap cleanup, validate before creating
destination paths, stage, install, and write the manifest. Keep tracker setup
behind a function call that reads from `KIRPR_INPUT`; choosing `3` creates no
tracker file and prints the shared config path.

```bash
main() {
    parse_args "$@"
    [ -n "$KIRPR_TARGET" ] || choose_target
    resolve_paths
    validate_bundle "$REPO_DIR"
    KIRPR_STAGE_DIR="$(mktemp -d)"
    trap 'rm -rf "$KIRPR_STAGE_DIR"' EXIT
    stage_bundle "$REPO_DIR"
    prepare_user_config
    install_staged_bundle
    write_manifest
}
```

- [ ] **Step 5: Run clean install tests and shell validation**

Run: `python3 -m unittest tests.test_installer.TestCleanInstall -v`

Expected: 6 tests PASS.

Run: `bash -n install.sh installer/lib.sh && shellcheck install.sh installer/lib.sh`

Expected: both commands exit 0.

- [ ] **Step 6: Commit clean target installation**

```bash
git add installer/lib.sh install.sh tests/test_installer.py
git commit -m "feat: add dual-target kirpr installer"
```

### Task 6: Migration, Backup, Rollback, and Manifest-Driven Uninstall

This task makes installation reversible and handles the current machine's
legacy imports without guessing between conflicting user files.

**Files:**
- Modify: `installer/lib.sh`
- Modify: `install.sh`
- Modify: `uninstall.sh:1-79`
- Modify: `kirpr/config/tracker.md.template`
- Modify: `tests/test_installer.py`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: Task 5 paths, staging, and line-oriented manifest.
- Produces shell functions `normalize_tracker`, `select_user_file`, `backup_path`, `record_backup`, `rollback_install`, `uninstall_target`, and `restore_displaced`; manifest record kinds `target`, `path`, and `backup`.

- [ ] **Step 1: Add failing migration and uninstall tests**

Add tests for these exact cases:

```python
class TestMigrationAndUninstall(InstallerCase):
    def seed(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_migrates_and_normalizes_claude_tracker(self):
        self.seed(".claude/kirpr/config/tracker.md", "Трекер: Jira\nСкрипт: `python3 ~/.claude/kirpr/scripts/fetch_jira.py X`\nURL: https://jira/browse/X\n")
        self.run_script("install.sh", "--target", "codex")
        text = (self.root / ".config/kirpr/tracker.md").read_text(encoding="utf-8")
        self.assertIn("Трекер: Jira", text)
        self.assertNotIn("Скрипт:", text)
        self.assertNotIn(".claude", text)

    def test_conflicting_custom_experts_stop_before_skill_replacement(self):
        self.seed(".config/kirpr/custom-experts.md", "shared\n")
        self.seed(".claude/skills/expert-panel/custom-experts.md", "claude\n")
        marker = self.seed(".agents/skills/expert-panel/marker", "original\n")
        result = self.run_script("install.sh", "--target", "codex", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original\n")

    def test_backs_up_displaced_codex_skills_and_retired_adr(self):
        self.seed(".agents/skills/kirpr-text/old", "text\n")
        self.seed(".agents/skills/kirpr-adr/SKILL.md", "legacy adr\n")
        self.run_script("install.sh", "--target", "codex")
        backups = list((self.root / ".config/kirpr/backups").rglob("old"))
        self.assertEqual(len(backups), 1)
        self.assertFalse((self.root / ".agents/skills/kirpr-adr").exists())

    def test_reinstall_preserves_user_files(self):
        self.run_script("install.sh", "--target", "all")
        custom = self.seed(".config/kirpr/custom-experts.md", "mine\n")
        self.run_script("install.sh", "--target", "all")
        self.assertEqual(custom.read_text(encoding="utf-8"), "mine\n")

    def test_uninstall_codex_leaves_claude_runtime_and_config(self):
        self.run_script("install.sh", "--target", "all")
        self.run_script("uninstall.sh", "--target", "codex")
        self.assertFalse((self.root / ".agents/skills/kirpr-text").exists())
        self.assertTrue((self.root / ".claude/skills/kirpr-text").exists())
        self.assertTrue((self.root / ".local/share/kirpr").exists())
        self.assertTrue((self.root / ".config/kirpr").exists())

    def test_failed_install_rolls_back_and_keeps_old_manifest(self):
        marker = self.seed(".agents/skills/kirpr-text/marker", "original\n")
        manifest = self.seed(".config/kirpr/install-manifest", "version\t1\n")
        result = self.run_script(
            "install.sh", "--target", "codex", check=False,
            extra_env={"KIRPR_TEST_FAIL_AFTER_INSTALL": "1"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original\n")
        self.assertEqual(manifest.read_text(encoding="utf-8"), "version\t1\n")
```

- [ ] **Step 2: Run migration tests and verify failure**

Run: `python3 -m unittest tests.test_installer.TestMigrationAndUninstall -v`

Expected: FAIL because migration, backup records, retired-skill handling, and
targeted uninstall are not implemented.

- [ ] **Step 3: Make tracker configuration platform-neutral**

Remove every `Скрипт:` line from `tracker.md.template`. Keep active tracker,
URL, environment-variable names, and alternative tracker documentation.
Implement `normalize_tracker SOURCE DEST` as an `awk` copy that removes only
lines beginning `Скрипт:`; compare normalized temporary files when deciding
whether tracker candidates conflict.

- [ ] **Step 4: Implement deterministic user-data selection**

`select_user_file KIND DEST CANDIDATE...` must:

```text
discard missing candidates
normalize tracker candidates before comparison
deduplicate byte-identical candidates
return without writing when DEST already equals the sole normalized value
copy the sole value when exactly one distinct value remains
print KIND and conflicting paths, then return non-zero when values differ
```

With no custom-expert candidate, seed
`~/.config/kirpr/custom-experts.md` from
`kirpr/config/custom-experts.md.template`. With no tracker candidate, run the
existing tracker setup prompt; choosing “None” leaves `tracker.md` absent.

Use candidates in this order:

```text
tracker: ~/.config/kirpr/tracker.md
         ~/.claude/kirpr/config/tracker.md
         ~/.codex/kirpr/config/tracker.md
custom:  ~/.config/kirpr/custom-experts.md
         ~/.claude/skills/expert-panel/custom-experts.md
         ~/.agents/skills/expert-panel/custom-experts.md
```

- [ ] **Step 5: Implement persistent backup and rollback records**

Before replacing a destination not owned by the previous manifest, copy it to
`~/.config/kirpr/backups/YYYYMMDD-HHMMSS/<path-relative-to-install-root>` and add:

```text
backup<TAB>codex<TAB>/original/absolute/path<TAB>/backup/absolute/path
```

Treat `~/.agents/skills/kirpr-adr` as a retired collision during Codex install:
back it up, record it, then remove it from the active selector. Back up existing
`kirpr-text`, `expert-panel`, `grill-me`, and `kirpr-flow` before first takeover.

Maintain a per-run rollback directory for every managed path touched during an
update. Trap non-zero exit after mutation, restore those paths, leave the old
manifest intact, and print only restored path names.

Support `KIRPR_TEST_FAIL_AFTER_INSTALL=1` only as a test injection point: after
the first destination replacement it returns status 90, allowing the rollback
test to prove restoration. Production runs never set this task-specific value.

- [ ] **Step 6: Rewrite uninstall.sh around manifest ownership**

Source `installer/lib.sh`, reuse target parsing, and remove only manifest `path`
records belonging to the selected target. Keep runtime while either target
remains. Preserve `~/.config/kirpr` unless the user separately confirms deletion.
When backup records exist, ask once whether to restore displaced content; on
approval, restore each original path only when the current path is absent.

- [ ] **Step 7: Run migration, uninstall, shell, and full Python tests**

Run: `python3 -m unittest tests.test_installer.TestMigrationAndUninstall -v`

Expected: 6 tests PASS.

Run: `bash -n install.sh uninstall.sh installer/lib.sh && shellcheck install.sh uninstall.sh installer/lib.sh`

Expected: exit 0.

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 8: Commit transactional migration and uninstall**

```bash
git add installer/lib.sh install.sh uninstall.sh kirpr/config/tracker.md.template tests/test_installer.py
git commit -m "feat: add safe kirpr migration and uninstall"
```

### Task 7: Remote Installer and Dual-Platform Documentation

This task removes the duplicated remote file list and documents the exact user
experience for both platforms.

**Files:**
- Modify: `tests/test_installer.py`
- Create: `tests/test_documentation.py`
- Modify: `install-remote.sh:1-225`
- Modify: `README.md:1-189`
- Test: `tests/test_installer.py`
- Test: `tests/test_documentation.py`

**Interfaces:**
- Consumes: `install.sh --target claude|codex|all` and manifest behavior from Tasks 5–6.
- Produces: archive-based remote delegation and documented local/remote commands.

- [ ] **Step 1: Add failing remote and README tests**

Add `TestRemoteInstall.test_archive_delegates_target` to
`tests/test_installer.py`. It builds a local tar.gz of the repository, creates a
fake curl executable, passes its absolute path through `KIRPR_CURL_BIN`, and
asserts the remote script delegates `--target codex` to the archived installer.
The fake curl parses `-o DEST` and copies the fixture archive to `DEST`; it must
not use the network.

Create `tests/test_documentation.py`:

```python
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
```

- [ ] **Step 2: Run new tests and verify failure**

Run: `python3 -m unittest tests.test_documentation -v`

Expected: FAIL because README does not mention Codex invocations or targets.

- [ ] **Step 3: Replace the remote file list with archive delegation**

`install-remote.sh` must parse and preserve all arguments, download
`https://github.com/jerrdasur/kirpr-claude-toolset/archive/refs/heads/main.tar.gz`
to a `mktemp -d` directory, extract it, verify `install.sh` and
`installer/lib.sh`, then execute:

```bash
"$EXTRACTED_DIR/install.sh" "$@"
```

Use `KIRPR_CURL_BIN="${KIRPR_CURL_BIN:-curl}"` as the only download test seam.
Trap removal of the temporary directory. A download or extraction failure must
exit before invoking the local installer.

- [ ] **Step 4: Rewrite README around dual-platform use**

Change the title and introduction to name Claude Code and Codex. For every
operation table, add a Codex column with its exact `$kirpr-*` invocation. Update
existing skill examples to show `$skill` for Codex and `/skill` for Claude.

Document:

```text
local interactive: ./install.sh
local explicit:    ./install.sh --target claude|codex|all
remote explicit:   curl -fsSL URL | sh -s -- --target codex
runtime:           ~/.local/share/kirpr
configuration:     ~/.config/kirpr
Codex skills:      ~/.agents/skills
Claude skills:     ~/.claude/skills
Claude adapters:   ~/.claude/commands/kirpr
```

Explain backup/conflict behavior, project `.kirpr` migration, targeted uninstall,
and that tokens remain environment variables. Remove claims that configuration
lives under `~/.claude/kirpr`.

- [ ] **Step 5: Run remote, documentation, and full tests**

Run: `python3 -m unittest tests.test_installer.TestRemoteInstall tests.test_documentation -v`

Expected: all remote and README tests PASS.

Run: `bash -n install-remote.sh && shellcheck install-remote.sh`

Expected: exit 0.

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit remote installation and documentation**

```bash
git add install-remote.sh README.md tests/test_installer.py tests/test_documentation.py
git commit -m "docs: add Codex installation and usage"
```

### Task 8: Full Verification and Installation on This Machine

This task proves the repository and installed result without performing any
tracker mutation.

**Files:**
- Verify: all files changed by Tasks 1–7
- External install targets: `~/.agents/skills`, `~/.claude/skills`, `~/.claude/commands/kirpr`, `~/.local/share/kirpr`, `~/.config/kirpr`
- Test: complete `tests/` suite and two CLI discovery smoke checks

**Interfaces:**
- Consumes: completed repository, installers, manifest, and current local Claude/Codex installations.
- Produces: verified dual installation with recoverable backups of displaced `kirpr-adr`, `kirpr-text`, `expert-panel`, `grill-me`, and `kirpr-flow`.

- [ ] **Step 1: Run every repository verification from a clean status snapshot**

Run:

```bash
git status --short
python3 -m unittest discover -s tests -v
bash -n install.sh install-remote.sh uninstall.sh installer/lib.sh
shellcheck install.sh install-remote.sh uninstall.sh installer/lib.sh
git diff --check
```

Expected: only intentional task changes are present before their commits; all
tests and validators exit 0; `git diff --check` prints nothing.

- [ ] **Step 2: Inspect the real migration inputs without printing secrets**

Run existence and hash-only checks for:

```text
~/.config/kirpr/tracker.md
~/.claude/kirpr/config/tracker.md
~/.config/kirpr/custom-experts.md
~/.claude/skills/expert-panel/custom-experts.md
~/.agents/skills/expert-panel/custom-experts.md
~/.agents/skills/kirpr-adr
~/.agents/skills/kirpr-text
```

Expected: paths and SHA-256 hashes only. If user-data hashes conflict, stop and
report the paths; do not install until the user resolves them.

- [ ] **Step 3: Install both targets using the explicit non-destructive target**

Run: `./install.sh --target all`

Expected: existing user data is migrated or preserved, displaced Codex skills
are named in a dated backup, 15 skills are installed for each platform, 12
Claude adapters are installed, and the manifest records both targets.

- [ ] **Step 4: Verify installed files and forbidden paths**

Run:

```bash
python3 -m unittest tests.test_skill_contracts -v
rg -n '~/.claude/kirpr|\.Codex|AskUserQuestion|TodoWrite' \
  ~/.agents/skills/{kirpr-*,expert-panel,grill-me} \
  ~/.claude/skills/{kirpr-*,expert-panel,grill-me}
```

Expected: contract tests PASS and `rg` prints no matches. Confirm separately that
`~/.agents/skills/kirpr-adr` no longer exists and its backup does.

- [ ] **Step 5: Start read-only discovery smoke checks**

Run Codex in a new process:

```bash
codex exec --sandbox read-only --ask-for-approval never -C "$PWD" \
  'Report whether these installed skills are available without opening or running them: kirpr-task-fetch, kirpr-task-create, kirpr-task-update, kirpr-task-delete, kirpr-tasks-decompose, kirpr-tasks-review, kirpr-tasks-adapt, kirpr-tasks-push, kirpr-adr-init, kirpr-adr-write, kirpr-adr-review, kirpr-text, expert-panel, grill-me, kirpr-flow.'
```

Expected: all 15 names reported available; no skill is invoked.

Run Claude Code with tools disabled:

```bash
claude --print --tools "" --permission-mode dontAsk --no-session-persistence \
  'Without invoking them, report whether /kirpr:task-fetch, /kirpr:adr-write, and /kirpr:text are available.'
```

Expected: all three representative adapters reported available; no command is
invoked.

- [ ] **Step 6: Report installation evidence**

Report the test count, both CLI versions, installed target paths, manifest path,
backup path, and smoke-check results. Do not print tracker URLs, tokens, or the
contents of `tracker.md` and `custom-experts.md`.
