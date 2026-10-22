---
name: expert-panel
description: "Multi-persona review of Go projects by a panel of experts (Rob Pike, Dave Cheney, Neal Ford, Michael Stonebraker, Filippo Valsorda plus custom ones). Two modes: spec review before planning and git diff review before committing. Explicit invocation only: Codex — $expert-panel spec <path> or $expert-panel diff [base]; Claude Code — /expert-panel spec <path> or /expert-panel diff [base]. Triggers (Russian names users type with the explicit call, not a reason to invoke on your own): ревью панелью экспертов, прогони через экспертов, ревью спеки, ревью диффа."
---

# expert-panel — review by a panel of experts

Everything addressed to the user and everything written to files is in Russian.

Runs an artifact through a panel of experts. Each expert is a separate agent with its own perspective; the orchestrator merges the results and walks through them with the user.

Runs only on explicit invocation. The panel is expensive: parallel agents, one per expert.

## Argument parsing

- `spec [path]` — spec review. Read `modes/spec.md` and follow it.
- `diff [base] [--spec path]` — change review. Read `modes/diff.md` and follow it.
- No arguments or unrecognized format — ask which mode is needed. Do not guess.

Paths to `modes/*.md` and `experts/*.md` are relative to this file's directory.

Before reading the expert personas, check that isolated delegation is available. If
it is not, say plainly that the panel cannot work without separate agents, and
stop: do not read `experts/*.md` and do not assemble the panel.

## Assembling the active panel

1. Core: `experts/pike.md`, `experts/cheney.md`, `experts/ford.md`, `experts/stonebraker.md`, `experts/valsorda.md`. Ids: `pike`, `cheney`, `ford`, `stonebraker`, `valsorda`.
2. Read `~/.config/kirpr/custom-experts.md` if it exists. Consider only what comes **after** the `<!-- BEGIN EXPERTS -->` line:
   - a `disable: <id>` line removes a core expert from the panel;
   - every `## <Имя> — <Домен>` section adds an expert;
   - a section whose `<Имя>` is the name of a core expert (for example `## Filippo Valsorda — …` from an older template) replaces that core expert's persona instead of adding a second one; the panel line marks it as «Valsorda (custom)». `disable: <id>` wins over such a section.
   Everything above the marker is instructions for a human. Ignore it entirely.
3. If no active experts remain — say so and stop.
4. Show the panel composition in one line before launching: «Панель: Pike, Cheney, Ford, Stonebraker, Valsorda».

## Launching the agents

One agent per expert. All agents are launched in one message so they run in parallel.

The agent prompt includes:

- Role: «Ты — <Имя>. Прочитай файл `<абсолютный путь к experts/<id>.md>` и ревьюй строго по нему.» For an overlay expert the text of its section is passed directly in the prompt — it has no file.
- Mode: `спека` or `diff` — the agent uses the matching checklist of its persona.
- Artifact: absolute path to the spec, or the path to the file with the saved diff.
- Relevant repository paths collected by the orchestrator.
- The prefix for finding `id`s. Core: Pike — `P`, Cheney — `C`, Ford — `F`, Stonebraker — `S`, Valsorda — `V`. Overlay experts get prefixes from the orchestrator — the first letter of the surname, or the first two on collision with a taken letter. `A` is reserved for the orchestrator's own acceptance and generated-code findings in diff mode and is never given to an expert.
- Severity: the «Severity» section below for the current mode — the table, the calibration paragraphs, and the rule that doubt is expressed in `уверенность`, not by raising severity.
- Restriction: read-only. The agent does not edit files, run tests or make commits.
- Language: every field of every finding and the good-decisions list is in Russian.
- The response schema (below).

The orchestrator does not read the persona files — only the agents need them.

## Finding schema

The agent returns a list of findings. Each has seven fields:

- `id` — the expert prefix plus an ordinal: `P1`, `C2`, `F3`, `S1`, `V2`. The agent receives the prefix in the prompt and does not choose it: agents run in parallel and do not see each other, so two experts with the same first letter of the surname would take one prefix and make the user's answer ambiguous.
- `severity` — `blocker`, `major`, `minor` or `nit`.
- `место` — spec section or `file:line`.
- `суть` — one sentence.
- `почему` — what it threatens.
- `правка` — what exactly to change.
- `уверенность` — `high`, `medium` or `low`: how sure the expert is that the problem is real.

