# Decomposition workflow: phases

The goal is not a list of tasks but a verified technical solution from which the tasks follow on their own. The order of phases is mandatory: a solution without research and a problem statement is a guess.

## Phase 1: Fetch from the tracker

0. Read `.kirpr/workspace.md` in the current directory (section «Project memory» of `templates.md`). Missing — say in one line that the workspace map was not found and `$kirpr-onboard` in Codex or `/kirpr:onboard` in Claude Code creates it, then continue without memory.
1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its runtime-selection instruction for the fetch operation exactly. It reads `~/.config/kirpr/tracker.md` and determines the script for the current tracker.
2. Run the script with the task number — it prints summary, description and comments.
3. If the script returned an error — **stop** and tell the user.
4. Extract the numbers of related tasks from the description and comments and load them with the same script (up to 50). Check whether child issues already exist in the tracker.
5. Show the user: title, description, related tasks, child issues found in the tracker.
6. Create the task directory (lowercase number, e.g. `sas-200/`) and `source.md` from the template in `~/.local/share/kirpr/config/templates.md`.
7. For every service on the scenario's path, read `<path>/.kirpr/memory.md` by the path from the workspace table. Missing — one line, continue. Memory files are read, never edited here.

The task description is the author's hypothesis, not a fact. Its claims («висит час», «падает из-за X») are verified in Phase 2 like everything else.

## Phase 2: Research

A fact that a tool can obtain is obtained with a tool. The user is asked only about what exists neither in code, nor in data, nor in documentation — one question at a time, after the research, not instead of it.

**2a — Code of every participant, end to end.** From the description, identify the services and repositories on the scenario's path and read them in full, not by headings: entry points (RPC, CLI, cron), the data path from entry to storage, state machines and allowed transitions, error handling and retries, existing tests and fixtures, infrastructure specs (orchestration, CI, alerting), generated artifacts (clients, API schemas). Record `file:function` for every fact. Check that repository branches are current. Traps and lessons from `memory.md` are facts of research: cite them as `L-NNN` where they shape a finding.

**2b — Primary sources on production behavior.** Collect alerts, logs and metrics for the affected components for the incident (if there was one) and for a representative period (e.g. 30 days). If there is no production data or the task does not concern it — state that explicitly in `research.md` rather than skipping the step silently. Build a «время / компонент / событие» table and a quantitative picture: how many times, which outcomes, which combinations. This step is usually enough to confirm or refute the task's premise.

**2c — Vendor and prior art.** Documentation and source code of the systems in use (orchestrator, DB, libraries) for the affected mechanisms; known issues and bugs; how analogues in other ecosystems solve the same problem. Verify claimed capabilities, do not assume them.

**2d — Questions to the user.** Only about what cannot be found out on your own: responsibility boundaries between layers, who needs the result, what counts as acceptable. One question at a time; the next depends on the answer.

**Artifact:** `research.md` in the task directory, from the template in `templates.md`: how it works now (with `file:function`), what the data showed (tables), what the vendor and prior art say (with links), what remains unverified. Show it to the user and wait for remarks.

## Phase 3: Problem statement

**Before this phase** read `~/.local/share/kirpr/config/style-examples.md` — it holds reference examples of a problem statement, a `SOLUTION.md`, task texts and a `research.md` fragment.

One paragraph or less, in terms of a contract or invariant between components: «между A и B одно сообщение X, исход Y передать нечем». Consequences — delays, alerts, retries, extra load — are not part of the statement: they are symptoms.

Checks:
- If the task's premise was not confirmed by facts — say so explicitly and state the problem from the facts, not from the description.
- If the statement cannot be read without knowing the code — simplify.
- If the user asks «суть в чём?» — the statement is vague, redo it.

Agree the statement with the user before moving to the solution. Write it as the «Проблема» section of `SOLUTION.md`.

## Phase 4: Solution

**4a — Options.** List the options briefly, with facts for and against from Phase 2, and name the recommended one. An option contradicted by a fact is not offered.

**4b — Solution rules.**
- Facts and verdicts are separated: the component that observes an event reports the fact; the decision is made by the component that owns the state, from the authoritative source. A message name carries the semantics of a fact, not a verdict.
- Responsibility boundaries accepted by the user are not violated: a mechanism that belongs to another layer (retries, orchestration) is neither duplicated nor bypassed while a solution exists inside its own layer.
- One service — one task — one MR.
- Every claim is verified against code, data or vendor sources. Anything unverified is marked «подтвердить на dev», not presented as a fact.

**4c — Solution text.** One sentence for the mechanism plus the changes per service. No «Принцип», «Эффект», «Что не меняем», «Порядок деплоя», «Проверить» sections and no how-to. The template is in `templates.md`.

**4d — Critique.** Show the solution. On every objection from the user, return to the problem statement rather than defending the option; if the objection rests on a fact, the option is discarded. If the user asks for justification — give facts and a trade-off table, do not change position silently.

**4e — Sentence-by-sentence cleanup.** For every sentence in the per-service sections (leave the «Проблема» section alone): is it a change? is it a decision inside a change? does it repeat another sentence? is it true? If a sentence can be deleted and the developer would do the same thing — delete it. «Как сейчас» and retellings of existing code are always deleted.

**Artifact:** `SOLUTION.md`. Agree it with the user. If the solution replaced an earlier one — the old one is not described; `research.md` records in one line what was rejected and why.

## Phase 5: Decomposition

1. One task per service or repository from `SOLUTION.md`. If a service has several changes that are safe on their own — still one task, one MR.
2. Task text uses the short format from `templates.md`: heading `{сервис}: {название}`, 3–6 verb steps, a «Проверить» list. No metadata, estimates or justifications.
3. Task order defines deployment order. A tracker dependency is created only where it is technical (client after server).
4. Show all texts at once, agree the edits.
5. Check against memory: no task repeats a situation recorded as a lesson `L-NNN` of its service; the «Проверить» list uses commands from `## Как проверять` of that service, not invented ones.
6. Go through the checklist from `templates.md` and show the result. Not passed — return to editing.

## Phase 6: Generate files

Format references are in `~/.local/share/kirpr/config/style-examples.md` (read before Phase 3).

Create in the task directory, from the templates in `templates.md`:
1. `source.md` (if not created yet).
2. `research.md` (if not written in Phase 2).
3. `SOLUTION.md` (if not written in Phase 4) — problem statement and solution.
4. `00-overview.md` — task order, dependencies, file map.
5. `NN-service.md` — one file per task.
6. `.context.md` — the session context cache. **Mandatory step**: without it `$kirpr-tasks-adapt` and `$kirpr-tasks-review` in Codex, or `/kirpr:tasks-adapt` and `/kirpr:tasks-review` in Claude Code, cannot use the fast context-loading path.

Show the list of created files. Check that `.context.md` was created.
