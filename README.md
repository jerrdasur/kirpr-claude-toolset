# kirpr — skills and commands for Claude Code and Codex

kirpr helps turn tracker tasks into plans, ADRs, edited text, expert reviews,
product-hypothesis interviews, and a git-free development workflow. The same
skills work in both Claude Code and Codex; Claude also has compatible
`/kirpr:*` command adapters.

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

### Architecture Decision Records

| What | Claude Code | Codex |
|------|-------------|-------|
| Initialize ADR support | `/kirpr:adr-init` | `$kirpr-adr-init` |
| Write an ADR | `/kirpr:adr-write SAS-200` | `$kirpr-adr-write SAS-200` |
| Review an ADR | `/kirpr:adr-review SAS-200` | `$kirpr-adr-review SAS-200` |

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

The panel combines reviews from Rob Pike, Dave Cheney, Neal Ford, and Michael
Stonebraker. Customize it in `~/.config/kirpr/custom-experts.md`.

### Product-hypothesis interview

| What | Claude Code | Codex |
|------|-------------|-------|
| Choose an interview subject | `/grill-me` | `$grill-me` |
| Start an interview | `/grill-me billing for small teams` | `$grill-me billing for small teams` |
| Continue from a document | `/grill-me docs/hypotheses/billing.md` | `$grill-me docs/hypotheses/billing.md` |
| Resume a saved session | `/grill-me docs/grill-me/2026-08-12-billing/` | `$grill-me docs/grill-me/2026-08-12-billing/` |

### Development workflow

| What | Claude Code | Codex |
|------|-------------|-------|
| Brainstorm a spec | `/kirpr-flow brainstorm topic` | `$kirpr-flow brainstorm topic` |
| Plan a spec | `/kirpr-flow plan docs/spec.md` | `$kirpr-flow plan docs/spec.md` |
| Execute a plan | `/kirpr-flow execute docs/plan/` | `$kirpr-flow execute docs/plan/` |
| Execute inline | `/kirpr-flow execute --inline docs/plan/` | `$kirpr-flow execute --inline docs/plan/` |
| Request a review | `/kirpr-flow review docs/plan/` | `$kirpr-flow review docs/plan/` |
| Debug a symptom | `/kirpr-flow debug symptom` | `$kirpr-flow debug symptom` |
| Finish with a summary | `/kirpr-flow finish` | `$kirpr-flow finish` |
| Create or edit a skill | `/kirpr-flow skill name` | `$kirpr-flow skill name` |

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
before replacement, and a failed install rolls back its own changes. Tracker
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
kirpr/           shared runtime configuration, prompts, and scripts
skills/          canonical Agent Skills for Codex and Claude Code
install.sh       local installation
install-remote.sh archive-based remote bootstrap
uninstall.sh     manifest-scoped removal
```

## License

Open source. Free to use.
