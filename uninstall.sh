#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=installer/lib.sh
. "$REPO_DIR/installer/lib.sh"

manifest_has_target() {
    local selected

    selected="$1"
    awk -F '\t' -v selected="$selected" '$1 == "target" && $2 == selected { found = 1 } END { exit !found }' "$KIRPR_MANIFEST"
}

manifest_has_shared_runtime() {
    awk -F '\t' -v runtime="$KIRPR_RUNTIME_DIR" '$1 == "path" && $2 == "shared" && $3 == runtime { found = 1 } END { exit !found }' "$KIRPR_MANIFEST"
}

selection_includes_target() {
    case "$1:$2" in
        codex:codex|claude:claude|all:codex|all:claude) return 0 ;;
    esac
    return 1
}

selection_removes_last_target() {
    local selected found

    selected="$1"
    found=0
    if manifest_has_target codex; then
        found=1
        selection_includes_target "$selected" codex || return 1
    fi
    if manifest_has_target claude; then
        found=1
        selection_includes_target "$selected" claude || return 1
    fi
    [ "$found" -eq 1 ] || return 1
    return 0
}

selection_has_backup() {
    local selected include_shared

    selected="$1"; include_shared="$2"
    awk -F '\t' -v selected="$selected" -v include_shared="$include_shared" '
        $1 != "backup" { next }
        (selected == "all" && ($2 == "codex" || $2 == "claude")) ||
        (selected == $2) ||
        (include_shared == "1" && $2 == "shared") { found = 1 }
        END { exit !found }
    ' "$KIRPR_MANIFEST"
}

rewrite_manifest_after_uninstall() {
    local selected include_shared manifest_tmp kind target path backup

    selected="$1"; include_shared="$2"
    manifest_tmp="$(mktemp "$KIRPR_CONFIG_DIR/.install-manifest.XXXXXX")"
    {
        printf 'version\t1\n'
        while IFS=$'\t' read -r kind target path backup; do
            [ "$kind" = version ] && continue
            if selection_includes_target "$selected" "$target"; then continue; fi
            if [ "$include_shared" = 1 ] && [ "$target" = shared ]; then continue; fi
            if [ "$kind" = backup ]; then
                printf 'backup\t%s\t%s\t%s\n' "$target" "$path" "$backup"
            elif [ "$kind" = path ]; then
                printf 'path\t%s\t%s\n' "$target" "$path"
            elif [ "$kind" = target ]; then
                printf 'target\t%s\n' "$target"
            fi
        done < "$KIRPR_MANIFEST"
    } > "$manifest_tmp"
    mv "$manifest_tmp" "$KIRPR_MANIFEST"
}

remove_runtime_if_recorded() {
    local remove_shared

    remove_shared="$1"
    [ "$remove_shared" = 1 ] || return 0
    if [ -e "$KIRPR_RUNTIME_DIR" ] || [ -L "$KIRPR_RUNTIME_DIR" ]; then
        rm -rf "$KIRPR_RUNTIME_DIR"
        printf 'Removed %s\n' "$KIRPR_RUNTIME_DIR"
    fi
}

restore_displaced_selection() {
    local selected include_shared kind target original backup

    selected="$1"; include_shared="$2"
    while IFS=$'\t' read -r kind target original backup; do
        [ "$kind" = backup ] || continue
        if ! selection_includes_target "$selected" "$target" && { [ "$include_shared" != 1 ] || [ "$target" != shared ]; }; then
            continue
        fi
        if { [ -e "$original" ] || [ -L "$original" ]; } || { [ ! -e "$backup" ] && [ ! -L "$backup" ]; }; then
            continue
        fi
        mkdir -p "$(dirname "$original")"
        cp -R "$backup" "$original"
        printf 'Restored %s\n' "$original"
    done < "$KIRPR_MANIFEST"
}

main() {
    local remove_shared restore

    parse_args "$@"
    [ -n "$KIRPR_TARGET" ] || choose_target
    resolve_paths
    [ -f "$KIRPR_MANIFEST" ] || { printf '%s\n' 'No kirpr installation manifest found.'; return 0; }
    validate_manifest
    remove_shared=0
    if selection_removes_last_target "$KIRPR_TARGET" && manifest_has_shared_runtime; then
        remove_shared=1
    fi
    restore=n
    if selection_has_backup "$KIRPR_TARGET" "$remove_shared"; then
        printf '%s' 'Restore displaced content? [y/N]: '
        if kirpr_read_input; then restore="$KIRPR_INPUT_VALUE"; fi
    fi
    case "$KIRPR_TARGET" in
        codex) uninstall_target codex ;;
        claude) uninstall_target claude ;;
        all) uninstall_target codex; uninstall_target claude ;;
    esac
    remove_runtime_if_recorded "$remove_shared"
    if [ "$restore" = y ] || [ "$restore" = Y ]; then
        restore_displaced_selection "$KIRPR_TARGET" "$remove_shared"
    fi
    rewrite_manifest_after_uninstall "$KIRPR_TARGET" "$remove_shared"
}

main "$@"
