#!/bin/bash
# ============================================================================
# common.sh - Shared utilities for hook scripts
# ============================================================================
# Sourced by format.sh, lint.sh, typecheck.sh, test.sh to avoid duplication.
# ============================================================================

# Find project root by walking up from a given directory
# Checks for common build/config files that indicate a project root.
# Usage: PROJECT_ROOT=$(find_project_root "$DIR")
find_project_root() {
    local current="$1"
    local fallback="${2:-$current}"
    while [ "$current" != "/" ]; do
        if [ -f "$current/Makefile" ] || \
           [ -f "$current/package.json" ] || \
           [ -f "$current/pyproject.toml" ] || \
           [ -f "$current/go.mod" ] || \
           [ -f "$current/Cargo.toml" ] || \
           [ -f "$current/pom.xml" ] || \
           [ -f "$current/build.gradle" ] || \
           [ -f "$current/build.gradle.kts" ] || \
           [ -f "$current/build.sbt" ] || \
           [ -f "$current/mix.exs" ] || \
           [ -f "$current/pubspec.yaml" ] || \
           [ -f "$current/CMakeLists.txt" ] || \
           [ -f "$current/Package.swift" ] || \
           [ -f "$current/composer.json" ] || \
           [ -f "$current/Gemfile" ] || \
           [ -f "$current/fpm.toml" ] || \
           [ -f "$current/alire.toml" ]; then
            echo "$current"
            return
        fi
        current=$(dirname "$current")
    done
    echo "$fallback"
}

# Check if Makefile has a specific target
# Usage: has_makefile_target "lint" "$PROJECT_ROOT"
has_makefile_target() {
    local target="$1"
    local root="${2:-.}"
    if [ -f "$root/Makefile" ]; then
        grep -qE "^${target}:" "$root/Makefile" 2>/dev/null
        return $?
    fi
    return 1
}

# Check if Makefile supports FILE= parameter
# Usage: makefile_supports_file "$PROJECT_ROOT"
makefile_supports_file() {
    local root="${1:-.}"
    grep -qE "FILE\s*[:?]?=" "$root/Makefile" 2>/dev/null
}

# Run a Makefile target with optional FILE parameter
# Usage: run_makefile_target "fmt" "$FILE" "$PROJECT_ROOT"
run_makefile_target() {
    local target="$1"
    local file="$2"
    local root="${3:-.}"
    cd "$root" || exit 0
    if makefile_supports_file "$root"; then
        make "$target" FILE="$file" 2>/dev/null || true
    else
        make "$target" 2>/dev/null || true
    fi
}
