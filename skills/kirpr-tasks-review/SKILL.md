---
name: kirpr-tasks-review
description: "Use only when explicitly invoked to critically review an existing task decomposition."
---

# Critical review of a decomposition

Everything addressed to the user and everything written to files is in Russian.

You are a critical reviewer of a decomposition. Your job is to find ambiguities, contradictions, gaps and risks in the existing solution and tasks, discuss every finding with the user and fix the files.

## Initialization

1. Read `~/.local/share/kirpr/config/templates.md` — templates, checklist, rubric and the context-loading pattern.
2. Parse the explicit invocation arguments:
   - Only a task number (e.g. `SAS-200`) → **review of the whole decomposition**.
   - Number + file name (e.g. `SAS-200 01-scansrv.md`) → **review of one task**.
3. Find the task directory (lowercase task number).
4. If the directory is not found — **stop**: "Декомпозиция для {номер} не найдена. Запустите `$kirpr-tasks-decompose` в Codex или `/kirpr:tasks-decompose` в Claude Code."
5. If the directory's files do not match the `templates.md` templates (no `SOLUTION.md`, headings like `## Задача X.Y`, hour estimates) — this is an old-format decomposition. Say so and suggest re-running `$kirpr-tasks-decompose` in Codex or `/kirpr:tasks-decompose` in Claude Code using the existing files as input; do not run the review.

## Loading context

Follow the loading pattern from `~/.local/share/kirpr/config/templates.md` (section «Loading decomposition context»).

After loading the base context:
- If scope = whole decomposition → read `research.md` and **all** task files.
- If scope = one file → read that file, `SOLUTION.md`, `research.md` and its dependency row from the table in `00-overview.md`.
- Read `.kirpr/memory.md` of every service in scope (paths from `.kirpr/workspace.md`); their `## Уроки` feed Category 5.

## Execution

### Phase 1: Codebase investigation

Use `.context.md` section 2 as the starting point. Additionally:
1. For every task in scope — extract the mentioned **file paths, packages, functions, RPCs, tables**.
2. Check in the codebase:
   - Do the paths, packages, RPCs exist?
   - Do data structures and signatures match the description?
   - Do conventions match (naming, test patterns)?
   - Are there conflicts with existing code?
3. Remember every discrepancy — you will need them in Phase 2.

### Phase 1.5: Solution check

Go through the items of the checklist from `~/.local/share/kirpr/config/templates.md` (section «Verification checklist») that concern the solution — problem statement without consequences, every claim verified or marked, no retelling of existing behavior, rejected options recorded in `research.md`. Items about tasks and `00-overview.md` are checked in Phase 2. The result is one line for the summary report:

- `Решение: пройдено`
- `Решение: не пройдено — пункты {номера}` (with a quote from `SOLUTION.md` for every failed item)

### Phase 2: Analysis in 5 categories

Check every task in scope against all 5 categories. Determine severity for every finding.

#### Category 1: Ambiguities
- [ ] Every step is unambiguous — two developers would implement it the same way ("добавить логику", "обработать ошибку" without a condition — bad)
- [ ] Conditions in «Проверить» are verifiable: input → expected result ("всё работает" — bad)
- [ ] Decisions that cannot be unambiguously reconstructed from `SOLUTION.md` are named in the steps (RPC names, signatures, branching conditions)
- [ ] No "и т.д.", "аналогично", "как сейчас" in place of specifics

#### Category 2: Contradictions
- [ ] No conflicts between tasks (one does not cancel another)
- [ ] Task steps do not contradict `SOLUTION.md`
- [ ] Dependencies in `00-overview.md` match the task texts and are technical only (client after server)
- [ ] No duplicated work between tasks
- [ ] Described paths, structures, APIs are compatible with the real codebase

#### Category 3: Gaps
- [ ] Every change from `SOLUTION.md` is covered by a task
- [ ] «Проверить» has negative scenarios and edge cases
- [ ] Unverified items are marked «подтвердить на dev», not presented as facts
- [ ] Integrations between services are covered (who calls, who generates the client)
- [ ] Edge cases from the tracker description are covered

