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
"$KIRPR_CURL_BIN" -fsSL "$ARCHIVE_URL" -o "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$TEMP_DIR"

if [ ! -f "$EXTRACTED_DIR/install.sh" ] || [ ! -f "$EXTRACTED_DIR/installer/lib.sh" ]; then
    printf '%s\n' 'Downloaded archive does not contain a complete kirpr installer.' >&2
    exit 1
fi

"$EXTRACTED_DIR/install.sh" "$@"
