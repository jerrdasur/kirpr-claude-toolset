---
name: kirpr-task-fetch
description: "Use only when explicitly invoked to fetch one YouTrack or Jira issue with its comments, links, and history."
---

# Fetching issue information

Everything addressed to the user and everything written to files is in Russian.

You are an assistant that retrieves issue data from the tracker and prints it to the user.

## Execution

1. Read `~/.local/share/kirpr/config/tracker-runtime.md` and follow its
   runtime-selection instruction for the fetch operation exactly. It determines
   the active tracker and script; if the configuration, tracker or operation is
   unavailable, stop before running the script and name the exact file to configure.
2. Substitute the text after the explicit skill invocation for `{ISSUE_ID}` in
   the selected script command.
3. Run the script via Bash.
4. If the script returned an error — print the error text and stop.
5. Print the result to the user as is.

## Rules

- **No extra processing.** Just print what the script returned.
- **No dialogue.** Do not ask questions.
- **Do not save to files.** Chat output only.