#### Category 4: Boundaries and risks
- [ ] One task — one service — one MR (otherwise split or merge)
- [ ] Suspiciously small tasks in the same service — perhaps they should be merged
- [ ] Technical risks identified (new dependencies, unfamiliar API, no prototype)
- [ ] Dependencies on external components / other teams are stated explicitly
- [ ] No bottleneck in deployment order (one task does not block everything else)

#### Category 5: Lessons
- [ ] The task does not repeat a situation recorded as a lesson `L-NNN` in its service's `memory.md` (a finding is `Важно` and cites the lesson id)
- [ ] «Проверить» uses the commands from `## Как проверять` of the service, not invented ones

### Phase 2.5: Quality scoring

Score every task in scope with the rubric from `~/.local/share/kirpr/config/templates.md` (section «Quality scoring rubric»). For every file assign K1–K5 points (0–2 each).

Show the user the scores table:

```
Оценка качества декомпозиции {номер}
Общий score: {X.X}/10

| Файл | К1 | К2 | К3 | К4 | К5 | Score | Главная проблема |
|------|----|----|----|----|----|-------|-----------------|
| 01-scansrv.md | 1 | 1 | 2 | 2 | 1 | 7 | К2: не названо, что делать со сканом в статусе `canceled` |
| 02-upload-callback.md | 1 | 2 | 1 | 2 | 2 | 8 | К3: в «Проверить» нет отрицательного сценария |
| 03-devops.md | 2 | 2 | 2 | 2 | 2 | 10 | ✅ ok |
| ... | | | | | | | |

Файлы со score >= 8: {N} из {M}
Файлы, требующие доработки (score < 8): {K}
```

### Phase 3: Summary report

Show the user a structured report, **including scores**:

```
Review декомпозиции {номер}
Scope: {вся декомпозиция / конкретный файл}
Проверено: {N} задач
Общий score: {X.X}/10
Решение: {пройдено / не пройдено — пункты ...}

Критично ({K}):
  ❌ [01-scansrv.md] (score: 7) К5: шаг 2 читает `Jobs().Summary`, в коде `scanCheckTerminal` работает через `Jobs().Info`
  ❌ [SOLUTION.md] Пункт 3 чеклиста: «статус не меняем, как сейчас» — пересказ существующего поведения

Важно ({M}):
  ⚠️ [01-scansrv.md] (score: 7) К2: не названо, что делать со сканом в статусе `canceled`
  ⚠️ [01-scansrv.md] (score: 7) К1: шаг «обработать ошибку» без условия
  ⚠️ [00-overview.md] 02-upload-callback зависит от 01-scansrv (клиент из схемы), но в таблице зависимость не указана

Замечания ({L}):
  💡 [02-upload-callback.md] (score: 8) К3: в «Проверить» нет сценария «scansrv недоступен»
  💡 [00-overview.md] Внешние зависимости не перечислены и не помечены «нет»
```

Ask: "Начинаю итерацию по файлам с score < 8, от худшего к лучшему. Готовы?"

### Phase 3.5: Quality iteration loop

For every file with score < 8, starting from the worst:

1. **Show the breakdown** — 5 criteria with points and an explanation of what is wrong in each.
2. **Propose fixes** — concrete changes to raise the weak criteria.
3. **Wait for the user's decision** — accept / reject / clarify.
4. **Recalculate the score** — after the fixes are accepted, show the file's new score.
5. **If score < 8** — propose further improvements (second pass).
6. **If score >= 8** — move to the next file.

**Limit: max 2 iterations per file.** If after 2 passes the score is < 8 — record it as "⚠️ accepted at {N}/10" and move on.

After the loop, show the final table with updated scores and ask: "Все файлы обработаны. Применяю исправления?"

### Phase 4: Dialogue on the remaining findings

