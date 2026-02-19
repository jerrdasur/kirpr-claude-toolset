#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"

echo "Uninstalling kirpr (removing symlinks pointing to $REPO_DIR)"

removed=0

remove_symlinks() {
    local dir="$1" pattern="$2" repo_subpath="$3"
    [ -d "$dir" ] || return 0
    for f in "$dir"/$pattern; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        local name
        name="$(basename "$f")"
        if [ -L "$f" ] && [ "$(readlink "$f")" = "$REPO_DIR/$repo_subpath/$name" ]; then
            rm "$f"
            echo "  Removed: $f"
            removed=$((removed + 1))
        fi
    done
}

remove_symlinks "$COMMANDS_DIR" "*.md" "commands/kirpr"
remove_symlinks "$KIRPR_DIR/config" "*.md" "kirpr/config"
remove_symlinks "$KIRPR_DIR/scripts" "*.py" "kirpr/scripts"

echo ""
echo "Removed $removed symlinks."

if [ -f "$KIRPR_DIR/config/tracker.md" ]; then
    echo "Note: tracker.md preserved (user config). Delete manually if needed:"
    echo "  rm $KIRPR_DIR/config/tracker.md"
fi

# Clean up empty directories
rmdir "$COMMANDS_DIR" 2>/dev/null && echo "Removed empty: $COMMANDS_DIR" || true
rmdir "$KIRPR_DIR/scripts" 2>/dev/null && echo "Removed empty: $KIRPR_DIR/scripts" || true
rmdir "$KIRPR_DIR/config" 2>/dev/null || true
rmdir "$KIRPR_DIR" 2>/dev/null && echo "Removed empty: $KIRPR_DIR" || true
