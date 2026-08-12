#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands/kirpr"
KIRPR_DIR="$CLAUDE_DIR/kirpr"
SKILLS_DIR="$CLAUDE_DIR/skills"
PANEL_DIR="$SKILLS_DIR/expert-panel"
GRILL_DIR="$SKILLS_DIR/grill-me"

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

# --- Handle custom-experts.md ---
if [ -f "$PANEL_DIR/custom-experts.md" ]; then
    echo ""
    echo "custom-experts.md contains your custom expert panel."
    printf "Delete it too? [y/N]: "
    read -r delete_custom
    if [ "$delete_custom" != "y" ] && [ "$delete_custom" != "Y" ]; then
        CUSTOM_SAVE="$(mktemp)"
        cp "$PANEL_DIR/custom-experts.md" "$CUSTOM_SAVE"
        echo "  Saved custom-experts.md to $CUSTOM_SAVE"
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
if [ -d "$PANEL_DIR" ]; then
    rm -rf "$PANEL_DIR"
    echo "  Removed $PANEL_DIR"
fi
if [ -d "$GRILL_DIR" ]; then
    rm -rf "$GRILL_DIR"
    echo "  Removed $GRILL_DIR"
fi

# --- Clean up empty parent directories ---
rmdir "$CLAUDE_DIR/commands" 2>/dev/null && echo "  Removed empty: $CLAUDE_DIR/commands" || true
rmdir "$SKILLS_DIR" 2>/dev/null && echo "  Removed empty: $SKILLS_DIR" || true

echo ""
echo "Done! kirpr has been uninstalled."

if [ -n "${TRACKER_SAVE:-}" ] && [ -f "${TRACKER_SAVE:-}" ]; then
    echo ""
    echo "Your tracker.md was saved to: $TRACKER_SAVE"
    echo "To restore it after reinstalling: cp $TRACKER_SAVE ~/.claude/kirpr/config/tracker.md"
fi

if [ -n "${CUSTOM_SAVE:-}" ] && [ -f "${CUSTOM_SAVE:-}" ]; then
    echo ""
    echo "Your custom-experts.md was saved to: $CUSTOM_SAVE"
    echo "To restore it after reinstalling: cp $CUSTOM_SAVE ~/.claude/skills/expert-panel/custom-experts.md"
fi
