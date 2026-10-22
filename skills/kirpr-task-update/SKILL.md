---
name: kirpr-task-update
description: "Use only when explicitly invoked to update one YouTrack or Jira issue."
---

# Updating an issue in the tracker

Everything addressed to the user and everything written to files is in Russian.

You are an assistant that changes fields of an existing issue from a free-form request.

## Initialization

1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its
   runtime-selection instruction for the update operation exactly. It determines
   the active tracker and script; if the configuration, tracker or operation is
   unavailable, stop before running the script and name the exact file to configure.
2. Parse the **text after the explicit skill invocation**: the first token is the issue number (`SAS-201`), the rest is
   what to change. No number — ask.

## Phase 1: Mapping the request to flags

**YouTrack.** Text is edited with flags, everything else with commands:

| Request | Flag |
|---|---|
| переименуй, поменяй заголовок | `--summary "..."` |
| перепиши описание | `--description-file /tmp/desc.md` |
| статус, стадия | `--command "State In Progress"` |
| исполнитель | `--command "assignee ivanov"` |
| приоритет | `--command "Priority Critical"` |
| тег | `--command "tag регресс"` |
| добавь комментарий | `--comment "..."` |

**Jira.** Fields are typed:

| Request | Flag |
|---|---|
| переименуй | `--summary "..."` |
| перепиши описание | `--description-file /tmp/desc.md` |
| статус | `--status "In Progress"` |
| исполнитель | `--assignee ivanov` (unassign — `--assignee -1`) |
| приоритет | `--priority Critical` |
| метки | `--labels "a,b"` (replaces the whole set) |
| срок | `--duedate 2026-08-01` |
| комментарий | `--comment "..."` |

If the request does not map unambiguously — ask, one question at a time.

## Phase 2: Preview (dry-run)

```
{ВЫБРАННЫЙ_СКРИПТ} --dry-run update SAS-201 \
  --summary "..." --command "State In Progress"
```

Show the output in full: the `было → станет` table, the description diff, the command list.

For YouTrack, warn separately: the result of the lines in the «Команды» section
cannot be predicted; they are shown as is.

## Phase 3: Confirmation

Ask: «Применить изменения к {ISSUE}?». Options: `да` / `нет`.

**Do not change anything without explicit consent.**

## Phase 4: Execution

Repeat the same command without `--dry-run`.

- Non-zero exit code — show the output in full. The «Прервано» section says where
  it stopped; what was applied is not rolled back. A re-run is safe.

## Phase 5: Report

Show the script output and the link to the issue.

## Rules

- **One question at a time.**
- **Do not change the issue without the user's confirmation.**
- **Show the dry-run before the real edit.**
- **Long descriptions go through a file.** `--description-file`, not `--description`:
  multi-line text in a command-line argument breaks.
