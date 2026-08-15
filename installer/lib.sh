#!/usr/bin/env bash

# This library is sourced by the local and remote installers. Keep it
# compatible with the Bash 3.2 shipped by macOS.

KIRPR_SKILLS=(
    kirpr-task-fetch kirpr-task-create kirpr-task-update kirpr-task-delete
    kirpr-tasks-decompose kirpr-tasks-review kirpr-tasks-adapt kirpr-tasks-push
    kirpr-adr-init kirpr-adr-write kirpr-adr-review kirpr-text
    expert-panel grill-me kirpr-flow
)
KIRPR_COMMANDS=(
    adr-init adr-review adr-write task-create task-delete task-fetch task-update
    tasks-adapt tasks-decompose tasks-push tasks-review text
)
KIRPR_CONFIG_FILES=(
    adr-review-rubric.md adr-templates.md agent-rules.md
    custom-experts.md.template style-examples.md tracker-runtime.md
    tracker.md.template workflow.md templates.md
)
KIRPR_PROMPTS=(text.md)
KIRPR_SCRIPTS=(
    create_youtrack.py fetch_jira.py fetch_youtrack.py manage_jira.py
    manage_youtrack.py validate_services.py
)

KIRPR_TARGET="${KIRPR_TARGET:-}"
KIRPR_STAGE_DIR="${KIRPR_STAGE_DIR:-}"
KIRPR_INPUT_OPEN="${KIRPR_INPUT_OPEN:-0}"
KIRPR_ROOT="${KIRPR_INSTALL_ROOT:-$HOME}"
KIRPR_INPUT="${KIRPR_INPUT_FILE:-/dev/tty}"
KIRPR_CONFIG_DIR="$KIRPR_ROOT/.config/kirpr"
KIRPR_RUNTIME_DIR="$KIRPR_ROOT/.local/share/kirpr"
KIRPR_CODEX_SKILLS_DIR="$KIRPR_ROOT/.agents/skills"
KIRPR_CLAUDE_SKILLS_DIR="$KIRPR_ROOT/.claude/skills"
KIRPR_CLAUDE_COMMANDS_DIR="$KIRPR_ROOT/.claude/commands/kirpr"
KIRPR_MANIFEST="$KIRPR_CONFIG_DIR/install-manifest"

kirpr_error() {
    printf '%s\n' "$*" >&2
}

kirpr_read_input() {
    if [ "$KIRPR_INPUT_OPEN" -ne 1 ]; then
        exec 3< "$KIRPR_INPUT" || return 1
        KIRPR_INPUT_OPEN=1
    fi
    IFS= read -r KIRPR_INPUT_VALUE <&3
}

parse_args() {
    KIRPR_TARGET=""

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --target)
                if [ "$#" -lt 2 ]; then
                    kirpr_error "--target requires claude|codex|all"
                    return 2
                fi
                case "$2" in
                    claude|codex|all) KIRPR_TARGET="$2" ;;
                    *)
                        kirpr_error "--target must be claude|codex|all"
                        return 2
                        ;;
                esac
                shift 2
                ;;
            *)
                kirpr_error "Unknown argument: $1 (use --target claude|codex|all)"
                return 2
                ;;
        esac
    done
}

choose_target() {
    local choice

    printf '%s\n' "Install kirpr for:"
    printf '%s\n' "  1) Claude Code"
    printf '%s\n' "  2) Codex"
    printf '%s\n' "  3) Both"
    printf '%s' "Choice [1-3]: "
    if ! kirpr_read_input; then
        kirpr_error "Cannot read target selection; use --target claude|codex|all"
        return 2
    fi
    choice="$KIRPR_INPUT_VALUE"

    case "$choice" in
        1) KIRPR_TARGET="claude" ;;
        2) KIRPR_TARGET="codex" ;;
        3) KIRPR_TARGET="all" ;;
        *)
            kirpr_error "Target must be 1, 2, or 3; use --target claude|codex|all"
            return 2
            ;;
    esac
}

