#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"

echo "Uninstalling kirpr..."

# --- Handle tracker.md ---
if [ -f "$KIRPR_DIR/config/tracker.md" ]; then
    echo ""
    echo "tracker.md contains your tracker configuration."
    printf "Delete it too? [y/N]: "
    read -r delete_tracker
    if [ "$delete_tracker" != "y" ] && [ "$delete_tracker" != "Y" ]; then
        TRACKER_SAVE="$(mktemp)"
        cp "$KIRPR_DIR/config/tracker.md" "$TRACKER_SAVE"
        echo "  Saved tracker.md to $TRACKER_SAVE"
    fi
fi

# --- Remove directories ---
if [ -d "$COMMANDS_DIR" ]; then
    rm -rf "$COMMANDS_DIR"
    echo "  Removed $COMMANDS_DIR"
fi
if [ -d "$KIRPR_DIR" ]; then
    rm -rf "$KIRPR_DIR"
    echo "  Removed $KIRPR_DIR"
fi

# --- Clean up empty parent directories ---
rmdir "$CLAUDE_DIR/commands" 2>/dev/null && echo "  Removed empty: $CLAUDE_DIR/commands" || true

echo ""
echo "Done! kirpr has been uninstalled."

if [ -n "${TRACKER_SAVE:-}" ] && [ -f "${TRACKER_SAVE:-}" ]; then
    echo ""
    echo "Your tracker.md was saved to: $TRACKER_SAVE"
    echo "To restore it after reinstalling: cp $TRACKER_SAVE ~/.claude/kirpr/config/tracker.md"
fi