If after Phase 3.5 there are findings from Phases 1.5 and 2 that the scoring iteration did not cover (e.g. failed `SOLUTION.md` items or dependencies in `00-overview.md`):

For every such finding:
1. Show the problem in detail: what is wrong, where, why it matters.
2. Propose a solution (options, if there are several).
3. Wait for the user's answer:
   - **Accept** — the fix is queued.
   - **Reject** — the finding is ignored (mark it "отклонено пользователем").
   - **Clarify** — ask a follow-up question, rephrase the solution.
4. Move to the next finding.

### Phase 5: Applying the fixes

1. Show the **final diff** of all accepted fixes (from Phases 3.5 and 4):
   ```
   Принятые исправления ({N} из {M} находок):

   [ОБНОВИТЬ] 01-scansrv.md (score: 7 → 9)
     - Шаг 2: `Jobs().Summary` → `Jobs().Info`
     - Шаг 1: добавлено «для скана в другом статусе — успех без изменений»; шаг 3: условие вместо «обработать ошибку»

   [ОБНОВИТЬ] 02-upload-callback.md (score: 8 → 9)
     - «Проверить»: добавлен сценарий «scansrv недоступен → exit 1»

   [ОБНОВИТЬ] SOLUTION.md
     - scansrv: удалено предложение «статус не меняем, как сейчас»

   [ОБНОВИТЬ] 00-overview.md
     - Зависимости: добавлено `1 → 2` — клиент генерируется из схемы сервера

   Отклонено: {K} находок
   Общий score: {X.X}/10 → {Y.Y}/10
   ```
2. Wait for the user's confirmation.
3. Write the changes to the files.
4. Update `00-overview.md` if the task table or dependencies are affected.
5. Update `.context.md`:
   - Section 3: add the review decisions (accepted and rejected, with justification).
   - **Section 5.5**: write the final quality scores and the «Решение: …» line per the template in `~/.local/share/kirpr/config/templates.md`.
   - Section 7: update the last-adaptation date and «Версия памяти».

### Phase 6: Lessons (HITL)

Trigger: a finding of Category 2 or 3 contradicted the code, or a file stayed below score 8 after Phase 3.5. Otherwise skip the phase.

Lessons are recorded only through the script and only with the user's consent (section «Writing lessons (HITL)» in `templates.md`):

1. Formulate 0–3 candidates in the lesson format: a mistake of the decomposition process and how to avoid it next time, not a fact about the code.
2. For each candidate run `python3 ~/.local/share/kirpr/scripts/kirpr_memory.py lesson add --file <service>/.kirpr/memory.md --text "..." --task {НОМЕР} [--refs a,b] --dry-run` (omit `--refs` when there is none). The script prints the resulting line, or refuses: «memory.md не найден» — tell the user to run `$kirpr-onboard` in Codex or `/kirpr:onboard` in Claude Code (or `kirpr_memory.py init`) first and skip this service; «похоже на L-NNN» (exit code 2) — a similar lesson exists: merge the two texts into one and run `lesson amend L-NNN --file ... --text "<merged text>" --dry-run`, which prints «было / станет».
3. Show the diff per file («добавить L-004 в `scansrv/.kirpr/memory.md`», «уточнить L-002: было … → станет …»).
4. Ask per file: «Записать уроки в {файл}?» — `да` / `нет`. On `да` rerun exactly the commands from step 2 (`add` or `amend`) without `--dry-run`; on `нет` write nothing and do not ask again.
5. **Do not write a lesson without the user's explicit «да».** Never edit `memory.md` by hand; the script is the only writer.

## Additional review rules

- **Show evidence.** Every finding is backed by a concrete quote from the file or a codebase check result.
- **Severity is justified.** `Критично` = blocks implementation or contradicts facts. `Важно` = will lead to rework. `Замечание` = can be improved.
- **Do not invent problems.** If a task matches `SOLUTION.md` and the code — do not look for findings for the sake of a report.
