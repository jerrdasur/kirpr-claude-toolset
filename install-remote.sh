#!/usr/bin/env bash
set -euo pipefail

REPO="jerrdasur/kirpr-claude-toolset"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"

CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"
SKILLS_DIR="$CLAUDE_DIR/skills"
PANEL_DIR="$SKILLS_DIR/expert-panel"

echo "Installing kirpr from github.com/$REPO"

# --- Backup tracker.md if it exists ---
TRACKER_BACKUP=""
if [ -f "$KIRPR_DIR/config/tracker.md" ]; then
    TRACKER_BACKUP="$(mktemp)"
    cp "$KIRPR_DIR/config/tracker.md" "$TRACKER_BACKUP"
    echo "  Backed up tracker.md"
fi

# --- Backup custom-experts.md if it exists ---
CUSTOM_BACKUP=""
if [ -f "$PANEL_DIR/custom-experts.md" ]; then
    CUSTOM_BACKUP="$(mktemp)"
    cp "$PANEL_DIR/custom-experts.md" "$CUSTOM_BACKUP"
    echo "  Backed up custom-experts.md"
fi

# --- Clean old installation ---
if [ -d "$COMMANDS_DIR" ]; then
    rm -rf "$COMMANDS_DIR"
    echo "  Removed old $COMMANDS_DIR"
fi
if [ -d "$KIRPR_DIR" ]; then
    rm -rf "$KIRPR_DIR"
    echo "  Removed old $KIRPR_DIR"
fi
if [ -d "$PANEL_DIR" ]; then
    rm -rf "$PANEL_DIR"
    echo "  Removed old $PANEL_DIR"
fi

# --- Create directories ---
mkdir -p "$COMMANDS_DIR"
mkdir -p "$KIRPR_DIR/config"
mkdir -p "$KIRPR_DIR/scripts"
mkdir -p "$KIRPR_DIR/prompts"
mkdir -p "$PANEL_DIR/experts"
mkdir -p "$PANEL_DIR/modes"

# --- Download files ---
download() {
    local remote_path="$1" local_path="$2"
    if curl -fsSL "$BASE_URL/$remote_path" -o "$local_path"; then
        echo "  $remote_path -> downloaded"
    else
        echo "  ERROR: failed to download $remote_path" >&2
        return 1
    fi
}

# Commands
download "commands/kirpr/adr-init.md"         "$COMMANDS_DIR/adr-init.md"
download "commands/kirpr/adr-review.md"        "$COMMANDS_DIR/adr-review.md"
download "commands/kirpr/adr-write.md"         "$COMMANDS_DIR/adr-write.md"
download "commands/kirpr/task-fetch.md"        "$COMMANDS_DIR/task-fetch.md"
download "commands/kirpr/tasks-adapt.md"       "$COMMANDS_DIR/tasks-adapt.md"
download "commands/kirpr/tasks-decompose.md"   "$COMMANDS_DIR/tasks-decompose.md"
download "commands/kirpr/tasks-review.md"      "$COMMANDS_DIR/tasks-review.md"
download "commands/kirpr/tasks-push.md"        "$COMMANDS_DIR/tasks-push.md"
download "commands/kirpr/text.md"              "$COMMANDS_DIR/text.md"

# Config
download "kirpr/config/adr-review-rubric.md"   "$KIRPR_DIR/config/adr-review-rubric.md"
download "kirpr/config/adr-templates.md"       "$KIRPR_DIR/config/adr-templates.md"
download "kirpr/config/agent-rules.md"         "$KIRPR_DIR/config/agent-rules.md"
download "kirpr/config/style-examples.md"      "$KIRPR_DIR/config/style-examples.md"
download "kirpr/config/templates.md"           "$KIRPR_DIR/config/templates.md"
download "kirpr/config/workflow.md"            "$KIRPR_DIR/config/workflow.md"

# Prompts
download "kirpr/prompts/text.md"               "$KIRPR_DIR/prompts/text.md"

# Scripts
download "kirpr/scripts/fetch_jira.py"         "$KIRPR_DIR/scripts/fetch_jira.py"
download "kirpr/scripts/fetch_youtrack.py"     "$KIRPR_DIR/scripts/fetch_youtrack.py"
download "kirpr/scripts/validate_services.py"  "$KIRPR_DIR/scripts/validate_services.py"
download "kirpr/scripts/create_youtrack.py"    "$KIRPR_DIR/scripts/create_youtrack.py"

# Skill: expert-panel
download "skills/expert-panel/SKILL.md"                  "$PANEL_DIR/SKILL.md"
download "skills/expert-panel/experts/pike.md"           "$PANEL_DIR/experts/pike.md"
download "skills/expert-panel/experts/cheney.md"         "$PANEL_DIR/experts/cheney.md"
download "skills/expert-panel/experts/ford.md"           "$PANEL_DIR/experts/ford.md"
download "skills/expert-panel/experts/stonebraker.md"    "$PANEL_DIR/experts/stonebraker.md"
download "skills/expert-panel/modes/spec.md"             "$PANEL_DIR/modes/spec.md"
download "skills/expert-panel/modes/diff.md"             "$PANEL_DIR/modes/diff.md"

