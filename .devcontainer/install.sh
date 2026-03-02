#!/bin/bash
# ============================================================================
# Universal Claude Code Installation Script
# ============================================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/kodflow/devcontainer-template/main/.devcontainer/install.sh | bash
#
# Or with custom target:
#   DC_TARGET=/path/to/project curl -fsSL ... | bash
#
# Or minimal installation (no docs):
#   curl -fsSL ... | bash -s -- --minimal
# ============================================================================

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
REPO="kodflow/devcontainer-template"
BRANCH="main"
BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
API="https://api.github.com/repos/${REPO}/contents"

# Parse arguments
INSTALL_MINIMAL=false
for arg in "$@"; do
    case "$arg" in
        --minimal) INSTALL_MINIMAL=true ;;
        --help)
            cat <<EOF
Universal Claude Code Installation Script

Usage:
  curl -fsSL URL | bash                    # Full installation
  curl -fsSL URL | bash -s -- --minimal    # Skip documentation (155+ files)
  DC_TARGET=/path curl -fsSL URL | bash    # Custom target directory

Options:
  --minimal    Skip documentation installation (saves ~2.4MB, 155 files)
  --help       Show this help message

Installation Location:
  Always:          \$HOME/.claude/ (both host and container)

What Gets Installed:
  - Claude CLI (if not already installed)
  - 35 specialist agents
  - 11 slash commands (/git, /review, /plan, etc.)
  - 11 hook scripts (security, lint, format, etc.)
  - 155+ design patterns (unless --minimal)
  - Configuration files (settings.json, mcp.json, etc.)
  - super-claude function (in ~/.bashrc and ~/.zshrc)

1Password Integration (REQUIRED for MCP tokens):
  OP_SERVICE_ACCOUNT_TOKEN  1Password Service Account Token
                            (vault auto-detected from service account)

  Items to create in 1Password:
    mcp-github    → GitHub Personal Access Token (field: credential)
    mcp-codacy    → Codacy Account Token (field: credential)
    mcp-gitlab    → GitLab Personal Access Token (field: credential)

Total: 239 files (~3.2MB) or 84 files (~0.8MB) with --minimal
EOF
            exit 0
            ;;
    esac
done

# ============================================================================
# Environment Detection
# ============================================================================
detect_environment() {
    echo "═══════════════════════════════════════════════"
    echo "  Universal Claude Code Installation"
    echo "═══════════════════════════════════════════════"
    echo ""

    # OS Detection
    case "$(uname -s)" in
        Linux*)  OS="linux" ;;
        Darwin*) OS="darwin" ;;
        MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
        *)       OS="unknown" ;;
    esac

    # Architecture Detection
    case "$(uname -m)" in
        x86_64|amd64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        *)            ARCH="unknown" ;;
    esac

    # Container Detection
    IS_CONTAINER=false
    if [ -f /.dockerenv ]; then
        IS_CONTAINER=true
    fi

    # Home Directory Detection
    HOME_DIR="${HOME:-/home/vscode}"

    # Target Directory - ALWAYS in $HOME/.claude/ (same behavior for host and container)
    # This ensures no Claude files pollute the project workspace
    TARGET_DIR="${DC_TARGET:-$HOME_DIR/.claude}"

    echo "→ Environment Detection:"
    echo "  OS:         $OS"
    echo "  Arch:       $ARCH"
    echo "  Container:  $IS_CONTAINER"
    echo "  Home:       $HOME_DIR"
    echo "  Target:     $TARGET_DIR"
    echo ""
}

# ============================================================================
# Safe Download with Validation
# ============================================================================
# GitHub API call with optional authentication
# Uses GITHUB_TOKEN if available (5000 req/h vs 60 req/h)
github_api_call() {
    local url="$1"
    local auth_header=""

    # Use token if available for higher rate limit
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        auth_header="-H \"Authorization: token ${GITHUB_TOKEN}\""
    fi

    eval curl -sL $auth_header "$url" 2>/dev/null
}

safe_download() {
    local url="$1"
    local output="$2"
    local temp_file
    temp_file=$(mktemp)

    # Download with HTTP code
    local http_code
    http_code=$(curl -sL -w "%{http_code}" -o "$temp_file" "$url" 2>/dev/null || echo "000")

    # Validate download
    if [ "$http_code" != "200" ]; then
        rm -f "$temp_file"
        return 1
    fi

    # Check for HTML error pages (404 disguised as 200)
    if head -1 "$temp_file" 2>/dev/null | grep -qE "^404|^<!DOCTYPE|^<html"; then
        rm -f "$temp_file"
        return 1
    fi

    # Check not empty
    if [ ! -s "$temp_file" ]; then
        rm -f "$temp_file"
        return 1
    fi

    # All good, move to destination
    mkdir -p "$(dirname "$output")"
    mv "$temp_file" "$output"
    return 0
}

