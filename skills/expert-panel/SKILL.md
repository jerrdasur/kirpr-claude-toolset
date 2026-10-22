---
name: expert-panel
description: "Multi-persona review of Go projects by a panel of experts (Rob Pike, Dave Cheney, Neal Ford, Michael Stonebraker plus custom ones). Two modes: spec review before planning and git diff review before committing. Explicit invocation only: Codex — $expert-panel spec <path> or $expert-panel diff [base]; Claude Code — /expert-panel spec <path> or /expert-panel diff [base]. Triggers (Russian names users type with the explicit call, not a reason to invoke on your own): ревью панелью экспертов, прогони через экспертов, ревью спеки, ревью диффа."
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

1. Core: `experts/pike.md`, `experts/cheney.md`, `experts/ford.md`, `experts/stonebraker.md`. Ids: `pike`, `cheney`, `ford`, `stonebraker`.
2. Read `~/.config/kirpr/custom-experts.md` if it exists. Consider only what comes **after** the `<!-- BEGIN EXPERTS -->` line:
   - a `disable: <id>` line removes a core expert from the panel;
   - every `## <Имя> — <Домен>` section adds an expert.
   Everything above the marker is instructions for a human. Ignore it entirely.
3. If no active experts remain — say so and stop.
4. Show the panel composition in one line before launching: «Панель: Pike, Cheney, Ford, Stonebraker».

## Launching the agents

One agent per expert. All agents are launched in one message so they run in parallel.

The agent prompt includes:

- Role: «Ты — <Имя>. Прочитай файл `<абсолютный путь к experts/<id>.md>` и ревьюй строго по нему.» For an overlay expert the text of its section is passed directly in the prompt — it has no file.
- Mode: `спека` or `diff` — the agent uses the matching checklist of its persona.
- Artifact: absolute path to the spec, or the path to the file with the saved diff.
- Relevant repository paths collected by the orchestrator.
- The prefix for finding `id`s. Core: Pike — `P`, Cheney — `C`, Ford — `F`, Stonebraker — `S`. Overlay experts get prefixes from the orchestrator — the first letter of the surname, or the first two on collision with a taken letter.
- Restriction: read-only. The agent does not edit files, run tests or make commits.
- Language: every field of every finding and the good-decisions list is in Russian.
- The response schema (below).

The orchestrator does not read the persona files — only the agents need them.

## Finding schema

The agent returns a list of findings. Each has six fields:

- `id` — the expert prefix plus an ordinal: `P1`, `C2`, `F3`, `S1`. The agent receives the prefix in the prompt and does not choose it: agents run in parallel and do not see each other, so two experts with the same first letter of the surname would take one prefix and make the user's answer ambiguous.
- `severity` — `blocker`, `major`, `minor` or `nit`.
- `место` — spec section or `file:line`.
- `суть` — one sentence.
- `почему` — what it threatens.
- `правка` — what exactly to change.

**A finding without the «правка» field is not accepted.** «Тут неясно» is not a finding. «В разделе X не описано поведение при недоступности Y; добавить абзац с ответом сервиса и поведением клиента» is a finding. Drop such agent responses during synthesis.

Separately the agent returns a list of good decisions — what was done right. At least one, if there is anything to name.

## Severity

| | In a spec | In a diff |
|---|---|---|
| `blocker` | leads to rework: wrong data model, unfulfillable requirement, internal contradiction | bug, vulnerability, data loss |
| `major` | significant gap: failure, migration or responsibility boundary not described | architectural problem, wrong logic |
| `minor` | clarification that saves questions at the planning stage | improvement, non-critical |
| `nit` | wording | style, naming |

## Synthesis

1. **Dedup.** Findings about the same place with the same substance merge into one. Authors are listed comma-separated, severity is the maximum, the «правка» field is the most specific of those proposed.
2. **Conflicts.** If two findings demand mutually exclusive edits of one place — that is not a defect but a fork. Put them out as a pair in the «Конфликты» block with each expert's position. The verdict on a conflict is the user's, not the orchestrator's.
3. **Limits.** Show in full no more than 3 `blocker` and 5 `major` — the heaviest. Everything else — `blocker` and `major` beyond the limit, and all `minor` and `nit` — collapse into one line each under the «Ниже порога» heading. No finding is thrown away, but the report is for decisions, not for volume.
4. **Numbering** is kept from the agents: the user refers to `C2`, not to «второе сверху».

## General rules

- Writes nothing to disk until the user has explicitly accepted the findings.
- Does not run tests, linters or builds. If a check is needed — prints the command for the user to run.
- Makes no commits.
- Does not move between mode phases without confirmation where the phase requires it.
- When in doubt about severity, picks the higher one.
