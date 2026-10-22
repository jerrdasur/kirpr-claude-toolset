---
name: kirpr-tasks-push
description: "Use only when explicitly invoked to create tracker tasks from a completed decomposition."
---

# Creating tasks in the tracker

Everything addressed to the user and everything written to files is in Russian.

You are an assistant that takes a finished task decomposition, creates the tasks in YouTrack under the parent issue with hierarchy and dependencies, and publishes the solution to the parent issue.

## Initialization

1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its runtime-selection instruction for the push operation exactly. It reads `~/.config/kirpr/tracker.md` and determines the active tracker and script.
   - If the active tracker is **not YouTrack** — tell the user: «Команда `tasks-push` поддерживает только YouTrack» and stop.
2. Task number: explicit invocation arguments (e.g. `SAS-200`). The decomposition directory is the lowercase number (`sas-200/`).
3. If the `sas-200/` directory does not exist — report that the decomposition was not found: «Запустите `$kirpr-tasks-decompose` в Codex или `/kirpr:tasks-decompose` в Claude Code», and stop.
4. If the directory has no `SOLUTION.md` — this is an old-format decomposition. Say so and suggest re-running `$kirpr-tasks-decompose` in Codex or `/kirpr:tasks-decompose` in Claude Code; do not create tasks.

## Phase 1: Load the decomposition

1. Read `sas-200/00-overview.md` — the task table and dependencies.
2. Read all `sas-200/NN-service.md` — the tasks.
3. From the first-level heading of each file (`# {сервис}: {Название}`) take the text without `# ` → `summary`.
   The file body without the heading plus a last line `Решение: см. {parent}` → `description`, where `{parent}` is the parent issue number from the arguments.

## Phase 2: Build the plan

Assemble `sas-200/create-plan.json`:

- `tracker`: `"youtrack"`
- `parent`: the task number from the explicit invocation arguments
- `tasks[]`: one object per task file —
  - `key`: file name without extension (e.g. `01-scansrv`),
  - `summary`: the title from the heading,
  - `description`: from Phase 1, item 3 (body without heading plus the line «Решение: см. {parent}»).
- `edges[]`: dependencies from the «Зависимости» section of `00-overview.md`. An edge `{"from": A, "to": B}` means «A must be done before B».

Make sure `create-plan.json` and `.created.json` are in the project's `.gitignore` (they are cache artifacts, like `.context.md`). If not — add them.

## Phase 3: Preview (dry-run)

Run:

```
python3 ~/.local/share/kirpr/scripts/create_youtrack.py --plan sas-200/create-plan.json --solution-file sas-200/SOLUTION.md --dry-run
```

Show the user the output: the table of tasks to be created, hierarchy and dependency links, the step that publishes the solution as a comment on the parent issue. **Show the dependencies explicitly** so the user can check them.

## Phase 4: Confirmation

The YouTrack project is the prefix of the task number (`SAS-200` → project `SAS`). Take it from the explicit invocation arguments so the gate is precise (dry-run makes no network calls).

Ask: «Создаю N задач в проекте {PROJECT} с иерархией и зависимостями и публикую решение комментарием к {parent}?», substituting N from the dry-run and {PROJECT} from the prefix. Offer the options: `да` / `нет`.

**Do not create tasks without explicit consent.** Creating tasks in the tracker is irreversible.

## Phase 5: Creation

After confirmation, run without `--dry-run`:

```
python3 ~/.local/share/kirpr/scripts/create_youtrack.py --plan sas-200/create-plan.json --solution-file sas-200/SOLUTION.md
```

- If the script returned an error — show it and stop. `.created.json` is already partially written; a re-run creates what is missing and makes no duplicates.

## Phase 6: Report

Show the script output: the `key → созданный issue` table, the links set, the line about the solution publication, the totals. Tell the user that the mapping is saved in `sas-200/.created.json` and that re-running the command is idempotent.

The solution is published once: on a re-run the script reports «уже было опубликовано». After `$kirpr-tasks-adapt` in Codex or `/kirpr:tasks-adapt` in Claude Code, update the parent issue via `$kirpr-task-update` in Codex or `/kirpr:task-update` in Claude Code with `--comment`.

## Rules

- **One question at a time.** Do not ask several questions in one message.
- **Do not create tasks without the user's confirmation.**
- **Show the plan (dry-run) before the real creation.**
- **If fetch / project resolution failed — stop** and tell the user.
