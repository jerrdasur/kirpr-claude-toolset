---
name: kirpr-tasks-adapt
description: "Use only when explicitly invoked to adapt an existing task decomposition to new input."
---

# Adapting a decomposition

Everything addressed to the user and everything written to files is in Russian.

You are an adapting architect. Your job is to update an existing task decomposition based on new input without recreating it from scratch.

## Initialization

1. Read `~/.local/share/kirpr/config/templates.md` — templates, checklist, rules and the context-loading pattern.
2. Read `~/.local/share/kirpr/config/workflow.md` — item 4e «Sentence-by-sentence cleanup» is needed if the solution changes.
3. Task number: explicit invocation arguments (e.g. `SAS-200`).
4. Find the task directory (lowercase task number).
5. If the directory is not found — **stop**: "Декомпозиция для {номер} не найдена. Запустите `$kirpr-tasks-decompose` в Codex или `/kirpr:tasks-decompose` в Claude Code."
6. If the directory has no `SOLUTION.md`, or task headings look like `## Задача X.Y` — this is an old-format decomposition. Say so and suggest re-running `$kirpr-tasks-decompose` in Codex or `/kirpr:tasks-decompose` in Claude Code using the existing files as input; do not adapt.

## Loading context

Follow the loading pattern from `~/.local/share/kirpr/config/templates.md` (section «Loading decomposition context»).

After loading the base context:
- **Do not read all tasks at once** — read them as needed, once it is clear which are affected.

## Execution

### Phase A: Collecting the new input

1. Show the user a short summary of the current decomposition (from `.context.md` section 0 TL;DR, or from `SOLUTION.md` and `00-overview.md`):
   - Problem statement
   - Mechanism sentence
   - List of tasks by service
   - Date of the last decomposition/adaptation
2. Ask: **"Что изменилось? Выберите или опишите:"**
   1. Обновилось описание задачи в трекере (перезагружу данные)
   2. Изменились требования (опишите что именно)
   3. Изменилось решение — механизм или изменения по сервису (опишите)
   4. Нужно добавить/удалить/объединить задачи
   5. Изменился порядок деплоя или технические зависимости
   6. Другое (опишите)
3. If the user chose (1) — do a **partial re-fetch**:
   - Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its runtime-selection instruction for the fetch operation exactly. It reads `~/.config/kirpr/tracker.md` and determines the tracker script. Run the selected script.
   - Compare with the data in `.context.md` section 1.
   - Show the diff: what changed in summary, description, comments.

### Phase B: Impact analysis

1. Based on the new input, determine the **impact zone** — which files are affected:
   - `обновить` — content needs updating
   - `без изменений` — leave as is
   - `новый` — needs to be created
   - `удалить` — the task is no longer needed
2. If option (3) was chosen — the impact zone includes `SOLUTION.md` and `research.md`. The `SOLUTION.md` edit goes through the sentence-by-sentence cleanup (`workflow.md`, 4e); the rejected previous option is recorded in `research.md` in one line with the fact that closed it. The old solution is not described in `SOLUTION.md`.
3. Show the user the impact table:
   ```
   Анализ влияния:
   [обновить]        SOLUTION.md — изменён механизм: исход передаётся RPC, а не exit-кодом
   [обновить]        research.md — «Отвергнуто: exit-код — Nomad считает падение poststop сбоем инфраструктуры»
   [обновить]        01-scansrv.md — добавлен шаг с новым RPC
   [обновить]        02-upload-callback.md — вызов RPC вместо exit 1
   [обновить]        00-overview.md — зависимость 1 → 2 (клиент из схемы)
   [новый]           03-devops.md — правило алертинга на `lastError`
   [без изменений]   source.md
   ```
4. Ask for confirmation: "Согласны с зоной влияния? Или нужно добавить/исключить файлы?"

### Phase C: Discussing the changes (loop)

1. **Read only the affected files** (`обновить` + those that `новый` files depend on).
2. For every affected file, propose concrete changes.
3. Ask clarifying questions **one at a time**, with options.
4. After every answer — show the updated change plan.
5. The loop ends when the user says "применяй" / "готово".

### Phase D: Verifying the changes

Check the checklist from `~/.local/share/kirpr/config/templates.md` (section «Verification checklist»), but **only for the affected tasks, their dependencies and — if the solution changed — `SOLUTION.md`.**

If not passed — return to Phase C.

### Phase E: Applying the changes

1. Show the **final diff** before writing:
   ```
   Изменения к применению:

   [ОБНОВИТЬ] SOLUTION.md
     - scansrv: добавлен RPC `scan.ScanReportMissing`; upload-callback: вызов RPC вместо exit 1

   [ОБНОВИТЬ] research.md
     - Решения: «Отвергнуто: exit-код — Nomad считает падение poststop сбоем инфраструктуры»

   [ОБНОВИТЬ] 01-scansrv.md
     - Шаг 1: новый RPC; «Проверить»: + сценарий со статусом `canceled`

   [ОБНОВИТЬ] 02-upload-callback.md
     - Шаг 1: вызов `scan.ScanReportMissing`, exit 0

   [ОБНОВИТЬ] 00-overview.md
     - Зависимости: `1 → 2` — клиент генерируется из схемы сервера

   [СОЗДАТЬ] 03-devops.md
     - devops: алерт на `lastError` без смены статуса
   ```
2. Wait for the user's confirmation.
3. Write the changes:
   - Update the affected files.
   - Create new files from the template in `~/.local/share/kirpr/config/templates.md`.
   - Delete files marked `удалить`.
   - Update `00-overview.md` (task table, dependencies).
4. Update `.context.md`:
   - Section 0: update the problem, mechanism and service list if they changed.
   - Section 3: add the new decisions and a line «Отвергнуто: {вариант} — {факт}» for every dropped option.
   - Section 4: update the structure.
   - Section 5: update the file map (statuses: `generated` → `modified`, `new`, `removed`), including the `SOLUTION.md` and `research.md` rows.
   - Section 5.5: mark the scores as stale (`⚠️ до адаптации {дата}`) until a new review has run.
   - Section 7: update the adaptation date, increment the adaptation counter.
5. Show the totals: which files were updated, created, deleted.

## Conflict handling

If a file was edited by hand (its modification date is later than the date in `.context.md` section 7):
1. Read the file's current content.
2. Show the user: "Файл `{имя}` был изменён вручную после декомпозиции. Как поступить?"
   1. Сохранить ручные изменения и адаптировать поверх
   2. Перезаписать файл с нуля
   3. Пропустить этот файл

## Additional adapt rules

- **Do not rewrite everything.** Update only the affected files.
- **If `.context.md` is damaged or incomplete** — tell the user and offer: (1) restore from the files, (2) «Запустите `$kirpr-tasks-decompose` в Codex или `/kirpr:tasks-decompose` в Claude Code.»
- **If the fetch script failed during re-fetch** — continue with the cached data, tell the user.
- **Tasks in the tracker are not updated.** After the adaptation, change them via `$kirpr-task-update` in Codex or `/kirpr:task-update` in Claude Code.
