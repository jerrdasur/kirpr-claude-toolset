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
KIRPR_ROLLBACK_DIR="${KIRPR_ROLLBACK_DIR:-}"
KIRPR_ROLLBACK_RECORDS="${KIRPR_ROLLBACK_RECORDS:-}"
KIRPR_MANIFEST_RECORDS="${KIRPR_MANIFEST_RECORDS:-}"
KIRPR_MUTATION_STARTED=0
KIRPR_FAIL_INJECTED=0

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
    local repo_dir skill command config prompt script skill_dir adapter expected actual

    repo_dir="$1"
    for skill_dir in "$repo_dir"/skills/* "$repo_dir"/skills/.[!.]* "$repo_dir"/skills/..?*; do
        [ -d "$skill_dir" ] || continue
        skill="${skill_dir##*/}"
        if ! known_skill "$skill"; then
            kirpr_error "Unexpected skill in bundle: $skill"
            return 1
        fi
    done
    for skill in "${KIRPR_SKILLS[@]}"; do
        if [ ! -f "$repo_dir/skills/$skill/SKILL.md" ] || \
           [ ! -f "$repo_dir/skills/$skill/agents/openai.yaml" ]; then
            kirpr_error "Incomplete skill bundle: $skill"
            return 1
        fi
        if ! valid_skill_frontmatter "$skill" "$repo_dir/skills/$skill/SKILL.md"; then
            kirpr_error "Invalid skill front matter: $skill"
            return 1
        fi
        if ! valid_openai_metadata "$skill" "$repo_dir/skills/$skill/agents/openai.yaml"; then
            kirpr_error "Invalid OpenAI metadata: $skill"
            return 1
        fi
    done
    for adapter in "$repo_dir"/commands/kirpr/*.md \
        "$repo_dir"/commands/kirpr/.[!.]*.md \
        "$repo_dir"/commands/kirpr/..?*.md; do
        [ -f "$adapter" ] || continue
        command="${adapter##*/}"; command="${command%.md}"
        if ! known_command "$command"; then
            kirpr_error "Unexpected Claude adapter: $command"
            return 1
        fi
    done
    for command in "${KIRPR_COMMANDS[@]}"; do
        if [ ! -f "$repo_dir/commands/kirpr/$command.md" ]; then
            kirpr_error "Missing Claude adapter: $command"
            return 1
        fi
        expected="$(printf '%s\n' \
            '# Совместимый вызов kirpr' \
            '' \
            "Полностью прочитай \`~/.claude/skills/kirpr-$command/SKILL.md\` и следуй ему." \
            '' \
            'Аргументы явного вызова:' \
            '' \
            '```text' \
            "\$ARGUMENTS" \
            '```')"
        actual="$(cat "$repo_dir/commands/kirpr/$command.md")"
        if [ "$actual" != "$expected" ]; then
            kirpr_error "Invalid Claude adapter: $command"
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

known_skill() {
    local expected

    for expected in "${KIRPR_SKILLS[@]}"; do
        [ "$1" = "$expected" ] && return 0
    done
    return 1
}

known_command() {
    local expected

    for expected in "${KIRPR_COMMANDS[@]}"; do
        [ "$1" = "$expected" ] && return 0
    done
    return 1
}

valid_skill_frontmatter() {
    local expected file

    expected="$1"; file="$2"
    awk -v expected="$expected" '
        NR == 1 {
            if ($0 != "---") bad = 1
            next
        }
        closed { next }
        $0 == "---" { closed = 1; next }
        /^[[:space:]]*$/ { next }
        {
            if ($0 !~ /^[A-Za-z_][A-Za-z0-9_-]*:[[:space:]]*.+$/) {
                bad = 1
                next
            }
        }
        /^name:[[:space:]]*/ {
            value = $0
            sub(/^name:[[:space:]]*/, "", value)
            if ((substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") ||
                (substr(value, 1, 1) == "\047" && substr(value, length(value), 1) == "\047")) {
                value = substr(value, 2, length(value) - 2)
            }
            names++
            if (value != expected) bad = 1
        }
        /^description:[[:space:]]*/ { descriptions++ }
        END { exit !(closed && names == 1 && descriptions == 1 && !bad) }
    ' "$file"
}

valid_openai_metadata() {
    local expected file

    expected="$1"; file="$2"
    awk -v expected="$expected" '
        function scalar(line, value) {
            value = line
            sub(/^[^:]+:[[:space:]]*/, "", value)
            sub(/[[:space:]]+$/, "", value)
            if ((substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") ||
                (substr(value, 1, 1) == "\047" && substr(value, length(value), 1) == "\047")) {
                value = substr(value, 2, length(value) - 2)
            }
            return value
        }
        /^[[:space:]]*$/ { next }
        /^interface:[[:space:]]*$/ { interface_sections++; section = "interface"; next }
        /^policy:[[:space:]]*$/ { policy_sections++; section = "policy"; next }
        /^  display_name:[[:space:]]*.+$/ && section == "interface" {
            display_names++; display_name = scalar($0); next
        }
        /^  short_description:[[:space:]]*.+$/ && section == "interface" {
            short_descriptions++; short_description = scalar($0); next
        }
        /^  default_prompt:[[:space:]]*.+$/ && section == "interface" {
            default_prompts++; default_prompt = scalar($0); next
        }
        /^  allow_implicit_invocation:[[:space:]]*false[[:space:]]*$/ && section == "policy" {
            allow_false++; next
        }
        { bad = 1 }
        END {
            valid = interface_sections == 1 && policy_sections == 1 &&
                display_names == 1 && short_descriptions == 1 && default_prompts == 1 &&
                allow_false == 1 && display_name != "" && short_description != "" &&
                index(default_prompt, "$" expected) > 0 && !bad
            exit !valid
        }
    ' "$file"
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
    local tracker_choice tracker_url tracker_type tracker_issue_url tracker_kind

    printf '\n=== Tracker Setup ===\nWhich issue tracker do you use?\n'
    printf '%s\n' '  1) YouTrack' '  2) Jira' '  3) None (skip)'
    printf '%s' 'Choice [1-3]: '
    kirpr_read_input || { kirpr_error 'Cannot read tracker selection'; return 2; }
    tracker_choice="$KIRPR_INPUT_VALUE"
    case "$tracker_choice" in
        1) printf '%s' 'YouTrack base URL: '; kirpr_read_input || return 2
           tracker_url="${KIRPR_INPUT_VALUE%/}"; tracker_type=YouTrack
           tracker_issue_url="$tracker_url/issue/{ISSUE_ID}"; tracker_kind=youtrack ;;
        2) printf '%s' 'Jira base URL: '; kirpr_read_input || return 2
           tracker_url="${KIRPR_INPUT_VALUE%/}"; tracker_type=Jira
           tracker_issue_url="$tracker_url/browse/{ISSUE_ID}"; tracker_kind=jira ;;
        3|'') printf '%s\n' "Tracker setup skipped. Configure it later at: $KIRPR_CONFIG_DIR/tracker.md"; return 0 ;;
        *) kirpr_error 'Tracker choice must be 1, 2, or 3'; return 2 ;;
    esac
    awk -v tracker_type="$tracker_type" -v tracker_issue_url="$tracker_issue_url" -v tracker_kind="$tracker_kind" '
        /^Трекер: \{\{TRACKER_TYPE\}\}$/ { print "Трекер: " tracker_type; next }
        /^URL: \{\{TRACKER_ISSUE_URL\}\}$/ { print "URL: " tracker_issue_url; next }
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
    ' "$KIRPR_STAGE_DIR/runtime/config/tracker.md.template" > "$KIRPR_STAGE_DIR/user-config/tracker.md"
    printf '%s\n' "Tracker configured: $tracker_type"
}

normalize_tracker() {
    awk '!/^Скрипт:/' "$1" > "$2"
}

select_user_file() {
    local kind dest candidate normalized first temp_dir

    kind="$1"; dest="$2"; shift 2
    KIRPR_SELECTED=0
    temp_dir="$(mktemp -d)"; first=''
    for candidate in "$@"; do
        [ -f "$candidate" ] || continue
        normalized="$temp_dir/candidate"
        if [ "$kind" = tracker ]; then normalize_tracker "$candidate" "$normalized"; else cp "$candidate" "$normalized"; fi
        if [ -z "$first" ]; then
            first="$temp_dir/first"; cp "$normalized" "$first"
        elif ! cmp -s "$first" "$normalized"; then
            kirpr_error "Conflicting $kind files:"
            for conflict_candidate in "$@"; do
                [ -f "$conflict_candidate" ] && kirpr_error "  $conflict_candidate"
            done
            rm -rf "$temp_dir"; return 1
        fi
    done
    if [ -n "$first" ]; then
        KIRPR_SELECTED=1
        if [ ! -f "$dest" ] || ! cmp -s "$dest" "$first"; then mkdir -p "$(dirname "$dest")"; cp "$first" "$dest"; fi
    fi
    rm -rf "$temp_dir"
}

prepare_user_config() {
    local user_config_dir

    user_config_dir="$KIRPR_STAGE_DIR/user-config"; mkdir -p "$user_config_dir"
    select_user_file custom-experts "$user_config_dir/custom-experts.md" \
        "$KIRPR_CONFIG_DIR/custom-experts.md" \
        "$KIRPR_CLAUDE_SKILLS_DIR/expert-panel/custom-experts.md" \
        "$KIRPR_CODEX_SKILLS_DIR/expert-panel/custom-experts.md"
    if [ "$KIRPR_SELECTED" -eq 0 ]; then
        cp "$KIRPR_STAGE_DIR/runtime/config/custom-experts.md.template" "$user_config_dir/custom-experts.md"
    fi
    select_user_file tracker "$user_config_dir/tracker.md" \
        "$KIRPR_CONFIG_DIR/tracker.md" "$KIRPR_ROOT/.claude/kirpr/config/tracker.md" \
        "$KIRPR_ROOT/.codex/kirpr/config/tracker.md"
    if [ "$KIRPR_SELECTED" -eq 0 ]; then
        setup_tracker
    fi
}

manifest_owns() {
    local destination kind path

    destination="$1"; [ -f "$KIRPR_MANIFEST" ] || return 1
    while IFS=$'\t' read -r kind _ path; do
        [ "$kind" = path ] || continue
        [ "$path" = "$destination" ] && return 0
        case "$path" in
            "$KIRPR_CODEX_SKILLS_DIR"|"$KIRPR_CLAUDE_SKILLS_DIR"|"$KIRPR_CLAUDE_COMMANDS_DIR")
                case "$destination" in "$path"/*) return 0 ;; esac ;;
        esac
    done < "$KIRPR_MANIFEST"
    return 1
}

managed_path_is_safe() {
    local path parent

    path="$1"
    case "$path" in "$KIRPR_ROOT"/*) ;; *) return 1 ;; esac
    case "$path/" in *'/../'*|*'/./'*|*'//'*) return 1 ;; esac
    parent="$path"
    while [ "$parent" != "$KIRPR_ROOT" ]; do
        [ -L "$parent" ] && return 1
        parent="${parent%/*}"
    done
    return 0
}

require_safe_destination() {
    if ! managed_path_is_safe "$1"; then
        kirpr_error "Unsafe installer destination: $1"
        return 1
    fi
}

validate_destination_layout() {
    local path skill command

    for path in \
        "$KIRPR_CONFIG_DIR" \
        "$KIRPR_CONFIG_DIR/custom-experts.md" \
        "$KIRPR_CONFIG_DIR/tracker.md" \
        "$KIRPR_CONFIG_DIR/backups" \
        "$KIRPR_MANIFEST" \
        "$KIRPR_RUNTIME_DIR"; do
        require_safe_destination "$path" || return $?
    done
    case "$KIRPR_TARGET" in
        codex|all)
            require_safe_destination "$KIRPR_CODEX_SKILLS_DIR" || return $?
            for skill in "${KIRPR_SKILLS[@]}"; do
                require_safe_destination "$KIRPR_CODEX_SKILLS_DIR/$skill" || return $?
            done
            require_safe_destination "$KIRPR_CODEX_SKILLS_DIR/kirpr-adr" || return $?
            ;;
    esac
    case "$KIRPR_TARGET" in
        claude|all)
            require_safe_destination "$KIRPR_CLAUDE_SKILLS_DIR" || return $?
            require_safe_destination "$KIRPR_CLAUDE_COMMANDS_DIR" || return $?
            for skill in "${KIRPR_SKILLS[@]}"; do
                require_safe_destination "$KIRPR_CLAUDE_SKILLS_DIR/$skill" || return $?
            done
            for command in "${KIRPR_COMMANDS[@]}"; do
                require_safe_destination "$KIRPR_CLAUDE_COMMANDS_DIR/$command.md" || return $?
            done
            ;;
    esac
}

valid_managed_path() {
    local target path skill command

    target="$1"; path="$2"
    managed_path_is_safe "$path" || return 1
    case "$target" in
        shared) [ "$path" = "$KIRPR_RUNTIME_DIR" ] && return 0 ;;
        codex)
            [ "$path" = "$KIRPR_CODEX_SKILLS_DIR" ] && return 0
            for skill in "${KIRPR_SKILLS[@]}"; do
                [ "$path" = "$KIRPR_CODEX_SKILLS_DIR/$skill" ] && return 0
            done
            ;;
        claude)
            [ "$path" = "$KIRPR_CLAUDE_SKILLS_DIR" ] && return 0
            [ "$path" = "$KIRPR_CLAUDE_COMMANDS_DIR" ] && return 0
            for skill in "${KIRPR_SKILLS[@]}"; do
                [ "$path" = "$KIRPR_CLAUDE_SKILLS_DIR/$skill" ] && return 0
            done
            for command in "${KIRPR_COMMANDS[@]}"; do
                [ "$path" = "$KIRPR_CLAUDE_COMMANDS_DIR/$command.md" ] && return 0
            done
            ;;
    esac
    return 1
}

valid_backup_original() {
    local target original skill command

    target="$1"; original="$2"
    managed_path_is_safe "$original" || return 1
    case "$target" in
        shared) [ "$original" = "$KIRPR_RUNTIME_DIR" ] && return 0 ;;
        codex)
            for skill in "${KIRPR_SKILLS[@]}"; do
                [ "$original" = "$KIRPR_CODEX_SKILLS_DIR/$skill" ] && return 0
            done
            ;;
        claude)
            for skill in "${KIRPR_SKILLS[@]}"; do
                [ "$original" = "$KIRPR_CLAUDE_SKILLS_DIR/$skill" ] && return 0
            done
            for command in "${KIRPR_COMMANDS[@]}"; do
                [ "$original" = "$KIRPR_CLAUDE_COMMANDS_DIR/$command.md" ] && return 0
            done
            ;;
    esac
    case "$target:$original" in
        "shared:$KIRPR_CONFIG_DIR/custom-experts.md"|"shared:$KIRPR_CONFIG_DIR/tracker.md"|\
        "codex:$KIRPR_CODEX_SKILLS_DIR/kirpr-adr")
            return 0
            ;;
    esac
    return 1
}

valid_backup_path() {
    local backup root parent

    backup="$1"; root="$KIRPR_CONFIG_DIR/backups"
    case "$backup" in "$root"/*) ;; *) return 1 ;; esac
    case "$backup/" in *'/../'*|*'/./'*|*'//'*) return 1 ;; esac
    managed_path_is_safe "$root" || return 1
    parent="$backup"
    while [ "$parent" != "$root" ]; do
        [ -L "$parent" ] && return 1
        parent="${parent%/*}"
    done
    [ -L "$root" ] && return 1
    return 0
}

validate_manifest() {
    local line kind target path backup extra valid

    [ -f "$KIRPR_MANIFEST" ] || return 0
    valid=1
    while IFS= read -r line || [ -n "$line" ]; do
        IFS=$'\t' read -r kind target path backup extra <<< "$line"
        case "$kind" in
            version)
                [ "$target" = 1 ] && [ -z "$path" ] && [ -z "$backup" ] && [ -z "$extra" ] || { valid=0; break; }
                ;;
            target)
                case "$target" in codex|claude) ;; *) valid=0; break ;; esac
                [ -z "$path" ] && [ -z "$backup" ] && [ -z "$extra" ] || { valid=0; break; }
                ;;
            path)
                case "$target" in shared|codex|claude) ;; *) valid=0; break ;; esac
                valid_managed_path "$target" "$path" && [ -z "$backup" ] && [ -z "$extra" ] || { valid=0; break; }
                ;;
            backup)
                case "$target" in shared|codex|claude) ;; *) valid=0; break ;; esac
                valid_backup_original "$target" "$path" && valid_backup_path "$backup" && [ -z "$extra" ] || { valid=0; break; }
                ;;
            *) valid=0; break ;;
        esac
    done < "$KIRPR_MANIFEST"
    if [ "$valid" -ne 1 ]; then
        kirpr_error 'Invalid install manifest'
        return 1
    fi
}

backup_path() {
    local original relative
    original="$1"; relative="${original#"$KIRPR_ROOT"/}"
    printf '%s/%s\n' "$KIRPR_BACKUP_DIR" "$relative"
}

record_backup() { printf 'backup\t%s\t%s\t%s\n' "$1" "$2" "$3" >> "$KIRPR_MANIFEST_RECORDS"; }

begin_install_transaction() {
    KIRPR_ROLLBACK_DIR="$(mktemp -d)"
    KIRPR_ROLLBACK_RECORDS="$KIRPR_ROLLBACK_DIR/records"
    KIRPR_MANIFEST_RECORDS="$KIRPR_ROLLBACK_DIR/manifest-records"
    KIRPR_BACKUP_DIR=''
    : > "$KIRPR_ROLLBACK_RECORDS"; : > "$KIRPR_MANIFEST_RECORDS"
}

ensure_backup_dir() {
    [ -n "$KIRPR_BACKUP_DIR" ] && return 0
    managed_path_is_safe "$KIRPR_CONFIG_DIR" || return 1
    [ -L "$KIRPR_CONFIG_DIR/backups" ] && return 1
    mkdir -p "$KIRPR_CONFIG_DIR/backups"
    KIRPR_BACKUP_DIR="$(mktemp -d "$KIRPR_CONFIG_DIR/backups/$(date +%Y%m%d-%H%M%S).XXXXXX")"
}

record_rollback() {
    local destination relative saved state recorded_path
    destination="$1"
    while IFS=$'\t' read -r state recorded_path saved; do [ "$recorded_path" = "$destination" ] && return 0; done < "$KIRPR_ROLLBACK_RECORDS"
    relative="${destination#"$KIRPR_ROOT"/}"; saved="$KIRPR_ROLLBACK_DIR/original/$relative"
    if [ -e "$destination" ] || [ -L "$destination" ]; then
        mkdir -p "$(dirname "$saved")" || return $?
        cp -R "$destination" "$saved" || return $?
        printf 'present\t%s\t%s\n' "$destination" "$saved" >> "$KIRPR_ROLLBACK_RECORDS"
    else
        printf 'absent\t%s\t\n' "$destination" >> "$KIRPR_ROLLBACK_RECORDS"
    fi
}

backup_displaced() {
    local target destination force backup
    target="$1"; destination="$2"; force="${3:-0}"
    if { [ "$force" = 1 ] || ! manifest_owns "$destination"; } && { [ -e "$destination" ] || [ -L "$destination" ]; }; then
        ensure_backup_dir || return $?
        backup="$(backup_path "$destination")"
        mkdir -p "$(dirname "$backup")" || return $?
        cp -R "$destination" "$backup" || return $?
        record_backup "$target" "$destination" "$backup"
    fi
}

replace_managed_path() {
    local target source destination
    target="$1"; source="$2"; destination="$3"
    record_rollback "$destination" || return $?
    backup_displaced "$target" "$destination" || return $?
    KIRPR_MUTATION_STARTED=1
    mkdir -p "$(dirname "$destination")" || return $?
    rm -rf "$destination" || return $?
    cp -R "$source" "$destination" || return $?
    # Internal rollback-test seam. Failure switches are inert for normal installs
    # unless the test suite explicitly enables this gate.
    if [ "${KIRPR_INTERNAL_TEST_MODE:-}" = 1 ]; then
        if [ "${KIRPR_TEST_FAIL_AFTER_INSTALL:-}" = 1 ] && [ "$KIRPR_FAIL_INJECTED" -eq 0 ]; then
            KIRPR_FAIL_INJECTED=1
            return 90
        fi
        if [ "${KIRPR_TEST_FAIL_AFTER_SKILL:-}" = "$(basename "$destination")" ]; then
            return 90
        fi
    fi
}

install_user_config() {
    local name source destination
    for name in custom-experts.md tracker.md; do
        source="$KIRPR_STAGE_DIR/user-config/$name"; destination="$KIRPR_CONFIG_DIR/$name"
        [ -f "$source" ] || continue
        if [ ! -f "$destination" ] || ! cmp -s "$source" "$destination"; then
            replace_managed_path shared "$source" "$destination" || return $?
        fi
    done
}

retire_codex_adr() {
    local destination
    destination="$KIRPR_CODEX_SKILLS_DIR/kirpr-adr"
    [ -e "$destination" ] || [ -L "$destination" ] || return 0
    record_rollback "$destination" || return $?
    backup_displaced codex "$destination" 1 || return $?
    # shellcheck disable=SC2034 # Read by install.sh's EXIT trap.
    KIRPR_MUTATION_STARTED=1
    rm -rf "$destination"
}

rollback_install() {
    local state destination saved kind target original backup
    [ -f "$KIRPR_ROLLBACK_RECORDS" ] || return 0
    while IFS=$'\t' read -r state destination saved; do
        [ -n "$destination" ] || continue; rm -rf "$destination"
        if [ "$state" = present ]; then mkdir -p "$(dirname "$destination")"; cp -R "$saved" "$destination"; fi
        printf 'Restored %s\n' "$destination" >&2
    done < "$KIRPR_ROLLBACK_RECORDS"
    while IFS=$'\t' read -r kind target original backup; do
        [ "$kind" = backup ] || continue
        [ -n "$backup" ] && rm -rf "$backup"
    done < "$KIRPR_MANIFEST_RECORDS"
}

install_staged_bundle() {
    local skill command
    install_user_config || return $?
    case "$KIRPR_TARGET" in
        codex|all)
            for skill in "${KIRPR_SKILLS[@]}"; do
                replace_managed_path codex "$KIRPR_STAGE_DIR/skills/$skill" "$KIRPR_CODEX_SKILLS_DIR/$skill" || return $?
            done
            retire_codex_adr || return $? ;;
    esac
    case "$KIRPR_TARGET" in
        claude|all)
            for skill in "${KIRPR_SKILLS[@]}"; do
                replace_managed_path claude "$KIRPR_STAGE_DIR/skills/$skill" "$KIRPR_CLAUDE_SKILLS_DIR/$skill" || return $?
            done
            for command in "${KIRPR_COMMANDS[@]}"; do
                replace_managed_path claude "$KIRPR_STAGE_DIR/commands/kirpr/$command.md" "$KIRPR_CLAUDE_COMMANDS_DIR/$command.md" || return $?
            done ;;
    esac
    replace_managed_path shared "$KIRPR_STAGE_DIR/runtime" "$KIRPR_RUNTIME_DIR" || return $?
}

append_manifest_paths() {
    local target skill command
    target="$1"
    case "$target" in
        codex) printf 'path\tcodex\t%s\n' "$KIRPR_CODEX_SKILLS_DIR"; for skill in "${KIRPR_SKILLS[@]}"; do printf 'path\tcodex\t%s\n' "$KIRPR_CODEX_SKILLS_DIR/$skill"; done ;;
        claude) printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_SKILLS_DIR"; printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_COMMANDS_DIR"; for skill in "${KIRPR_SKILLS[@]}"; do printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_SKILLS_DIR/$skill"; done; for command in "${KIRPR_COMMANDS[@]}"; do printf 'path\tclaude\t%s\n' "$KIRPR_CLAUDE_COMMANDS_DIR/$command.md"; done ;;
    esac
}

target_selected() { case "$KIRPR_TARGET:$1" in codex:codex|claude:claude|all:codex|all:claude) return 0;; esac; return 1; }

write_manifest() {
    local manifest_tmp kind target path backup
    mkdir -p "$KIRPR_CONFIG_DIR"; manifest_tmp="$(mktemp "$KIRPR_CONFIG_DIR/.install-manifest.XXXXXX")"
    {
        printf 'version\t1\n'
        if [ -f "$KIRPR_MANIFEST" ]; then
            while IFS=$'\t' read -r kind target path backup; do
                case "$kind" in
                    version) ;;
                    backup) printf 'backup\t%s\t%s\t%s\n' "$target" "$path" "$backup" ;;
                    path)
                        [ "$target" = shared ] && continue
                        if ! target_selected "$target"; then printf 'path\t%s\t%s\n' "$target" "$path"; fi ;;
                    target) if ! target_selected "$target"; then printf 'target\t%s\n' "$target"; fi ;;
                esac
            done < "$KIRPR_MANIFEST"
        fi
        case "$KIRPR_TARGET" in codex|all) printf 'target\tcodex\n'; append_manifest_paths codex;; esac
        case "$KIRPR_TARGET" in claude|all) printf 'target\tclaude\n'; append_manifest_paths claude;; esac
        printf 'path\tshared\t%s\n' "$KIRPR_RUNTIME_DIR"
        cat "$KIRPR_MANIFEST_RECORDS"
    } > "$manifest_tmp"
    mv "$manifest_tmp" "$KIRPR_MANIFEST"
}

uninstall_target() {
    local selected target path
    selected="$1"; [ -f "$KIRPR_MANIFEST" ] || return 0
    while IFS=$'\t' read -r target path; do
        [ "$target" = "$selected" ] || continue
        case "$path" in "$KIRPR_CODEX_SKILLS_DIR"|"$KIRPR_CLAUDE_SKILLS_DIR"|"$KIRPR_CLAUDE_COMMANDS_DIR") continue;; esac
        [ -e "$path" ] || [ -L "$path" ] || continue; rm -rf "$path"; printf 'Removed %s\n' "$path"
    done < <(awk -F '\t' '$1 == "path" { print $2 "\t" $3 }' "$KIRPR_MANIFEST")
}

restore_displaced() {
    local selected kind target original backup
    selected="$1"; [ -f "$KIRPR_MANIFEST" ] || return 0
    while IFS=$'\t' read -r kind target original backup; do
        [ "$kind" = backup ] && [ "$target" = "$selected" ] || continue
        if { [ -e "$original" ] || [ -L "$original" ]; } || { [ ! -e "$backup" ] && [ ! -L "$backup" ]; }; then continue; fi
        mkdir -p "$(dirname "$original")"; cp -R "$backup" "$original"; printf 'Restored %s\n' "$original"
    done < "$KIRPR_MANIFEST"
}
