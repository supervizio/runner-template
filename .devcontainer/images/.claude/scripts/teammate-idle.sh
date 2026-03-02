#!/bin/bash
# ============================================================================
# teammate-idle.sh - Handle teammate idle event
# Hook: TeammateIdle (no matcher, always fires)
# Exit 0 = allow idle, Exit 2 = continue working
#
# Purpose: Notification + logging when a teammate goes idle.
# ============================================================================

set +e

printf '\a'  # Terminal bell

INPUT="$(cat 2>/dev/null || true)"
TEAMMATE=""
SESSION_ID="unknown"
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    TEAMMATE=$(printf '%s' "$INPUT" | jq -r '.teammate_name // ""' 2>/dev/null || echo "")
    SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null || echo "unknown")
fi

if [ -n "$TEAMMATE" ]; then
    echo "Teammate idle: $TEAMMATE" >&2
fi

# JSONL logging for consistency with other hooks
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/workspace}"
LOG_DIR="$PROJECT_DIR/.claude/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || true

if command -v jq &>/dev/null; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    jq -n -c \
        --arg ts "$TIMESTAMP" \
        --arg sid "$SESSION_ID" \
        --arg teammate "$TEAMMATE" \
        '{timestamp:$ts,session_id:$sid,teammate_name:$teammate,event:"TeammateIdle"}' \
        >> "$LOG_DIR/teammates.jsonl" 2>/dev/null || true
fi

exit 0
