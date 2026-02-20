# kirpr — Claude Code commands for task decomposition & ADR

Slash-commands for Claude Code that help decompose tasks from YouTrack/Jira into detailed specs and write Architecture Decision Records with self-review.

## Installation

```bash
git clone <repo-url> ~/claude-toolset
cd ~/claude-toolset
./install.sh
```

The installer creates symlinks in `~/.claude/` and optionally configures your issue tracker.

### Environment variables

**YouTrack:**
```bash
export YOUTRACK_URL=https://youtrack.example.com
export YOUTRACK_TOKEN=<your-bearer-token>
```

**Jira:**
```bash
export JIRA_URL=https://yourcompany.atlassian.net
export JIRA_TOKEN=<your-api-token>
export JIRA_EMAIL=you@example.com  # optional, for Jira Cloud basic auth
```

## Commands

| Command | Description |
|---------|-------------|
| `/kirpr:tasks-decompose SAS-200` | Decompose a tracker task into detailed subtask specs |
| `/kirpr:tasks-review SAS-200` | Critical review of an existing decomposition with quality scoring |
| `/kirpr:tasks-adapt SAS-200` | Adapt an existing decomposition to changed requirements |
| `/kirpr:adr-init` | Initialize ADR infrastructure and services map in a repository |
| `/kirpr:adr-write SAS-200` | Write an ADR with alternatives analysis and self-review |
| `/kirpr:adr-review SAS-200` | Cross-repo ADR review with traffic-light scoring (R1-R7) |

## Uninstall

```bash
./uninstall.sh
```

Removes symlinks. Tracker config (`~/.claude/kirpr/config/tracker.md`) is preserved.

## Update

```bash
cd ~/claude-toolset
git pull
```

Since commands are symlinked, updates take effect immediately.