# ============================================================================
# Install Claude CLI
# ============================================================================
install_claude_cli() {
    if command -v claude &>/dev/null; then
        echo "→ Claude CLI:"
        echo "  ✓ Already installed ($(command -v claude))"
        return 0
    fi

    echo "→ Installing Claude CLI..."

    # Method 1: npm (if available)
    if command -v npm &>/dev/null; then
        if npm install -g @anthropic-ai/claude-code 2>/dev/null; then
            echo "  ✓ Installed via npm"
            return 0
        fi
    fi

    # Method 2: Official installer
    if curl -fsSL https://claude.ai/install.sh | sh 2>/dev/null; then
        echo "  ✓ Installed via official script"
        return 0
    fi

    echo "  ⚠ Installation failed (may already be in PATH)"
    return 0  # Non-blocking
}

# ============================================================================
# Download Assets Archive (single file, ~1MB)
# ============================================================================
# Priority method: download pre-built tar.gz instead of 20+ API calls
download_assets_archive() {
    local target_dir="$1"
    local release_url="https://github.com/${REPO}/releases/latest/download/claude-assets.tar.gz"
    local temp_archive
    temp_archive=$(mktemp)

    echo "→ Trying assets archive (faster)..."

    # Try GitHub Releases first (faster CDN, versioned)
    local http_code
    http_code=$(curl -sL -w "%{http_code}" -o "$temp_archive" "$release_url" 2>/dev/null || echo "000")

    if [ "$http_code" != "200" ]; then
        echo "  ⚠ Release archive not available, will use API discovery"
        rm -f "$temp_archive"
        return 1
    fi

    # Validate archive (tar -tzf works on all POSIX systems, unlike `file`)
    if ! tar -tzf "$temp_archive" >/dev/null 2>&1; then
        echo "  ⚠ Invalid archive format"
        rm -f "$temp_archive"
        return 1
    fi

    # Extract to target directory
    mkdir -p "$target_dir"
    if tar -xzf "$temp_archive" -C "$target_dir" 2>/dev/null; then
        local file_count
        file_count=$(tar -tzf "$temp_archive" 2>/dev/null | wc -l)
        echo "  ✓ Extracted $file_count files from archive"
        rm -f "$temp_archive"

        # Make scripts executable
        chmod -R 755 "$target_dir/scripts/" 2>/dev/null || true
        chmod -R 755 "$target_dir/agents/" 2>/dev/null || true

        return 0
    else
        echo "  ⚠ Failed to extract archive"
        rm -f "$temp_archive"
        return 1
    fi
}

# ============================================================================
# Download Agents (35 files)
# ============================================================================
download_agents() {
    local target_dir="$1"
    mkdir -p "$target_dir/agents"

    echo "→ Downloading agents..."

    # Discover via GitHub API (uses GITHUB_TOKEN if available for higher rate limit)
    local agents
    agents=$(github_api_call "$API/.devcontainer/images/.claude/agents" | jq -r '.[].name' 2>/dev/null | grep '\.md$' || echo "")

    if [ -z "$agents" ]; then
        echo "  ⚠ Could not discover agents via API, using fallback"
        # Fallback: known agents list (truncated for brevity)
        agents="developer-orchestrator.md developer-specialist-go.md developer-specialist-python.md"
    fi

    local count=0
    local failed=0

    for agent in $agents; do
        if safe_download "$BASE/.devcontainer/images/.claude/agents/$agent" "$target_dir/agents/$agent"; then
            count=$((count + 1))
        else
            failed=$((failed + 1))
        fi
    done

    echo "  ✓ Downloaded $count agents"
    [ $failed -gt 0 ] && echo "  ⚠ Failed: $failed agents" || true
}

