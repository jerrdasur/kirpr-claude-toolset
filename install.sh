#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=installer/lib.sh
. "$REPO_DIR/installer/lib.sh"

main() {
    parse_args "$@"
    [ -n "$KIRPR_TARGET" ] || choose_target
    resolve_paths
    validate_bundle "$REPO_DIR"
    KIRPR_STAGE_DIR="$(mktemp -d)"
    trap 'rm -rf "$KIRPR_STAGE_DIR"' EXIT
    stage_bundle "$REPO_DIR"
    prepare_user_config
    install_staged_bundle
    write_manifest
}

main "$@"
