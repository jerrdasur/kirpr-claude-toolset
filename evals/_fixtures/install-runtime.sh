#!/usr/bin/env bash
# Installs the kirpr runtime into the eval run's temporary HOME and prepares
# the tracker fixtures in the current directory as .eval-tracker/.
# git is checked by the fixtures that create repositories.
set -euo pipefail
FIX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$FIX/../.." && pwd)"
input="${TMPDIR:-/tmp}/kirpr-eval-input.$$"
printf '1\nhttps://youtrack.example.invalid\n' > "$input"
KIRPR_INSTALL_ROOT="$HOME" KIRPR_INPUT_FILE="$input" "$REPO/install.sh" --target claude >/dev/null
rm -f "$input"
# The plugin under test provides skills and commands; the installer's copies in
# ~/.claude would duplicate them, so only the runtime and tracker config stay.
for skill_dir in "$REPO"/skills/*/; do
    rm -rf "$HOME/.claude/skills/$(basename "$skill_dir")"
done
rm -rf "$HOME/.claude/commands/kirpr"
rm -rf ./.eval-tracker
cp -R "$FIX/tracker" ./.eval-tracker