# ============================================================================
# Download Commands (11 files)
# ============================================================================
download_commands() {
    local target_dir="$1"
    mkdir -p "$target_dir/commands"

    echo "→ Downloading commands..."

    # Discover via GitHub API
    local commands
    commands=$(github_api_call "$API/.devcontainer/images/.claude/commands" | jq -r '.[].name' 2>/dev/null | grep '\.md$' || echo "")

    if [ -z "$commands" ]; then
        echo "  ⚠ Could not discover commands via API, using fallback"
        commands="git.md review.md plan.md do.md search.md update.md"
    fi

    local count=0
    local failed=0

    for cmd in $commands; do
        if safe_download "$BASE/.devcontainer/images/.claude/commands/$cmd" "$target_dir/commands/$cmd"; then
            count=$((count + 1))
        else
            failed=$((failed + 1))
        fi
    done

    echo "  ✓ Downloaded $count commands"
    [ $failed -gt 0 ] && echo "  ⚠ Failed: $failed commands" || true
}

# ============================================================================
# Download Scripts (11 files)
# ============================================================================
download_scripts() {
    local target_dir="$1"
    mkdir -p "$target_dir/scripts"

    echo "→ Downloading scripts..."

    # Discover via GitHub API
    local scripts
    scripts=$(github_api_call "$API/.devcontainer/images/.claude/scripts" | jq -r '.[].name' 2>/dev/null | grep '\.sh$' || echo "")

    if [ -z "$scripts" ]; then
        echo "  ⚠ Could not discover scripts via API, using fallback"
        scripts="commit-validate.sh format.sh lint.sh log.sh post-compact.sh post-edit.sh pre-commit-checks.sh pre-validate.sh security.sh test.sh typecheck.sh"
    fi

    local count=0
    local failed=0

    for script in $scripts; do
        if safe_download "$BASE/.devcontainer/images/.claude/scripts/$script" "$target_dir/scripts/$script"; then
            chmod +x "$target_dir/scripts/$script"
            count=$((count + 1))
        else
            failed=$((failed + 1))
        fi
    done

    echo "  ✓ Downloaded $count scripts"
    [ $failed -gt 0 ] && echo "  ⚠ Failed: $failed scripts" || true
}

# ============================================================================
# Download Documentation (155+ files) - OPTIONAL
# ============================================================================
download_docs() {
    local target_dir="$1"

    if [ "$INSTALL_MINIMAL" = true ]; then
        echo "→ Skipping documentation (--minimal mode)"
        return 0
    fi

    mkdir -p "$target_dir/docs"

    echo "→ Downloading documentation (this may take a moment)..."

    # Download root docs files
    local root_docs="CLAUDE.md README.md TEMPLATE-PATTERN.md TEMPLATE-README.md .markdownlint.json"
    local root_count=0

    for file in $root_docs; do
        if safe_download "$BASE/.devcontainer/images/.claude/docs/$file" "$target_dir/docs/$file"; then
            root_count=$((root_count + 1))
        fi
    done

    # Download category directories (20 categories)
    local categories
    categories=$(github_api_call "$API/.devcontainer/images/.claude/docs" | jq -r '.[] | select(.type == "dir") | .name' 2>/dev/null || echo "")

    if [ -z "$categories" ]; then
        echo "  ⚠ Could not discover doc categories, skipping patterns"
        return 0
    fi

    local pattern_count=0
    local failed=0

    for category in $categories; do
        mkdir -p "$target_dir/docs/$category"

        # Download all .md files in category
        local category_files
        category_files=$(github_api_call "$API/.devcontainer/images/.claude/docs/$category" | jq -r '.[].name' 2>/dev/null | grep '\.md$' || echo "")

        for file in $category_files; do
            if safe_download "$BASE/.devcontainer/images/.claude/docs/$category/$file" "$target_dir/docs/$category/$file"; then
                pattern_count=$((pattern_count + 1))
            else
                failed=$((failed + 1))
            fi
        done
    done

    echo "  ✓ Downloaded $root_count root files"
    echo "  ✓ Downloaded $pattern_count pattern files"
    [ $failed -gt 0 ] && echo "  ⚠ Failed: $failed files" || true
}

# ============================================================================
# Download Configuration Files
# ============================================================================
download_configs() {
    local target_dir="$1"

    echo "→ Downloading configurations..."

    local count=0

    if safe_download "$BASE/.devcontainer/images/.claude/settings.json" "$target_dir/settings.json"; then
        count=$((count + 1))
    fi

    if safe_download "$BASE/.devcontainer/images/.claude/.claude.json" "$target_dir/.claude.json"; then
        count=$((count + 1))
    fi

    # Download CLAUDE.md if not in container (host installation)
    if [ "$IS_CONTAINER" = false ] && [ ! -f "$HOME_DIR/CLAUDE.md" ]; then
        if safe_download "$BASE/CLAUDE.md" "$HOME_DIR/CLAUDE.md"; then
            echo "  ✓ Downloaded CLAUDE.md to $HOME_DIR/"
        fi
    fi

    echo "  ✓ Downloaded $count config files"
}