In diff mode every `blocker` and `major` carries three more fields, so that the author closes the cause with a test instead of fitting the code to the example:

- `инвариант` — which invariant or contract is violated;
- `ломающий вход` — the concrete input or state that breaks it; for a numeric or global invariant («≤ N», «во всех ветках») — the worst case;
- `тест` — which test to add so the cause stays closed.

During synthesis, if a diff-mode `blocker` or `major` lacks these fields, the orchestrator fills the block itself when it follows from `суть` and `почему`; if it does not, the finding is lowered one step (`blocker` → `major`, `major` → `minor`) and the finding says so: «понижено: нет блока инвариант/вход/тест». `A` findings are exempt: for them `инвариант` is the criterion or the Review log decision, `ломающий вход` is «нет изменений» or the `file:line` of the conflicting change, `тест` is the matching «Проверить» item when there is one.

**A finding without the «правка» field is not accepted.** «Тут неясно» is not a finding. «В разделе X не описано поведение при недоступности Y; добавить абзац с ответом сервиса и поведением клиента» is a finding. Drop such agent responses during synthesis.

Separately the agent returns a list of good decisions — what was done right. At least one, if there is anything to name.

## Severity

| | In a spec | In a diff |
|---|---|---|
| `blocker` | leads to rework: wrong data model, unfulfillable requirement, internal contradiction | bug, vulnerability, data loss |
| `major` | significant gap: failure, migration or responsibility boundary not described | broken boundary or contract, wrong logic |
| `minor` | clarification that saves questions at the planning stage | improvement, non-critical |
| `nit` | wording | style, naming |

Report every finding, including minor ones and ones the expert is unsure about: a missed bug costs more than an extra remark, and the user filters in the walkthrough. Report everything in this single pass; do not hold findings back.

In diff mode: `blocker` and `major` are only what will actually fire — a bug on valid data or in a real scenario, a security hole, an unmet acceptance criterion, a broken boundary or contract, stale generated code, an untested branch of new functionality when the project has a test harness and the branch is reachable, scope creep that widens the risk.

In spec mode: `blocker` and `major` are what will lead to rework or to unpredictable behavior in the implementation — a wrong data model, a contradiction, an undescribed failure, migration or responsibility boundary.

Not `blocker` or `major` in either mode (→ `minor` or `nit`): protection against states excluded by the contract or by the calling code; a missing test for a trivial function or in a project without a test harness; a different name for the same behavior; «would be nice to harden»; style, wording preferences and comments that retell the code.

## Synthesis

1. **Dedup.** Findings about the same place with the same substance merge into one. Authors are listed comma-separated, severity is the maximum, `уверенность` of the finding whose severity was kept (raised only when the experts also agreed on severity), the merged finding keeps the `id` of that finding, the «правка» field is the most specific of those proposed. The same problem in several places is one finding with a list of `file:line`. Different bugs are not merged, even when they look alike.
2. **Conflicts.** If two findings demand mutually exclusive edits of one place — that is not a defect but a fork. Put them out as a pair in the «Конфликты» block with each expert's position. The verdict on a conflict is the user's, not the orchestrator's.
3. **Order.** All findings are shown, by descending severity, then by descending `уверенность`. Nothing is cut. `blocker` and `major` are shown as full blocks; `minor` and `nit` as one compact table with the columns `id | место | суть | правка | уверенность` — every finding stays visible and addressable by its `id`.
4. **Numbering** is kept from the agents: the user refers to `C2`, not to «второе сверху».

## General rules

- Writes nothing to disk until the user has explicitly accepted the findings.
- Does not run tests, linters or builds. If a check is needed — prints the command for the user to run.
- Makes no commits.
- Does not move between mode phases without confirmation where the phase requires it.
- Severity follows the calibration above; doubt is expressed in `уверенность`, not by raising severity.
