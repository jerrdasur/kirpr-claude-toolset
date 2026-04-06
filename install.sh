#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"

echo "Installing kirpr from $REPO_DIR"

# --- Backup tracker.md if it exists ---
TRACKER_BACKUP=""
if [ -f "$KIRPR_DIR/config/tracker.md" ]; then
    TRACKER_BACKUP="$(mktemp)"
    cp "$KIRPR_DIR/config/tracker.md" "$TRACKER_BACKUP"
    echo "  Backed up tracker.md"
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

# --- Create directories ---
mkdir -p "$COMMANDS_DIR"
mkdir -p "$KIRPR_DIR/config"
mkdir -p "$KIRPR_DIR/scripts"

# --- Copy commands ---
for f in "$REPO_DIR"/commands/kirpr/*.md; do
    name="$(basename "$f")"
    cp "$f" "$COMMANDS_DIR/$name"
    echo "  commands/kirpr/$name -> copied"
done

# --- Copy config files (skip tracker.md.template) ---
for f in "$REPO_DIR"/kirpr/config/*.md; do
    name="$(basename "$f")"
    [ "$name" = "tracker.md.template" ] && continue
    cp "$f" "$KIRPR_DIR/config/$name"
    echo "  kirpr/config/$name -> copied"
done

# --- Copy prompts ---
if [ -d "$REPO_DIR/kirpr/prompts" ]; then
    mkdir -p "$KIRPR_DIR/prompts"
    for f in "$REPO_DIR"/kirpr/prompts/*.md; do
        [ -f "$f" ] || continue
        name="$(basename "$f")"
        cp "$f" "$KIRPR_DIR/prompts/$name"
        echo "  kirpr/prompts/$name -> copied"
    done
fi

# --- Copy scripts ---
for f in "$REPO_DIR"/kirpr/scripts/*.py; do
    name="$(basename "$f")"
    cp "$f" "$KIRPR_DIR/scripts/$name"
    echo "  kirpr/scripts/$name -> copied"
done

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
            echo "See the template at: $REPO_DIR/kirpr/config/tracker.md.template"
            ;;
        *)
            echo "Unknown choice. Tracker setup skipped."
            ;;
    esac
fi

echo ""
echo "Done! kirpr commands are now available in Claude Code as /kirpr:*"
