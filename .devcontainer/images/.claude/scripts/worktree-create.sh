#!/bin/bash
# ============================================================================
# worktree-create.sh - Handle worktree creation
# Hook: WorktreeCreate (no matcher, always fires)
# MUST print worktree path to stdout (Claude Code spec requirement)
# Non-zero exit = creation failure
#
# Purpose: Custom worktree setup with logging.
# ============================================================================

set +e

INPUT="$(cat 2>/dev/null || true)"
WORKTREE_NAME=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    WORKTREE_NAME=$(printf '%s' "$INPUT" | jq -r '.name // ""' 2>/dev/null || echo "")
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/workspace}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create worktree in a standard location
WORKTREE_BASE="/tmp/claude-worktrees"
mkdir -p "$WORKTREE_BASE" 2>/dev/null || true

if [ -n "$WORKTREE_NAME" ]; then
    WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_NAME"

    # Create the worktree
    git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" 2>/dev/null
    RC=$?

    if [ $RC -eq 0 ]; then
        # MUST print path to stdout (Claude Code reads this)
        echo "$WORKTREE_PATH"

        # Log the creation
        LOG_DIR="$PROJECT_DIR/.claude/logs"
        mkdir -p "$LOG_DIR" 2>/dev/null || true
        if command -v jq &>/dev/null; then
            jq -n -c \
                --arg ts "$TIMESTAMP" \
                --arg name "$WORKTREE_NAME" \
                --arg path "$WORKTREE_PATH" \
                '{timestamp:$ts,name:$name,path:$path,event:"WorktreeCreate"}' \
                >> "$LOG_DIR/worktrees.jsonl" 2>/dev/null || true
        fi
        exit 0
    else
        echo "Failed to create worktree: $WORKTREE_NAME" >&2
        exit 1
    fi
fi

exit 0
