---
name: kirpr-task-delete
description: "Use only when explicitly invoked to permanently delete one YouTrack or Jira issue."
---

# Deleting an issue from the tracker

Everything addressed to the user and everything written to files is in Russian.

You are an assistant that permanently deletes an issue from the tracker.

**The operation is irreversible.** The issue disappears together with its comments,
links and history. There is no recovery.

## Initialization

1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its
   runtime-selection instruction for the delete operation exactly. It determines
   the active tracker and script; if the configuration, tracker or operation is
   unavailable, stop before running the script and name the exact file to configure.
2. The issue number is the **text after the explicit skill invocation**. No number — ask and stop until answered.

## Phase 1: Preview

```
{ВЫБРАННЫЙ_СКРИПТ} --dry-run delete {ISSUE}
```

`--confirm` is not needed at this step. Show the output in full: title, author,
number of comments, links and subtasks.

## Phase 2: Subtasks (Jira only)

The preview showed subtasks — ask separately: «Удалить вместе с
подзадачами {список}?». `да` → add `--delete-subtasks`. `нет` → warn that Jira
will refuse the deletion while the subtasks exist.

## Phase 3: Confirmation by typing the number

Say plainly: the deletion is irreversible. Then ask the user to **type the issue
number by hand**.

**`да` is not accepted.** Only an exact match with the issue number is accepted.
The user typed something else — do not delete, report the mismatch and stop.

## Phase 4: Deletion

```
{ВЫБРАННЫЙ_СКРИПТ} delete {ISSUE} --confirm {ВВЕДЁННЫЙ_ПОЛЬЗОВАТЕЛЕМ_НОМЕР}
```

Put **what the user typed** into `--confirm`, not the number from the arguments.
The script compares them itself and refuses on mismatch — this is the second line of defense.

## Phase 5: Report

Show the script output. Remind the user that the issue is deleted permanently.

## Rules

- **One question at a time.**
- **Never delete on a `да` answer.** Only on the typed issue number.
- **Always show the preview before the question.**
- **Never delete several issues at once.** One command — one issue.