resolve_paths() {
    KIRPR_ROOT="${KIRPR_INSTALL_ROOT:-$HOME}"
    KIRPR_INPUT="${KIRPR_INPUT_FILE:-/dev/tty}"
    KIRPR_CONFIG_DIR="$KIRPR_ROOT/.config/kirpr"
    KIRPR_RUNTIME_DIR="$KIRPR_ROOT/.local/share/kirpr"
    KIRPR_CODEX_SKILLS_DIR="$KIRPR_ROOT/.agents/skills"
    KIRPR_CLAUDE_SKILLS_DIR="$KIRPR_ROOT/.claude/skills"
    KIRPR_CLAUDE_COMMANDS_DIR="$KIRPR_ROOT/.claude/commands/kirpr"
    KIRPR_MANIFEST="$KIRPR_CONFIG_DIR/install-manifest"
}

validate_bundle() {
    local repo_dir skill command config prompt script

    repo_dir="$1"
    for skill in "${KIRPR_SKILLS[@]}"; do
        if [ ! -f "$repo_dir/skills/$skill/SKILL.md" ] || \
           [ ! -f "$repo_dir/skills/$skill/agents/openai.yaml" ]; then
            kirpr_error "Incomplete skill bundle: $skill"
            return 1
        fi
    done
    for command in "${KIRPR_COMMANDS[@]}"; do
        if [ ! -f "$repo_dir/commands/kirpr/$command.md" ]; then
            kirpr_error "Missing Claude adapter: $command"
            return 1
        fi
    done
    for config in "${KIRPR_CONFIG_FILES[@]}"; do
        if [ ! -f "$repo_dir/kirpr/config/$config" ]; then
            kirpr_error "Missing runtime config: $config"
            return 1
        fi
    done
    for prompt in "${KIRPR_PROMPTS[@]}"; do
        if [ ! -f "$repo_dir/kirpr/prompts/$prompt" ]; then
            kirpr_error "Missing runtime prompt: $prompt"
            return 1
        fi
    done
    for script in "${KIRPR_SCRIPTS[@]}"; do
        if [ ! -f "$repo_dir/kirpr/scripts/$script" ]; then
            kirpr_error "Missing runtime script: $script"
            return 1
        fi
    done
}

stage_bundle() {
    local repo_dir

    repo_dir="$1"
    if [ -z "$KIRPR_STAGE_DIR" ]; then
        kirpr_error "KIRPR_STAGE_DIR is not set"
        return 1
    fi
    mkdir -p "$KIRPR_STAGE_DIR/runtime" "$KIRPR_STAGE_DIR/skills" \
        "$KIRPR_STAGE_DIR/commands"
    cp -R "$repo_dir/kirpr/." "$KIRPR_STAGE_DIR/runtime/"
    cp -R "$repo_dir/skills/." "$KIRPR_STAGE_DIR/skills/"
    cp -R "$repo_dir/commands/kirpr" "$KIRPR_STAGE_DIR/commands/"
}

