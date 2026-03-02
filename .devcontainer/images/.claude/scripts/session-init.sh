#!/bin/bash
# ============================================================================
# session-init.sh - Cache project metadata as env vars at session start
# Hook: SessionStart (all events)
# Exit 0 = always (fail-open)
#
# Purpose: Pre-cache git metadata into CLAUDE_ENV_FILE so every hook
#          doesn't need to call git rev-parse repeatedly.
#
# Env vars cached:
#   GH_ORG, GH_REPO, GH_BRANCH, GH_DEFAULT_BRANCH
# ============================================================================

set +e  # Fail-open: never block

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/workspace}"

# Read stdin for session metadata
INPUT="$(cat 2>/dev/null || true)"
SOURCE=""
MODEL=""
if [ -n "$INPUT" ] && command -v jq &>/dev/null; then
    SOURCE=$(printf '%s' "$INPUT" | jq -r '.source // ""' 2>/dev/null || echo "")
    MODEL=$(printf '%s' "$INPUT" | jq -r '.model // ""' 2>/dev/null || echo "")
fi

# CLAUDE_ENV_FILE is set by Claude Code runtime; if not, we cannot write env vars
ENV_FILE="${CLAUDE_ENV_FILE:-}"
if [ -z "$ENV_FILE" ]; then
    exit 0
fi

# Cache git metadata
GH_BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
GH_DEFAULT_BRANCH=$(git -C "$PROJECT_DIR" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")

# Extract org/repo from git remote
REMOTE_URL=$(git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || echo "")
GH_ORG=""
GH_REPO=""
if [ -n "$REMOTE_URL" ]; then
    # Handle both HTTPS and SSH formats
    SLUG=$(echo "$REMOTE_URL" | sed -E 's|.*[:/]([^/]+)/([^/.]+)(\.git)?$|\1/\2|')
    GH_ORG=$(echo "$SLUG" | cut -d'/' -f1)
    GH_REPO=$(echo "$SLUG" | cut -d'/' -f2)
fi

# Write to CLAUDE_ENV_FILE (key=value format, one per line)
{
    echo "GH_ORG=$GH_ORG"
    echo "GH_REPO=$GH_REPO"
    echo "GH_BRANCH=$GH_BRANCH"
    echo "GH_DEFAULT_BRANCH=$GH_DEFAULT_BRANCH"
} >> "$ENV_FILE" 2>/dev/null || true

# Log session start with source and model
BRANCH_SAFE=$(printf '%s' "$GH_BRANCH" | tr '/ ' '__')
LOG_DIR="$PROJECT_DIR/.claude/logs/$BRANCH_SAFE"
mkdir -p "$LOG_DIR" 2>/dev/null || true

if command -v jq &>/dev/null; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    jq -n -c \
        --arg ts "$TIMESTAMP" \
        --arg src "$SOURCE" \
        --arg mdl "$MODEL" \
        --arg branch "$GH_BRANCH" \
        '{timestamp:$ts,source:$src,model:$mdl,branch:$branch,event:"SessionStart"}' \
        >> "$LOG_DIR/session.jsonl" 2>/dev/null || true
fi

exit 0
