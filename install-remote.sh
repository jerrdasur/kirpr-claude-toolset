#!/usr/bin/env bash
set -eu

ARCHIVE_URL="https://github.com/jerrdasur/kirpr-claude-toolset/archive/refs/heads/main.tar.gz"
KIRPR_CURL_BIN="${KIRPR_CURL_BIN:-curl}"
TEMP_DIR="$(mktemp -d)"
ARCHIVE="$TEMP_DIR/kirpr.tar.gz"
EXTRACTED_DIR="$TEMP_DIR/kirpr-claude-toolset-main"

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT HUP INT TERM

printf '%s\n' 'Downloading kirpr installer archive...'
if ! "$KIRPR_CURL_BIN" -fsSL "$ARCHIVE_URL" -o "$ARCHIVE"; then
    printf '%s\n' 'Failed to download kirpr installer archive.' >&2
    exit 1
fi
if ! tar -xzf "$ARCHIVE" -C "$TEMP_DIR"; then
    printf '%s\n' 'Downloaded archive could not be extracted.' >&2
    exit 1
fi

if [ ! -f "$EXTRACTED_DIR/install.sh" ] || \
   [ ! -f "$EXTRACTED_DIR/installer/lib.sh" ] || \
   [ ! -d "$EXTRACTED_DIR/skills" ] || \
   [ ! -d "$EXTRACTED_DIR/commands/kirpr" ] || \
   [ ! -d "$EXTRACTED_DIR/kirpr/config" ] || \
   [ ! -d "$EXTRACTED_DIR/kirpr/prompts" ] || \
   [ ! -d "$EXTRACTED_DIR/kirpr/scripts" ]; then
    printf '%s\n' 'Downloaded archive does not contain a complete kirpr installer.' >&2
    exit 1
fi

"$EXTRACTED_DIR/install.sh" "$@"