# ============================================================================
# Download Additional Tools (grepai, status-line)
# ============================================================================
download_tools() {
    echo "→ Installing additional tools..."

    local tool_count=0

    # Install grepai (semantic code search)
    if ! command -v grepai &>/dev/null; then
        mkdir -p "$HOME_DIR/.local/bin"

        local grepai_ext=""
        [ "$OS" = "windows" ] && grepai_ext=".exe"

        local grepai_latest
        grepai_latest=$(curl -fsSL "https://api.github.com/repos/yoanbernabeu/grepai/releases/latest" 2>/dev/null | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4) || true
        if [[ -z "$grepai_latest" ]]; then
            echo "  ⚠ Failed to resolve latest grepai version (optional, skipping)"
            return 0
        fi
        local grepai_url="https://github.com/yoanbernabeu/grepai/releases/download/${grepai_latest}/grepai_${grepai_latest#v}_${OS}_${ARCH}.tar.gz"
        local grepai_tmp grepai_extract
        grepai_tmp=$(mktemp)
        grepai_extract=$(mktemp -d)

        if curl -fsL --retry 3 --proto '=https' --tlsv1.2 "$grepai_url" -o "$grepai_tmp" 2>/dev/null && \
           tar -xzf "$grepai_tmp" -C "$grepai_extract" grepai 2>/dev/null; then
            install -m 0755 "$grepai_extract/grepai" "$HOME_DIR/.local/bin/grepai${grepai_ext}"
            tool_count=$((tool_count + 1))
            echo "  ✓ grepai ${grepai_latest} installed"
        else
            echo "  ⚠ grepai download failed (optional)"
        fi
        rm -f "$grepai_tmp"
        rm -rf "$grepai_extract"
    else
        echo "  ✓ grepai already installed"
    fi

    # Install status-line (git status display)
    if ! command -v status-line &>/dev/null; then
        mkdir -p "$HOME_DIR/.local/bin"

        local status_ext=""
        [ "$OS" = "windows" ] && status_ext=".exe"

        local status_url="https://github.com/kodflow/status-line/releases/latest/download/status-line-${OS}-${ARCH}${status_ext}"
        local status_tmp
        status_tmp=$(mktemp)

        if curl -fsL --retry 3 --proto '=https' --tlsv1.2 "$status_url" -o "$status_tmp" 2>/dev/null; then
            install -m 0755 "$status_tmp" "$HOME_DIR/.local/bin/status-line${status_ext}"
            tool_count=$((tool_count + 1))
            echo "  ✓ status-line installed"
        else
            echo "  ⚠ status-line download failed (optional)"
        fi
        rm -f "$status_tmp"
    else
        echo "  ✓ status-line already installed"
    fi

    # Add to PATH if needed
    if [[ ":$PATH:" != *":$HOME_DIR/.local/bin:"* ]]; then
        # shellcheck disable=SC2016
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_DIR/.bashrc" 2>/dev/null || true
        # shellcheck disable=SC2016
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_DIR/.zshrc" 2>/dev/null || true
        echo "  → Added ~/.local/bin to PATH (restart shell to apply)"
    fi
}

# ============================================================================
# Ensure sensitive files are in .gitignore
# ============================================================================
ensure_gitignore() {
    local gitignore="$HOME_DIR/.gitignore"

    # Use project .gitignore if we're in a git repo
    if [ -d ".git" ]; then
        gitignore=".gitignore"
    fi

    echo "→ Updating .gitignore..."

    # Create .gitignore if it doesn't exist
    if [ ! -f "$gitignore" ]; then
        touch "$gitignore"
        echo "  ✓ Created $gitignore"
    fi

    # Add .env if not present
    if ! grep -qE '^\.env$|^\*\*\/\.env$' "$gitignore" 2>/dev/null; then
        echo "" >> "$gitignore"
        echo "# Environment files (contain secrets)" >> "$gitignore"
        echo ".env" >> "$gitignore"
        echo "**/.env" >> "$gitignore"
        echo "  ✓ Added .env"
    else
        echo "  ✓ .env already ignored"
    fi

    # Add CLAUDE.md if not present
    if ! grep -qE '^CLAUDE\.md$|^\*\*\/CLAUDE\.md$' "$gitignore" 2>/dev/null; then
        echo "" >> "$gitignore"
        echo "# Claude Code configuration (local preferences)" >> "$gitignore"
        echo "CLAUDE.md" >> "$gitignore"
        echo "**/CLAUDE.md" >> "$gitignore"
        echo "  ✓ Added CLAUDE.md"
    else
        echo "  ✓ CLAUDE.md already ignored"
    fi

    # Add .claude/ directory if not present
    if ! grep -qE '^\.claude\/?$|^\*\*\/\.claude\/?$' "$gitignore" 2>/dev/null; then
        echo "" >> "$gitignore"
        echo "# Claude Code local directory (created per project)" >> "$gitignore"
        echo ".claude/" >> "$gitignore"
        echo "**/.claude/" >> "$gitignore"
        echo "  ✓ Added .claude/"
    else
        echo "  ✓ .claude/ already ignored"
    fi
}

