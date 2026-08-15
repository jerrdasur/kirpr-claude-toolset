#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=installer/lib.sh
. "$REPO_DIR/installer/lib.sh"

manifest_has_backup() {
    local selected

    selected="$1"
    [ -f "$KIRPR_MANIFEST" ] || return 1
    awk -F '\t' -v selected="$selected" '$1 == "backup" && $2 == selected { found = 1 } END { exit !found }' "$KIRPR_MANIFEST"
}

manifest_has_target() {
    local selected

    selected="$1"
    [ -f "$KIRPR_MANIFEST" ] || return 1
    awk -F '\t' -v selected="$selected" '$1 == "target" && $2 == selected { found = 1 } END { exit !found }' "$KIRPR_MANIFEST"
}

rewrite_manifest_after_uninstall() {
    local remove_target manifest_tmp kind target path backup remaining

    remove_target="$1"
    manifest_tmp="$(mktemp "$KIRPR_CONFIG_DIR/.install-manifest.XXXXXX")"
    remaining=0
    if [ "$remove_target" != codex ] && manifest_has_target codex; then remaining=1; fi
    if [ "$remove_target" != claude ] && manifest_has_target claude; then remaining=1; fi
    {
        printf 'version\t1\n'
        while IFS=$'\t' read -r kind target path backup; do
            [ "$kind" = version ] && continue
            [ "$target" = "$remove_target" ] && continue
            if [ "$kind" = path ] && [ "$target" = shared ] && [ "$remaining" -eq 0 ]; then
                continue
            fi
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

remove_runtime_if_unused() {
    if ! manifest_has_target codex && ! manifest_has_target claude; then
        if [ -e "$KIRPR_RUNTIME_DIR" ] || [ -L "$KIRPR_RUNTIME_DIR" ]; then
            rm -rf "$KIRPR_RUNTIME_DIR"
            printf 'Removed %s\n' "$KIRPR_RUNTIME_DIR"
        fi
    fi
}

uninstall_one_target() {
    local selected restore

    selected="$1"
    manifest_has_target "$selected" || return 0
    restore=n
    if manifest_has_backup "$selected"; then
        printf 'Restore displaced content for %s? [y/N]: ' "$selected"
        if kirpr_read_input; then restore="$KIRPR_INPUT_VALUE"; fi
    fi
    uninstall_target "$selected"
    if [ "$restore" = y ] || [ "$restore" = Y ]; then restore_displaced "$selected"; fi
    rewrite_manifest_after_uninstall "$selected"
    remove_runtime_if_unused
}

main() {
    parse_args "$@"
    [ -n "$KIRPR_TARGET" ] || choose_target
    resolve_paths
    [ -f "$KIRPR_MANIFEST" ] || { printf '%s\n' 'No kirpr installation manifest found.'; return 0; }
    case "$KIRPR_TARGET" in
        codex) uninstall_one_target codex ;;
        claude) uninstall_one_target claude ;;
        all) uninstall_one_target codex; uninstall_one_target claude ;;
    esac
}

main "$@"