# --- Restore or seed custom-experts.md ---
if [ -n "$CUSTOM_BACKUP" ] && [ -f "$CUSTOM_BACKUP" ]; then
    cp "$CUSTOM_BACKUP" "$PANEL_DIR/custom-experts.md"
    rm "$CUSTOM_BACKUP"
    echo "  Restored custom-experts.md"
else
    download "skills/expert-panel/custom-experts.md"      "$PANEL_DIR/custom-experts.md"
fi

# --- Restore or configure tracker ---
if [ -n "$TRACKER_BACKUP" ] && [ -f "$TRACKER_BACKUP" ]; then
    cp "$TRACKER_BACKUP" "$KIRPR_DIR/config/tracker.md"
    rm "$TRACKER_BACKUP"
    echo "  Restored tracker.md"
elif [ ! -f "$KIRPR_DIR/config/tracker.md" ]; then
    echo ""
    echo "=== Tracker Setup ==="
    echo "Which issue tracker do you use?"
    echo "  1) YouTrack"
    echo "  2) Jira"
    echo "  3) None (skip)"
    printf "Choice [1-3]: "
    read -r tracker_choice

    case "$tracker_choice" in
        1)
            printf "YouTrack base URL (e.g. https://youtrack.example.com): "
            read -r youtrack_url
            youtrack_url="${youtrack_url%/}"
            cat > "$KIRPR_DIR/config/tracker.md" <<TRACKER_EOF
# Конфигурация трекера задач

## Активный трекер

Трекер: YouTrack
Скрипт: \`python3 ~/.claude/kirpr/scripts/fetch_youtrack.py {ISSUE_ID}\`
URL: ${youtrack_url}/issue/{ISSUE_ID}

## Переменные окружения

- \`YOUTRACK_URL\` — базовый URL (\`${youtrack_url}\`)
- \`YOUTRACK_TOKEN\` — Bearer-токен для API YouTrack (обязателен)

## Альтернативные трекеры

### Jira

Скрипт: \`python3 ~/.claude/kirpr/scripts/fetch_jira.py {ISSUE_ID}\`

Переменные окружения:
- \`JIRA_URL\` — базовый URL (например \`https://yourcompany.atlassian.net\`)
- \`JIRA_TOKEN\` — API-токен (обязателен)
- \`JIRA_EMAIL\` — email для Jira Cloud (опционален, для basic auth)
TRACKER_EOF
            echo "Tracker configured: YouTrack at $youtrack_url"
            echo ""
            echo "Don't forget to set environment variables:"
            echo "  export YOUTRACK_URL=$youtrack_url"
            echo "  export YOUTRACK_TOKEN=<your-token>"
            ;;
        2)
            printf "Jira base URL (e.g. https://yourcompany.atlassian.net): "
            read -r jira_url
            jira_url="${jira_url%/}"
            cat > "$KIRPR_DIR/config/tracker.md" <<TRACKER_EOF
# Конфигурация трекера задач

## Активный трекер

Трекер: Jira
Скрипт: \`python3 ~/.claude/kirpr/scripts/fetch_jira.py {ISSUE_ID}\`
URL: ${jira_url}/browse/{ISSUE_ID}

## Переменные окружения

- \`JIRA_URL\` — базовый URL (\`${jira_url}\`)
- \`JIRA_TOKEN\` — API-токен (обязателен)
- \`JIRA_EMAIL\` — email для Jira Cloud (опционален, для basic auth)

## Альтернативные трекеры

### YouTrack

Скрипт: \`python3 ~/.claude/kirpr/scripts/fetch_youtrack.py {ISSUE_ID}\`

Переменные окружения:
- \`YOUTRACK_URL\` — базовый URL (например \`https://youtrack.example.com\`)
- \`YOUTRACK_TOKEN\` — Bearer-токен для API YouTrack (обязателен)
TRACKER_EOF
            echo "Tracker configured: Jira at $jira_url"
            echo ""
            echo "Don't forget to set environment variables:"
            echo "  export JIRA_URL=$jira_url"
            echo "  export JIRA_TOKEN=<your-token>"
            echo "  export JIRA_EMAIL=<your-email>  # optional, for Jira Cloud"
            ;;
        3|"")
            echo "Tracker setup skipped. You can configure it later by editing:"
            echo "  $KIRPR_DIR/config/tracker.md"
            ;;
        *)
            echo "Unknown choice. Tracker setup skipped."
            ;;
    esac
fi

echo ""
echo "Done! kirpr commands are available as /kirpr:*, expert-panel skill as /expert-panel"
