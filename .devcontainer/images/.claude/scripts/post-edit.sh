#!/bin/bash
# Combined post-edit hook: format + lint + typecheck
# Usage: post-edit.sh <file_path>
# Note: format.sh handles imports (goimports, ruff, rustfmt, etc.)
# Outputs additionalContext with lint/format issues for Claude self-correction.

set +e  # Fail-open: hooks should never block unexpectedly

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read file_path from stdin JSON (preferred) or fallback to argument
INPUT="$(cat 2>/dev/null || true)"
FILE=""
if [ -n "$INPUT" ] && command -v jq &>/dev/null; then
    FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)
fi
FILE="${FILE:-${1:-}}"

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    exit 0
fi

# Skip format/lint for documentation and config files
if [[ "$FILE" == *".claude/contexts/"* ]] || \
   [[ "$FILE" == *".claude/plans/"* ]] || \
   [[ "$FILE" == *".claude/sessions/"* ]] || \
   [[ "$FILE" == */plans/* ]] || \
   [[ "$FILE" == *.md ]] || \
   [[ "$FILE" == /tmp/* ]] || \
   [[ "$FILE" == /home/vscode/.claude/* ]]; then
    exit 0
fi

# === Format/Lint/Types pipeline (capture issues) ===
ISSUES=""

# 1. Format (includes import sorting via goimports, ruff, rustfmt, etc.)
FMT_OUT=$("$SCRIPT_DIR/format.sh" "$FILE" 2>&1) || true
if [ -n "$FMT_OUT" ]; then
    ISSUES="${ISSUES}Format: ${FMT_OUT:0:300}\n"
fi

# 2. Lint (with auto-fix)
LINT_OUT=$("$SCRIPT_DIR/lint.sh" "$FILE" 2>&1)
LINT_RC=$?
if [ $LINT_RC -ne 0 ] && [ -n "$LINT_OUT" ]; then
    ISSUES="${ISSUES}Lint: ${LINT_OUT:0:300}\n"
fi

# 3. Type check (academic rigor)
TYPE_OUT=$("$SCRIPT_DIR/typecheck.sh" "$FILE" 2>&1)
TYPE_RC=$?
if [ $TYPE_RC -ne 0 ] && [ -n "$TYPE_OUT" ]; then
    ISSUES="${ISSUES}Typecheck: ${TYPE_OUT:0:300}\n"
fi

# Output additionalContext if issues found
if [ -n "$ISSUES" ] && command -v jq &>/dev/null; then
    CONTEXT="Post-edit issues in $FILE:\n$ISSUES\nPlease fix these issues in your next edit."
    jq -n -c \
        --arg ctx "$CONTEXT" \
        '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":$ctx}}' \
        2>/dev/null || true
fi

exit 0
