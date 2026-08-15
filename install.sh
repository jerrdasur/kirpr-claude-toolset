#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=installer/lib.sh
. "$REPO_DIR/installer/lib.sh"

cleanup_install() {
    local status=$?
    trap - EXIT
    if [ "$status" -ne 0 ] && [ "$KIRPR_MUTATION_STARTED" -eq 1 ]; then
        rollback_install
    fi
    [ -n "${KIRPR_STAGE_DIR:-}" ] && rm -rf "$KIRPR_STAGE_DIR"
    [ -n "${KIRPR_ROLLBACK_DIR:-}" ] && rm -rf "$KIRPR_ROLLBACK_DIR"
    exit "$status"
}

main() {
    parse_args "$@"
    [ -n "$KIRPR_TARGET" ] || choose_target
    resolve_paths
    validate_destination_layout
    validate_manifest
    validate_bundle "$REPO_DIR"
    KIRPR_STAGE_DIR="$(mktemp -d)"
    trap 'rm -rf "$KIRPR_STAGE_DIR"' EXIT
    stage_bundle "$REPO_DIR"
    prepare_user_config
    begin_install_transaction
    trap cleanup_install EXIT
    install_staged_bundle || return $?
    write_manifest || return $?
}

main "$@"
