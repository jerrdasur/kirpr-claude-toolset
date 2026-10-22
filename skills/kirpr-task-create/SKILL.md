---
name: kirpr-task-create
description: "Use only when explicitly invoked to create one YouTrack or Jira issue."
---

# Creating an issue in the tracker

Everything addressed to the user and everything written to files is in Russian.

You are an assistant that creates one tracker issue from a free-form request.

## Initialization

1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its
   runtime-selection instruction for the create operation exactly. It determines
   the active tracker and script; if the configuration, tracker or operation is
   unavailable, stop before running the script and name the exact file to configure.
2. Parse the **text after the explicit skill invocation**. It is free text: `SAS Починить экспорт` or
   «заведи в SAS задачу про таймауты в экспорте».

## Phase 1: Collecting arguments

Extract from the request:

- **project** — short name (YouTrack) or key (Jira). Not in the request — ask.
- **summary** — a short statement of the issue. None — compose it from the request
  yourself and show it to the user for confirmation.
- **description** — the issue body, if the user gave one. Save a long description
  to a temporary file and pass it via `--description-file`.
- **parent** — if the user said «подзадача к SAS-200».
- **issue type** — Jira only, the `--type` flag is mandatory. Not obvious from the
  request — ask, offering `Task` as the default.
- **assignee, status, priority** — if the user named them.

One question at a time. Do not ask several questions in one message.

## Phase 2: Preview (dry-run)

YouTrack:

```
{ВЫБРАННЫЙ_СКРИПТ} --dry-run create \
  --project SAS --summary "..." --description-file /tmp/desc.md \
  --command "assignee ivanov"
```

Jira:

```
{ВЫБРАННЫЙ_СКРИПТ} --dry-run create \
  --project PROJ --summary "..." --type Task --assignee ivanov
```

Show the user the script output in full.

## Phase 3: Confirmation

Ask: «Создать задачу в проекте {PROJECT}?». Options: `да` / `нет`.

**Do not create the issue without explicit consent.**

## Phase 4: Creation

Repeat the same command without `--dry-run`.

- The script returned a non-zero code — show the output in full and stop. The
  report shows what managed to apply.

## Phase 5: Report

Show the script output. Separately name the created issue number and the link to it
(the base URL was determined while running the runtime instruction).

## Rules

- **One question at a time.**
- **Do not create the issue without the user's confirmation.**
- **Show the dry-run before the real creation.**
- **Do not touch the decomposition.** This command neither reads nor writes
  `create-plan.json` and `.created.json`. For tasks from a decomposition there is
  Codex `$kirpr-tasks-push` and Claude Code `/kirpr:tasks-push`.
