# kirpr — skills and commands for Claude Code and Codex

kirpr helps turn tracker tasks into decompositions, edited text, expert
reviews, and product-hypothesis interviews. The same skills work in both
Claude Code and Codex; Claude also has compatible `/kirpr:*` command adapters.

## Invocations

Use the Claude Code or Codex form in the relevant client.

### Tracker tasks

| What | Claude Code | Codex |
|------|-------------|-------|
| Fetch a task | `/kirpr:task-fetch SAS-200` | `$kirpr-task-fetch SAS-200` |
| Create a task | `/kirpr:task-create SAS Fix export` | `$kirpr-task-create SAS Fix export` |
| Update a task | `/kirpr:task-update SAS-200 status In Progress` | `$kirpr-task-update SAS-200 status In Progress` |
| Delete a task | `/kirpr:task-delete SAS-200` | `$kirpr-task-delete SAS-200` |

`task-delete` is irreversible: it previews the result and requires manually
entering the issue number.

### Task decomposition

| What | Claude Code | Codex |
|------|-------------|-------|
| Decompose | `/kirpr:tasks-decompose SAS-200` | `$kirpr-tasks-decompose SAS-200` |
| Review decomposition | `/kirpr:tasks-review SAS-200` | `$kirpr-tasks-review SAS-200` |
| Adapt decomposition | `/kirpr:tasks-adapt SAS-200` | `$kirpr-tasks-adapt SAS-200` |
| Push subtasks | `/kirpr:tasks-push SAS-200` | `$kirpr-tasks-push SAS-200` |
| Create project memory | `/kirpr:onboard` | `$kirpr-onboard` |

### Text editing

| What | Claude Code | Codex |
|------|-------------|-------|
| Edit a text | `/kirpr:text` | `$kirpr-text` |

### Expert panel

| What | Claude Code | Codex |
|------|-------------|-------|
| Review a specification | `/expert-panel spec docs/spec.md` | `$expert-panel spec docs/spec.md` |
| Review working tree | `/expert-panel diff` | `$expert-panel diff` |
| Review against a base | `/expert-panel diff main` | `$expert-panel diff main` |
| Review against a specification | `/expert-panel diff --spec docs/spec.md` | `$expert-panel diff --spec docs/spec.md` |

The panel combines reviews from Rob Pike, Dave Cheney, Neal Ford, Michael
Stonebraker, and Filippo Valsorda; each runs as a separate agent. Customize it
in `~/.config/kirpr/custom-experts.md` (`disable: <id>` or your own sections).

Every finding is reported in full with a confidence level; in diff mode each
`blocker` and `major` names the violated invariant, the breaking input, and the
test that closes it. `--spec` accepts a design spec or a decomposition task
file `NN-service.md`: before the panel runs, its acceptance criteria are
checked as met / unmet. The panel also flags generated code that was not
regenerated and reads `.kirpr/memory.md` when the repository has one.

### Product-hypothesis interview

| What | Claude Code | Codex |
|------|-------------|-------|
| Choose an interview subject | `/grill-me` | `$grill-me` |
| Start an interview | `/grill-me billing for small teams` | `$grill-me billing for small teams` |
| Continue from a document | `/grill-me docs/hypotheses/billing.md` | `$grill-me docs/hypotheses/billing.md` |
| Resume a saved session | `/grill-me docs/grill-me/2026-08-12-billing/` | `$grill-me docs/grill-me/2026-08-12-billing/` |

## Installation

Clone the repository for a local installation:

```bash
git clone git@github.com:jerrdasur/kirpr-claude-toolset.git ~/kirpr-toolset
cd ~/kirpr-toolset

# Interactive: choose Claude Code, Codex, or both.
./install.sh

# Explicit local targets.
./install.sh --target claude
./install.sh --target codex
./install.sh --target all
```