# ============================================================================
# 1Password Integration
# ============================================================================

# Load .env file if exists (for OP_SERVICE_ACCOUNT_TOKEN)
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        echo "  → Loading $env_file"
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue
            # Remove quotes from value
            value="${value%\"}"
            value="${value#\"}"
            # Export only OP token
            case "$key" in
                OP_SERVICE_ACCOUNT_TOKEN)
                    export "$key=$value"
                    ;;
            esac
        done < "$env_file"
    fi
}

# List all vaults from service account
get_1password_vaults() {
    if command -v op &>/dev/null && [ -n "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]; then
        op vault list --format=json 2>/dev/null | jq -r '.[].name' 2>/dev/null || echo ""
    fi
}

# Get field from 1Password (searches all vaults)
get_1password_field() {
    local item="$1"
    local field="${2:-credential}"
    local value=""
    local vaults

    if ! command -v op &>/dev/null || [ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]; then
        echo ""
        return
    fi

    # Get all vaults
    vaults=$(get_1password_vaults)

    # Search item in each vault
    for vault in $vaults; do
        value=$(op item get "$item" --vault "$vault" --fields "$field" --reveal 2>/dev/null || echo "")
        if [ -n "$value" ]; then
            echo "$value"
            return
        fi
    done

    echo ""
}

# Fetch tokens from 1Password vault "halys"
fetch_1password_tokens() {
    echo "→ Checking 1Password for tokens..."

    # Try to load .env from common locations
    local env_locations=(
        "./.devcontainer/.env"
        "./.env"
        "$HOME_DIR/.env"
        "$HOME_DIR/.claude/.env"
    )

    for env_file in "${env_locations[@]}"; do
        if [ -f "$env_file" ]; then
            load_env_file "$env_file"
            break
        fi
    done

    # Check if 1Password CLI is available and configured
    if ! command -v op &>/dev/null; then
        echo "  ⚠ 1Password CLI (op) not installed"
        echo "    Install: https://developer.1password.com/docs/cli/get-started/"
        return 0
    fi

    if [ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]; then
        echo "  ⚠ OP_SERVICE_ACCOUNT_TOKEN not set"
        echo "    Set it in .env or export it"
        return 0
    fi

    echo "  ✓ 1Password CLI available"

    # List available vaults
    local vaults
    vaults=$(get_1password_vaults)

    if [ -z "$vaults" ]; then
        echo "  ⚠ No vaults accessible"
        return 0
    fi

    echo "  → Vaults: $(echo $vaults | tr '\n' ' ')"
    echo "  → Searching for tokens..."

    # Fetch tokens from 1Password (searches all vaults)
    local op_github op_codacy op_gitlab

    op_github=$(get_1password_field "mcp-github" "credential")
    op_codacy=$(get_1password_field "mcp-codacy" "credential")
    op_gitlab=$(get_1password_field "mcp-gitlab" "credential")

    # Use 1Password tokens if found
    [ -n "$op_github" ] && export GITHUB_TOKEN="$op_github" && echo "    ✓ mcp-github" || true
    [ -n "$op_codacy" ] && export CODACY_TOKEN="$op_codacy" && echo "    ✓ mcp-codacy" || true
    [ -n "$op_gitlab" ] && export GITLAB_TOKEN="$op_gitlab" && echo "    ✓ mcp-gitlab" || true

    # Report what wasn't found
    [ -z "$op_github" ] && echo "    ⚠ mcp-github not found" || true
    [ -z "$op_codacy" ] && echo "    ⚠ mcp-codacy not found" || true
    [ -z "$op_gitlab" ] && echo "    ⚠ mcp-gitlab not found" || true
}

# ============================================================================
# Generate MCP Configuration
# ============================================================================
generate_mcp_config() {
    local target_dir="$1"
    local mcp_output="$HOME_DIR/.claude/mcp.json"

    # First, try to fetch tokens from 1Password
    fetch_1password_tokens

    echo ""
    echo "→ Generating MCP configuration..."

    # Download template
    local mcp_tpl
    mcp_tpl=$(mktemp)

    if ! safe_download "$BASE/.devcontainer/images/mcp.json.tpl" "$mcp_tpl"; then
        echo "  ⚠ Could not download MCP template"
        rm -f "$mcp_tpl"
        return 0
    fi

    # Get tokens (set by 1Password only)
    local github_token="${GITHUB_TOKEN:-}"
    local codacy_token="${CODACY_TOKEN:-}"
    local gitlab_token="${GITLAB_TOKEN:-}"
    local gitlab_api="${GITLAB_API_URL:-https://gitlab.com/api/v4}"

    # Escape tokens for sed
    local escaped_github escaped_codacy escaped_gitlab escaped_gitlab_api
    escaped_github=$(printf '%s' "$github_token" | sed 's/[&/\]/\\&/g')
    escaped_codacy=$(printf '%s' "$codacy_token" | sed 's/[&/\]/\\&/g')
    escaped_gitlab=$(printf '%s' "$gitlab_token" | sed 's/[&/\]/\\&/g')
    escaped_gitlab_api=$(printf '%s' "$gitlab_api" | sed 's/[&/\]/\\&/g')

    # Generate mcp.json from template
    mkdir -p "$(dirname "$mcp_output")"

    if sed -e "s|{{GITHUB_TOKEN}}|${escaped_github}|g" \
           -e "s|{{CODACY_TOKEN}}|${escaped_codacy}|g" \
           -e "s|{{GITLAB_TOKEN}}|${escaped_gitlab}|g" \
           -e "s|{{GITLAB_API_URL:-https://gitlab.com/api/v4}}|${escaped_gitlab_api}|g" \
           "$mcp_tpl" > "$mcp_output"; then

        chmod 600 "$mcp_output"

        # Validate JSON
        if command -v jq &>/dev/null && jq empty "$mcp_output" 2>/dev/null; then
            echo "  ✓ mcp.json generated at $mcp_output"
        else
            echo "  ⚠ mcp.json created but could not validate (jq not available)"
        fi
    else
        echo "  ⚠ Failed to generate mcp.json"
    fi

    rm -f "$mcp_tpl"

    # Show final token status
    echo "  Token status:"
    [ -n "$github_token" ] && echo "    GITHUB_TOKEN: ✓ configured" || echo "    GITHUB_TOKEN: ✗ not set"
    [ -n "$codacy_token" ] && echo "    CODACY_TOKEN: ✓ configured" || echo "    CODACY_TOKEN: ✗ not set"
    [ -n "$gitlab_token" ] && echo "    GITLAB_TOKEN: ✓ configured" || echo "    GITLAB_TOKEN: ✗ not set"
}

# ============================================================================
# Install super-claude Function
# ============================================================================
install_super_claude() {
    echo "→ Installing super-claude function..."

    local shell_functions="$HOME_DIR/.shell-functions.sh"

    # Create ~/.shell-functions.sh with super-claude (and any future functions)
    # This file is sourced by both .bashrc and .zshrc
    cat > "$shell_functions" << 'FUNCSEOF'
# Shell functions - sourced by .bashrc and .zshrc
# Created by Claude Code installer

# super-claude: runs claude with MCP config and centralized config directory
super-claude() {
    local mcp_config="$HOME/.claude/mcp.json"

    # Centralize Claude config in ~/.claude (not project root)
    export CLAUDE_CONFIG_DIR="$HOME/.claude"

    if [ -f "$mcp_config" ] && command -v jq &>/dev/null && jq empty "$mcp_config" 2>/dev/null; then
        claude --dangerously-skip-permissions --mcp-config "$mcp_config" "$@"
    elif [ -f "$mcp_config" ]; then
        # jq not available, try anyway if file exists
        claude --dangerously-skip-permissions --mcp-config "$mcp_config" "$@"
    else
        claude --dangerously-skip-permissions "$@"
    fi
}
FUNCSEOF
    echo "  ✓ Created ~/.shell-functions.sh"

    # Source line to add to shell configs (generic, no Claude mention)
    local source_line='[[ -f ~/.shell-functions.sh ]] && source ~/.shell-functions.sh'

    # Add source line to .bashrc (create if doesn't exist)
    touch "$HOME_DIR/.bashrc" 2>/dev/null || true
    if ! grep -q "shell-functions.sh" "$HOME_DIR/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME_DIR/.bashrc"
        echo "$source_line" >> "$HOME_DIR/.bashrc"
        echo "  ✓ Added source line to ~/.bashrc"
    else
        echo "  ✓ Source line already in ~/.bashrc"
    fi

    # Add source line to .zshrc (create if doesn't exist)
    touch "$HOME_DIR/.zshrc" 2>/dev/null || true
    if ! grep -q "shell-functions.sh" "$HOME_DIR/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME_DIR/.zshrc"
        echo "$source_line" >> "$HOME_DIR/.zshrc"
        echo "  ✓ Added source line to ~/.zshrc"
    else
        echo "  ✓ Source line already in ~/.zshrc"
    fi

    echo ""
    echo "  Usage: super-claude [args]"
    echo "  → Runs claude with ~/.claude/mcp.json automatically"
}

# ============================================================================
# Configure Git Hooks (global, pointing to ~/.claude/hooks/)
# ============================================================================
configure_git_hooks() {
    local target_dir="$1"
    local hooks_dir="$target_dir/hooks"

    echo "→ Configuring Git hooks..."

    # Create hooks directory
    mkdir -p "$hooks_dir"

    # Create pre-commit hook that calls our validation scripts
    cat > "$hooks_dir/pre-commit" << 'HOOKEOF'
#!/bin/bash
# Pre-commit hook - calls Claude Code validation scripts
SCRIPTS_DIR="$HOME/.claude/scripts"

# Run commit validation (blocks AI mentions)
if [ -x "$SCRIPTS_DIR/commit-validate.sh" ]; then
    "$SCRIPTS_DIR/commit-validate.sh" || exit 1
fi

# Run pre-commit checks (lint, format, test)
if [ -x "$SCRIPTS_DIR/pre-commit-checks.sh" ]; then
    "$SCRIPTS_DIR/pre-commit-checks.sh" || exit 1
fi

exit 0
HOOKEOF

    # Create commit-msg hook
    cat > "$hooks_dir/commit-msg" << 'HOOKEOF'
#!/bin/bash
# Commit-msg hook - validates commit message format
COMMIT_MSG_FILE="$1"
SCRIPTS_DIR="$HOME/.claude/scripts"

# Check for AI mentions in commit message
if [ -f "$COMMIT_MSG_FILE" ]; then
    MSG=$(cat "$COMMIT_MSG_FILE")

    # Forbidden patterns (case insensitive)
    FORBIDDEN=(
        "co-authored-by.*claude"
        "co-authored-by.*anthropic"
        "co-authored-by.*ai"
        "co-authored-by.*gpt"
        "generated.*by.*ai"
        "generated.*by.*claude"
        "🤖"
    )

    for pattern in "${FORBIDDEN[@]}"; do
        if echo "$MSG" | grep -iE "$pattern" > /dev/null 2>&1; then
            echo "❌ Commit blocked: AI mention detected in commit message"
            echo "   Pattern: $pattern"
            echo "   Remove AI references and try again."
            exit 1
        fi
    done
fi

exit 0
HOOKEOF

    # Make hooks executable
    chmod +x "$hooks_dir/pre-commit" "$hooks_dir/commit-msg"

    # Configure git to use our hooks directory (global)
    git config --global core.hooksPath "$hooks_dir"

    echo "  ✓ Git hooks installed in $hooks_dir"
    echo "  ✓ Global core.hooksPath configured"
    echo ""
    echo "  Hooks installed:"
    echo "    pre-commit  → runs validation scripts"
    echo "    commit-msg  → blocks AI mentions"
}

# ============================================================================
# Verification
# ============================================================================
verify_installation() {
    local target_dir="$1"
    local errors=0

    echo ""
    echo "→ Verifying installation..."

    # Check Claude CLI
    if command -v claude &>/dev/null; then
        local claude_version
        claude_version=$(claude --version 2>/dev/null || echo "unknown")
        echo "  ✓ Claude CLI: $claude_version"
    else
        echo "  ✗ Claude CLI not found in PATH"
        errors=$((errors + 1))
    fi

    # Count assets
    local agent_count=0
    local cmd_count=0
    local script_count=0
    local doc_count=0

    [ -d "$target_dir/agents" ] && agent_count=$(find "$target_dir/agents" -name "*.md" 2>/dev/null | wc -l)
    [ -d "$target_dir/commands" ] && cmd_count=$(find "$target_dir/commands" -name "*.md" 2>/dev/null | wc -l)
    [ -d "$target_dir/scripts" ] && script_count=$(find "$target_dir/scripts" -name "*.sh" 2>/dev/null | wc -l)
    [ -d "$target_dir/docs" ] && doc_count=$(find "$target_dir/docs" -name "*.md" 2>/dev/null | wc -l)

    echo "  Assets installed:"
    echo "    Agents:   $agent_count / 35 expected"
    echo "    Commands: $cmd_count / 11 expected"
    echo "    Scripts:  $script_count / 11 expected"
    if [ "$INSTALL_MINIMAL" = false ]; then
        echo "    Docs:     $doc_count / 155+ expected"
    else
        echo "    Docs:     skipped (--minimal mode)"
    fi

    # Validate settings.json
    if [ -f "$target_dir/settings.json" ]; then
        if command -v jq &>/dev/null && jq empty "$target_dir/settings.json" 2>/dev/null; then
            echo "  ✓ settings.json is valid JSON"
        else
            echo "  ⚠ settings.json validation skipped (jq not available)"
        fi
    else
        echo "  ✗ settings.json not found"
        errors=$((errors + 1))
    fi

    # Check Git hooks
    local hooks_path
    hooks_path=$(git config --global core.hooksPath 2>/dev/null || echo "")
    if [ -n "$hooks_path" ] && [ -d "$hooks_path" ]; then
        local hook_count
        hook_count=$(find "$hooks_path" -type f -executable 2>/dev/null | wc -l)
        echo "  ✓ Git hooks: $hook_count hooks in $hooks_path"
    else
        echo "  ⚠ Git hooks not configured (run configure_git_hooks)"
    fi

    echo ""
    if [ $errors -eq 0 ]; then
        echo "✓ Installation verified successfully"
        return 0
    else
        echo "⚠ Installation completed with $errors error(s)"
        return 1
    fi
}

# ============================================================================
# Main Installation Flow
# ============================================================================
main() {
    detect_environment

    install_claude_cli

    echo ""
    echo "→ Downloading Claude Code assets..."
    echo "  Target: $TARGET_DIR"
    echo ""

    # Try archive first (1 request vs 20+)
    if download_assets_archive "$TARGET_DIR"; then
        echo "  → Using archive (fast path)"
        # Only download configs separately (may need dynamic generation)
        download_configs "$TARGET_DIR"
    else
        # Fallback to individual API discovery
        echo "  → Using API discovery (slow path)"
        download_agents "$TARGET_DIR"
        download_commands "$TARGET_DIR"
        download_scripts "$TARGET_DIR"
        download_docs "$TARGET_DIR"
        download_configs "$TARGET_DIR"
    fi

    echo ""
    download_tools

    echo ""
    ensure_gitignore

    echo ""
    generate_mcp_config "$TARGET_DIR"

    echo ""
    install_super_claude

    echo ""
    configure_git_hooks "$TARGET_DIR"

    verify_installation "$TARGET_DIR"

    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ✓ Installation Complete!"
    echo "═══════════════════════════════════════════════"
    echo ""
    echo "  Installation directory: $TARGET_DIR"
    echo ""
    echo "  Available commands:"
    echo "    /git      - Git workflow (commit, branch, PR)"
    echo "    /review   - AI-powered code review"
    echo "    /plan     - Planning mode"
    echo "    /do       - Iterative task execution"
    echo "    /search   - Documentation research"
    echo "    /update   - DevContainer template update"
    echo ""
    if [ "$IS_CONTAINER" = false ]; then
        echo "  Next steps:"
        echo "    1. Restart your shell (or source ~/.zshrc)"
        echo "    2. Create items in 1Password:"
        echo "       - mcp-github (GitHub token)"
        echo "       - mcp-codacy (Codacy token)"
        echo "       - mcp-gitlab (GitLab token)"
        echo "    3. Run: super-claude"
        echo ""
    else
        echo "  → Restart the DevContainer to apply changes"
        echo ""
    fi
    echo "═══════════════════════════════════════════════"
}

# Run main installation
main
