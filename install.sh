#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"

echo "Installing kirpr from $REPO_DIR"

# Create target directories
mkdir -p "$COMMANDS_DIR"
mkdir -p "$KIRPR_DIR/config"
mkdir -p "$KIRPR_DIR/scripts"

# --- Symlink commands ---
for f in "$REPO_DIR"/commands/kirpr/*.md; do
    name="$(basename "$f")"
    target="$COMMANDS_DIR/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "Warning: $target exists and is not a symlink, skipping (back up manually if needed)"
        continue
    fi
    ln -s "$f" "$target"
    echo "  commands/kirpr/$name -> linked"
done

# --- Symlink config files (except tracker.md which is user-specific) ---
for f in "$REPO_DIR"/kirpr/config/*.md; do
    name="$(basename "$f")"
    # Skip the template file
    [ "$name" = "tracker.md.template" ] && continue
    target="$KIRPR_DIR/config/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "Warning: $target exists and is not a symlink, skipping"
        continue
    fi
    ln -s "$f" "$target"
    echo "  kirpr/config/$name -> linked"
done

# --- Symlink scripts ---
for f in "$REPO_DIR"/kirpr/scripts/*.py; do
    name="$(basename "$f")"
    target="$KIRPR_DIR/scripts/$name"
    if [ -L "$target" ]; then
        rm "$target"
    elif [ -e "$target" ]; then
        echo "Warning: $target exists and is not a symlink, skipping"
        continue
    fi
    ln -s "$f" "$target"
    echo "  kirpr/scripts/$name -> linked"
done

# --- Configure tracker (interactive, only if tracker.md doesn't exist) ---
if [ -f "$KIRPR_DIR/config/tracker.md" ]; then
    echo ""
    echo "Tracker config already exists at $KIRPR_DIR/config/tracker.md, skipping setup."
else
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