For a remote, non-interactive install, pass the target through the bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/jerrdasur/kirpr-claude-toolset/main/install-remote.sh | sh -s -- --target codex
```

The remote bootstrap downloads the repository archive and runs its local
`install.sh`; it does not maintain a second list of installed files. To update,
run the same remote command or pull a local clone and re-run `./install.sh`
with the desired target.

## Installed paths and migration

Both platforms share one installer-managed runtime at `~/.local/share/kirpr` and one
mutable configuration directory at `~/.config/kirpr`. The platform-specific
entry points are:

| Platform | Installed path |
|----------|----------------|
| Codex skills | `~/.agents/skills` |
| Claude Code skills | `~/.claude/skills` |
| Claude Code adapters | `~/.claude/commands/kirpr` |

On the first install, tracker configuration and custom experts are migrated
from recognized legacy user locations into the shared configuration. If two
different user-owned versions conflict, installation stops before replacing
skills. Existing same-name skills are saved under `~/.config/kirpr/backups/`
before replacement, and a failed install rolls back its own changes. Skills
dropped from the bundle — `kirpr-flow` and the `kirpr-adr-*` family — are
removed from both platforms on the next install, with the same backup and
rollback treatment. Tracker
and API tokens are never stored or printed by the installer: keep them in
environment variables such as `YOUTRACK_TOKEN`, `JIRA_TOKEN`, and `JIRA_EMAIL`.

Project state is platform-neutral: use `.kirpr/grill-me/lenses.md` and
`.kirpr/expert-panel-ignore`. When the expert panel finds the older
`.claude/expert-panel-ignore`, it shows both paths and asks before copying it
to `.kirpr/expert-panel-ignore`; the installer never scans or rewrites project
repositories.

## Tracker configuration

The installer asks for YouTrack, Jira, or no tracker on the first run. Edit
`~/.config/kirpr/tracker.md` later if needed. Configure credentials in your
shell environment:

```bash
export YOUTRACK_URL=https://youtrack.example.com
export YOUTRACK_TOKEN=<bearer-token>

export JIRA_URL=https://yourcompany.atlassian.net
export JIRA_TOKEN=<api-token>
export JIRA_EMAIL=you@example.com
```

Python 3 is required for the tracker scripts; they use only the standard
library.

## Project memory

Decomposition, review and adaptation read two memory files that live in git:

- `.kirpr/workspace.md` in the workspace (the directory you run decomposition
  from): a table of services with path, base branch, tracker project and role.
- `.kirpr/memory.md` in each service repository: how to test and lint, traps
  (generators, what not to review), and lessons from past decompositions.

Store only what cannot be derived from the code; no architecture overviews.
Each file is limited to 150 lines. `/kirpr:onboard` (`$kirpr-onboard`) creates
the files; the skills only read them. Lessons are written by the review and
adapt skills after an explicit confirmation, never automatically.

All writes go through `~/.local/share/kirpr/scripts/kirpr_memory.py`:

```bash
kirpr_memory.py refresh [--workspace DIR] [--dry-run]   # rebuild the service table, keep roles
kirpr_memory.py role --service S --role R [--dry-run]  # set a service role in the table
kirpr_memory.py init --file F --name N [--check L]... [--traps L]... [--dry-run]  # create memory.md
kirpr_memory.py lesson add --file F --text T --task ID [--refs a,b] [--dry-run]
kirpr_memory.py lesson amend L-003 --file F --text T    # refine an existing lesson
kirpr_memory.py lint --file F                           # sections, format, budget
kirpr_memory.py stale --file F                          # lesson refs that no longer exist
```

`lesson add` exits with code 2 when a similar lesson exists and names the
`amend` command to use instead.

## Uninstall

Remove only one platform or both with the same target selector:

```bash
./uninstall.sh --target claude
./uninstall.sh --target codex
./uninstall.sh --target all
```

Uninstall reads the installation manifest and removes only its recorded paths.
The shared runtime remains until the final selected platform is removed;
`~/.config/kirpr` is retained. If an installation displaced a skill, uninstall
offers to restore its backup. Project `.kirpr` and `.claude` directories are
never removed.

## Repository layout

```text
commands/kirpr/  Claude Code command adapters
installer/       shared installer logic
kirpr/           shared runtime configuration, prompts, and scripts (incl. kirpr_memory.py)
skills/          canonical Agent Skills for Codex and Claude Code
install.sh       local installation
install-remote.sh archive-based remote bootstrap
uninstall.sh     manifest-scoped removal
```

## License

Open source. Free to use.
