#!/usr/bin/env bash
# Fails fast when git inside the eval sandbox would be the macOS xcrun shim,
# which cannot run there (it writes its cache to a temp dir outside the sandbox).
set -euo pipefail
git_path="$(command -v git || true)"
if [ -z "$git_path" ]; then
    echo "require-git: git не найден в PATH" >&2
    exit 1
fi
if [ "$(uname -s)" = "Darwin" ]; then
    if [ "$git_path" = "/usr/bin/git" ] || git --version 2>/dev/null | grep -q "Apple"; then
        echo "require-git: нужен git из Homebrew первым в PATH (сейчас: $git_path)" >&2
        exit 1
    fi
fi