setup_tracker() {
    local tracker_choice tracker_url tracker_type tracker_issue_url tracker_kind tracker_script

    printf '%s\n' ""
    printf '%s\n' "=== Tracker Setup ==="
    printf '%s\n' "Which issue tracker do you use?"
    printf '%s\n' "  1) YouTrack"
    printf '%s\n' "  2) Jira"
    printf '%s\n' "  3) None (skip)"
    printf '%s' "Choice [1-3]: "
    if ! kirpr_read_input; then
        kirpr_error "Cannot read tracker selection"
        return 2
    fi
    tracker_choice="$KIRPR_INPUT_VALUE"

    case "$tracker_choice" in
        1)
            printf '%s' "YouTrack base URL: "
            kirpr_read_input || return 2
            tracker_url="$KIRPR_INPUT_VALUE"
            tracker_url="${tracker_url%/}"
            tracker_type="YouTrack"
            tracker_issue_url="$tracker_url/issue/{ISSUE_ID}"
            tracker_kind="youtrack"
            tracker_script="fetch_youtrack.py"
            ;;
        2)
            printf '%s' "Jira base URL: "
            kirpr_read_input || return 2
            tracker_url="$KIRPR_INPUT_VALUE"
            tracker_url="${tracker_url%/}"
            tracker_type="Jira"
            tracker_issue_url="$tracker_url/browse/{ISSUE_ID}"
            tracker_kind="jira"
            tracker_script="fetch_jira.py"
            ;;
        3|"")
            printf '%s\n' "Tracker setup skipped. Configure it later at:"
            printf '%s\n' "  $KIRPR_CONFIG_DIR/tracker.md"
            return 0
            ;;
        *)
            kirpr_error "Tracker choice must be 1, 2, or 3"
            return 2
            ;;
    esac

    awk \
        -v tracker_type="$tracker_type" \
        -v tracker_issue_url="$tracker_issue_url" \
        -v tracker_kind="$tracker_kind" \
        -v tracker_script="$tracker_script" '
        /^Трекер: \{\{TRACKER_TYPE\}\}$/ {
            print "Трекер: " tracker_type
            next
        }
        /^Скрипт: `python3 ~\/\.claude\/kirpr\/scripts\/\{\{TRACKER_SCRIPT\}\} \{ISSUE_ID\}`$/ {
            print "Скрипт: `python3 ~/.local/share/kirpr/scripts/" tracker_script " {ISSUE_ID}`"
            next
        }
        /^URL: \{\{TRACKER_ISSUE_URL\}\}$/ {
            print "URL: " tracker_issue_url
            next
        }
        /^\{\{TRACKER_ENV_VARS\}\}$/ {
            if (tracker_kind == "youtrack") {
                print "- `YOUTRACK_URL` — базовый URL"
                print "- `YOUTRACK_TOKEN` — Bearer-токен для API YouTrack (обязателен)"
            } else {
                print "- `JIRA_URL` — базовый URL"
                print "- `JIRA_TOKEN` — API-токен (обязателен)"
                print "- `JIRA_EMAIL` — email для Jira Cloud (опционален, для basic auth)"
            }
            next
        }
        { print }
    ' "$KIRPR_STAGE_DIR/runtime/config/tracker.md.template" > "$KIRPR_CONFIG_DIR/tracker.md"
    printf '%s\n' "Tracker configured: $tracker_type"
}

prepare_user_config() {
    mkdir -p "$KIRPR_CONFIG_DIR"
    if [ ! -f "$KIRPR_CONFIG_DIR/custom-experts.md" ]; then
        cp "$KIRPR_STAGE_DIR/runtime/config/custom-experts.md.template" \
            "$KIRPR_CONFIG_DIR/custom-experts.md"
    fi
    if [ ! -f "$KIRPR_CONFIG_DIR/tracker.md" ]; then
        setup_tracker
    fi
}

install_staged_bundle() {
    local skill

    mkdir -p "$KIRPR_RUNTIME_DIR"
    cp -R "$KIRPR_STAGE_DIR/runtime/." "$KIRPR_RUNTIME_DIR/"

    case "$KIRPR_TARGET" in
        codex|all)
            mkdir -p "$KIRPR_CODEX_SKILLS_DIR"
            for skill in "${KIRPR_SKILLS[@]}"; do
                cp -R "$KIRPR_STAGE_DIR/skills/$skill" "$KIRPR_CODEX_SKILLS_DIR/"
            done
            ;;
    esac
    case "$KIRPR_TARGET" in
        claude|all)
            mkdir -p "$KIRPR_CLAUDE_SKILLS_DIR" "$KIRPR_CLAUDE_COMMANDS_DIR"
            for skill in "${KIRPR_SKILLS[@]}"; do
                cp -R "$KIRPR_STAGE_DIR/skills/$skill" "$KIRPR_CLAUDE_SKILLS_DIR/"
            done
            cp -R "$KIRPR_STAGE_DIR/commands/kirpr/." "$KIRPR_CLAUDE_COMMANDS_DIR/"
            ;;
    esac
}

write_manifest() {
    local manifest_tmp

    mkdir -p "$KIRPR_CONFIG_DIR"
    manifest_tmp="$(mktemp "$KIRPR_CONFIG_DIR/.install-manifest.XXXXXX")"
    {
        printf 'version\t1\n'
        printf 'target\t%s\n' "$KIRPR_TARGET"
        printf 'path\tshared\t%s\n' "$KIRPR_RUNTIME_DIR"
        case "$KIRPR_TARGET" in
            codex|all) printf 'path\tcodex\t%s\n' "$KIRPR_CODEX_SKILLS_DIR" ;;
        esac
        case "$KIRPR_TARGET" in
            claude|all)
                printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_SKILLS_DIR"
                printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_COMMANDS_DIR"
                ;;
        esac
    } > "$manifest_tmp"
    mv "$manifest_tmp" "$KIRPR_MANIFEST"
}
