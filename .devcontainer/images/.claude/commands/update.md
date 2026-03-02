---
name: update
description: |
  DevContainer Environment Update from official template.
  Profile-aware: auto-detects infrastructure projects and syncs from both templates.
  Uses git tarball (1 API call per source) instead of per-file curl.
  Use when: syncing local devcontainer with latest template improvements.
allowed-tools:
  - "Bash(curl:*)"
  - "Bash(git:*)"
  - "Bash(jq:*)"
  - "Read(**/*)"
  - "Write(.devcontainer/**/*)"
  - "Write(modules/**/*)"
  - "Write(stacks/**/*)"
  - "Write(ansible/**/*)"
  - "Write(packer/**/*)"
  - "Write(ci/**/*)"
  - "Write(tests/**/*)"
  - "WebFetch(*)"
  - "Glob(**/*)"
  - "Grep(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Task(*)"
---

# Update - DevContainer Environment Update

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Fallback to Grep ONLY for exact string matches or regex patterns.

---

## Description

Updates the DevContainer environment from the official template.

**GIT-TARBALL approach**: Downloads each template as a single tarball
(1 API call per source) instead of per-file curl. Extracts locally.

**Profile-aware**: Auto-detects infrastructure projects when `modules/`,
`stacks/`, or `ansible/` directories exist. No flags needed.

**Updated components (devcontainer - always):**

- **Hooks** - Claude scripts (format, lint, security, etc.)
- **Commands** - Slash commands (/git, /search, etc.)
- **Agents** - Agent definitions (specialists, executors)
- **Lifecycle** - Lifecycle hooks (delegation stubs)
- **Image-hooks** - Hooks embedded in the Docker image (real logic)
- **Shared-utils** - Shared utilities (utils.sh)
- **Config** - p10k, settings.json
- **Compose** - docker-compose.yml (update devcontainer, preserve custom)
- **Grepai** - Optimized grepai configuration

**Updated components (infrastructure - if profile detected):**

- **Modules** - Terraform modules (cloud, services, base)
- **Stacks** - Terragrunt stacks (management, edge, compute, vpn)
- **Ansible** - Roles and playbooks
- **Packer** - Machine images per provider
- **CI** - GitHub Actions + GitLab CI pipelines
- **Tests** - Terratest + Molecule tests

**Sources:**
- `github.com/kodflow/devcontainer-template` (always)
- `github.com/kodflow/infrastructure-template` (infrastructure profile only)

---

## Arguments

| Pattern | Action |
|---------|--------|
| (none) | Full update |
| `--check` | Check for available updates |
| `--component <name>` | Update a specific component |
| `--help` | Show help |

### Available components

| Component | Path | Description |
|-----------|------|-------------|
| `hooks` | `.devcontainer/images/.claude/scripts/` | Claude scripts |
| `commands` | `.devcontainer/images/.claude/commands/` | Slash commands |
| `agents` | `.devcontainer/images/.claude/agents/` | Agent definitions |
| `lifecycle` | `.devcontainer/hooks/lifecycle/` | Lifecycle hooks (stubs) |
| `image-hooks` | `.devcontainer/images/hooks/` | Image-embedded lifecycle hooks |
| `shared-utils` | `.devcontainer/hooks/shared/utils.sh` | Shared hook utilities |
| `p10k` | `.devcontainer/images/.p10k.zsh` | Powerlevel10k config |
| `settings` | `.../images/.claude/settings.json` | Claude config |
| `compose` | `.devcontainer/docker-compose.yml` | Update devcontainer service |
| `grepai` | `.devcontainer/images/grepai.config.yaml` | grepai config |

### Available components (infrastructure - auto-detected)

| Component | Path | Description |
|-----------|------|-------------|
| `modules` | `modules/` | Terraform modules (cloud, services, base) |
| `stacks` | `stacks/` | Terragrunt stacks |
| `ansible` | `ansible/` | Roles and playbooks |
| `packer` | `packer/` | Machine images per provider |
| `ci` | `ci/` | GitHub Actions + GitLab CI pipelines |
| `tests` | `tests/` | Terratest + Molecule tests |

---

## --help

```
═══════════════════════════════════════════════
  /update - DevContainer Environment Update
═══════════════════════════════════════════════

Usage: /update [options]

Options:
  (none)              Full update
  --check             Check for updates
  --component <name>  Update a component
  --help              Show this help

Components:
  hooks        Claude scripts (format, lint...)
  commands     Slash commands (/git, /search)
  agents       Agent definitions (specialists)
  lifecycle    Lifecycle hooks (delegation stubs)
  image-hooks  Image-embedded lifecycle hooks
  shared-utils Shared hook utilities (utils.sh)
  p10k         Powerlevel10k config
  settings     Claude settings.json
  compose      docker-compose.yml (devcontainer service)
  grepai       grepai config (provider, model)

Infrastructure (auto-detected):
  modules      Terraform modules (cloud, services)
  stacks       Terragrunt stacks
  ansible      Roles and playbooks
  packer       Machine images per provider
  ci           CI/CD pipelines
  tests        Terratest + Molecule tests

Profile auto-detection:
  modules/ OR stacks/ OR ansible/ exists -> infrastructure
  Otherwise -> devcontainer (single source)

Method: git tarball (1 API call per source)

Examples:
  /update                       Update everything
  /update --check               Check for updates
  /update --component hooks     Hooks only

Sources:
  kodflow/devcontainer-template (main) - always
  kodflow/infrastructure-template (main) - if infra detected
═══════════════════════════════════════════════
```

---

## Overview

DevContainer environment update using **RLM** patterns:

- **Peek** - Verify connectivity and versions
- **Profile** - Auto-detect project profile (devcontainer or infrastructure)
- **Download** - Download tarballs (1 API call per source)
- **Extract** - Extract files to correct paths
- **Synthesize** - Apply updates and consolidated report

---

## Configuration

```yaml
# DevContainer template (always - 1 API call)
REPO: "kodflow/devcontainer-template"
BRANCH: "main"
TARBALL_URL: "https://api.github.com/repos/${REPO}/tarball/${BRANCH}"

# Infrastructure template (auto-detected - 1 API call)
INFRA_REPO: "kodflow/infrastructure-template"
INFRA_BRANCH: "main"
INFRA_TARBALL_URL: "https://api.github.com/repos/${INFRA_REPO}/tarball/${INFRA_BRANCH}"
```

---

## ZSH Compatibility (CRITICAL)

**The default shell is `zsh` (set via `chsh -s /bin/zsh` in Dockerfile).**
Claude Code's Bash tool executes commands using `$SHELL` (zsh), not bash.

**RULE: All inline scripts MUST be zsh-compatible.**

| Pattern | Status | Reason |
|---------|--------|--------|
| `for x in $VAR` | **BROKEN in zsh** | zsh does not split variables on IFS |
| `while IFS= read -r x; do` | **WORKS everywhere** | Portable bash/zsh |
| `for x in literal1 literal2` | **WORKS everywhere** | No variable expansion |

**Always use `while read` for iterating over command output:**

```bash
# CORRECT (works in both bash and zsh):
curl ... | jq ... | while IFS= read -r item; do
    [ -z "$item" ] && continue
    echo "$item"
done

# INCORRECT (breaks in zsh - variable not split):
ITEMS=$(curl ... | jq ...)
for item in $ITEMS; do
    echo "$item"
done
```

**For the reference script:** Write to a temp file and execute with `bash` explicitly:
```bash
# Write script to temp file, then run with bash
cat > /tmp/update-script.sh << 'SCRIPT'
#!/bin/bash
# ... script content ...
SCRIPT
bash /tmp/update-script.sh && rm -f /tmp/update-script.sh
```

---

## Phase 1.0: Environment Detection (NEW)

**MANDATORY: Detect execution context before any operation.**

```yaml
environment_detection:
  1_container_check:
    action: "Detect if running inside container"
    method: "[ -f /.dockerenv ]"
    output: "IS_CONTAINER (true|false)"

  2_devcontainer_check:
    action: "Check DEVCONTAINER env var"
    method: "[ -n \"${DEVCONTAINER:-}\" ]"
    note: "Set by VS Code when attached to devcontainer"

  3_determine_target:
    container_mode:
      target: "/workspace/.devcontainer/images/.claude"
      behavior: "Update template source (requires rebuild)"
      propagation: "Changes applied at next container start"

    host_mode:
      target: "$HOME/.claude"
      behavior: "Update user Claude configuration"
      propagation: "Immediate (no rebuild needed)"

  4_display_context:
    output: |
      Environment: {CONTAINER|HOST}
      Update target: {path}
      Mode: {template|user}
```

**Implementation:**

```bash
# Detect environment context
detect_context() {
    # Check if running inside container
    if [ -f /.dockerenv ]; then
        CONTEXT="container"
        UPDATE_TARGET="/workspace/.devcontainer/images/.claude"
        echo "Detected: Container environment"
    else
        CONTEXT="host"
        UPDATE_TARGET="$HOME/.claude"
        echo "Detected: Host machine"
    fi

    # Additional checks
    if [ -n "${DEVCONTAINER:-}" ]; then
        echo "  (DevContainer detected via DEVCONTAINER env var)"
    fi

    echo "Update target: $UPDATE_TARGET"
    echo "Mode: $CONTEXT"
}

# Call at start of update
detect_context
```

**Output Phase 1.0:**

```
═══════════════════════════════════════════════
  /update - Environment Detection
═══════════════════════════════════════════════

  Environment: HOST MACHINE
  Update target: /home/user/.claude
  Mode: user configuration

  Changes will be:
    - Applied immediately
    - No container rebuild needed
    - Synced to container via postStart.sh

═══════════════════════════════════════════════
```

Or in container:

```
═══════════════════════════════════════════════
  /update - Environment Detection
═══════════════════════════════════════════════

  Environment: DEVCONTAINER
  Update target: /workspace/.devcontainer/images/.claude
  Mode: template source

  Changes will be:
    - Applied to template files
    - Require container rebuild to propagate
    - Or wait for next postStart.sh sync

═══════════════════════════════════════════════
```

---

## Phase 1.5: Profile Detection

**MANDATORY: Auto-detect project profile to determine sync sources. No flags.**

```yaml
profile_detection:
  1_check_directories:
    action: "Check for infrastructure markers"
    checks:
      - "[ -d modules/ ]"
      - "[ -d stacks/ ]"
      - "[ -d ansible/ ]"
    result: "Any directory exists → INFRASTRUCTURE profile"

  2_determine_profile:
    infrastructure:
      condition: "modules/ OR stacks/ OR ansible/ exists"
      sources:
        - "kodflow/devcontainer-template (always)"
        - "kodflow/infrastructure-template (additional)"
      version_files:
        - ".devcontainer/.template-version"
        - ".infra-template-version"

    devcontainer:
      condition: "No infrastructure markers found"
      sources:
        - "kodflow/devcontainer-template (only)"
      version_files:
        - ".devcontainer/.template-version"
```

**Implementation:**

```bash
detect_profile() {
    PROFILE="devcontainer"
    INFRA_DIRS_FOUND=""

    for dir in modules stacks ansible; do
        if [ -d "$dir/" ]; then
            INFRA_DIRS_FOUND="${INFRA_DIRS_FOUND} $dir"
            PROFILE="infrastructure"
        fi
    done

    echo "Profile: $PROFILE"
    if [ "$PROFILE" = "infrastructure" ]; then
        echo "  Infrastructure dirs found:$INFRA_DIRS_FOUND"
        echo "  Sources: devcontainer-template + infrastructure-template"
    else
        echo "  Source: devcontainer-template only"
    fi
}
```

**Output Phase 1.5 (infrastructure detected):**

```
═══════════════════════════════════════════════
  /update - Profile Detection
═══════════════════════════════════════════════

  Profile: infrastructure
  Detected dirs: modules stacks ansible

  Sources:
    - kodflow/devcontainer-template (always)
    - kodflow/infrastructure-template

═══════════════════════════════════════════════
```

---

## Phase 2.0: Peek (Version Check)

```yaml
peek_workflow:
  1_connectivity:
    action: "Verify GitHub connectivity"
    tool: WebFetch
    url: "https://api.github.com/repos/kodflow/devcontainer-template/commits/main"

  2_local_version:
    action: "Read local version"
    tool: Read
    file: ".devcontainer/.template-version"
```

**Output Phase 2.0:**

```
═══════════════════════════════════════════════
  /update - Peek Analysis
═══════════════════════════════════════════════

  Connectivity   : ✓ GitHub API accessible
  Local version  : abc1234 (2024-01-15)
  Remote version : def5678 (2024-01-20)

  Status: UPDATE AVAILABLE

═══════════════════════════════════════════════
```

---

## Phase 3.0: Download (Git Tarball - Single API Call)

**CRITICAL RULE: Download the full tarball in 1 API call.**

One `curl` per source instead of N individual per-file calls.
The tarball is extracted into a temp directory, then files are
copied to their destinations.

```yaml
download_workflow:
  strategy: "GIT-TARBALL (1 API call per source)"

  devcontainer_tarball:
    url: "https://api.github.com/repos/kodflow/devcontainer-template/tarball/main"
    method: "curl -sL -o /tmp/devcontainer-template.tar.gz"
    extract: "tar xzf into /tmp/devcontainer-template/"
    note: "GitHub returns tarball with prefix dir (owner-repo-sha/)"

  infrastructure_tarball:
    condition: "PROFILE == infrastructure"
    url: "https://api.github.com/repos/kodflow/infrastructure-template/tarball/main"
    method: "curl -sL -o /tmp/infrastructure-template.tar.gz"
    extract: "tar xzf into /tmp/infrastructure-template/"

  protected_paths:
    description: "NEVER overwritten - product-specific files"
    paths:
      - "inventory/"
      - "terragrunt.hcl"
      - ".env*"
      - "CLAUDE.md"
      - "AGENTS.md"
      - "README.md"
      - "Makefile"
      - "docs/"
```

**Implementation:**

```bash
# Download and extract a GitHub tarball (1 API call)
# Returns the extracted directory path via EXTRACT_DIR variable
download_tarball() {
    local tarball_url="$1"
    local label="$2"
    local tmp_dir=$(mktemp -d)
    local tmp_tar="${tmp_dir}/template.tar.gz"

    echo "  Downloading $label tarball..."
    local http_code
    http_code=$(curl -sL -w "%{http_code}" -o "$tmp_tar" "$tarball_url")

    if [ "$http_code" != "200" ]; then
        echo "  ✗ $label tarball download failed (HTTP $http_code)"
        rm -rf "$tmp_dir"
        return 1
    fi

    if [ ! -s "$tmp_tar" ]; then
        echo "  ✗ $label tarball is empty"
        rm -rf "$tmp_dir"
        return 1
    fi

    # Extract with --strip-components=1 (GitHub tarballs have owner-repo-sha/ prefix)
    if ! tar xzf "$tmp_tar" --strip-components=1 -C "$tmp_dir"; then
        echo "  ✗ $label extraction failed"
        rm -rf "$tmp_dir"
        return 1
    fi
    rm -f "$tmp_tar"

    EXTRACT_DIR="$tmp_dir"

    echo "  ✓ $label tarball downloaded and extracted"
    return 0
}
```

---

## Phase 4.0: Extract & Apply (From Tarball)

**Copy files from extracted tarballs to their destinations.
No per-file HTTP validation needed: the tarball is already validated.**

```yaml
extract_workflow:
  rule: "Copy from extracted tarball, validate non-empty"

  devcontainer_extract:
    strategy: "cp from extract dir to local paths"
    compose_strategy: "REPLACE devcontainer service, PRESERVE custom"

  infra_extract:
    strategy: "cp with protected path filtering"
    skip_protected: true
```

**Implementation:**

```bash
# Check if a path is protected (for infra sync)
is_protected() {
    local file_path="$1"
    for protected in $PROTECTED_PATHS; do
        case "$file_path" in
            "$protected"*) return 0 ;;
            */"$protected") return 0 ;;
        esac
        local bn
        bn=$(basename "$file_path")
        if [ "$bn" = "$protected" ]; then
            return 0
        fi
    done
    return 1
}

# Copy devcontainer components from extracted tarball
# Safe glob copy: copies matching files or silently skips if no match
# Usage: safe_glob_copy <pattern> <dest_dir> [+x]
safe_glob_copy() {
    local pattern="$1" dest="$2" make_exec="${3:-}"
    local found=0
    # Use find to avoid glob expansion failures under set -e
    local dir=$(dirname "$pattern")
    local glob=$(basename "$pattern")
    while IFS= read -r -d '' f; do
        cp -f "$f" "$dest/"
        [ "$make_exec" = "+x" ] && chmod +x "$dest/$(basename "$f")"
        found=1
    done < <(find "$dir" -maxdepth 1 -name "$glob" -type f -print0 2>/dev/null)
    return 0
}

apply_devcontainer_tarball() {
    local src="$EXTRACT_DIR"

    # Scripts (hooks)
    if [ -d "$src/.devcontainer/images/.claude/scripts" ]; then
        mkdir -p "$UPDATE_TARGET/scripts"
        safe_glob_copy "$src/.devcontainer/images/.claude/scripts/*.sh" "$UPDATE_TARGET/scripts" "+x"
        echo "  ✓ hooks"
    fi

    # Commands
    if [ -d "$src/.devcontainer/images/.claude/commands" ]; then
        mkdir -p "$UPDATE_TARGET/commands"
        safe_glob_copy "$src/.devcontainer/images/.claude/commands/*.md" "$UPDATE_TARGET/commands"
        echo "  ✓ commands"
    fi

    # Agents
    if [ -d "$src/.devcontainer/images/.claude/agents" ]; then
        mkdir -p "$UPDATE_TARGET/agents"
        safe_glob_copy "$src/.devcontainer/images/.claude/agents/*.md" "$UPDATE_TARGET/agents"
        echo "  ✓ agents"
    fi

    # Lifecycle stubs (container only)
    if [ "$CONTEXT" = "container" ] && [ -d "$src/.devcontainer/hooks/lifecycle" ]; then
        mkdir -p ".devcontainer/hooks/lifecycle"
        safe_glob_copy "$src/.devcontainer/hooks/lifecycle/*.sh" ".devcontainer/hooks/lifecycle" "+x"
        echo "  ✓ lifecycle"
    fi

    # Image-embedded hooks (container only)
    if [ "$CONTEXT" = "container" ] && [ -d "$src/.devcontainer/images/hooks" ]; then
        mkdir -p ".devcontainer/images/hooks/shared" ".devcontainer/images/hooks/lifecycle"
        [ -f "$src/.devcontainer/images/hooks/shared/utils.sh" ] && \
            cp -f "$src/.devcontainer/images/hooks/shared/utils.sh" ".devcontainer/images/hooks/shared/utils.sh" && \
            chmod +x ".devcontainer/images/hooks/shared/utils.sh"
        safe_glob_copy "$src/.devcontainer/images/hooks/lifecycle/*.sh" ".devcontainer/images/hooks/lifecycle" "+x"
        echo "  ✓ image-hooks"
    fi

    # Shared utils (container only - needed by initialize.sh on host)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/hooks/shared/utils.sh" ]; then
        cp -f "$src/.devcontainer/hooks/shared/utils.sh" ".devcontainer/hooks/shared/utils.sh"
        echo "  ✓ shared-utils"
    fi

    # p10k (container only)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/images/.p10k.zsh" ]; then
        cp -f "$src/.devcontainer/images/.p10k.zsh" ".devcontainer/images/.p10k.zsh"
        echo "  ✓ p10k"
    fi

    # settings.json
    if [ -f "$src/.devcontainer/images/.claude/settings.json" ]; then
        cp -f "$src/.devcontainer/images/.claude/settings.json" "$UPDATE_TARGET/settings.json"
        echo "  ✓ settings"
    fi

    # grepai config (container only)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/images/grepai.config.yaml" ]; then
        cp -f "$src/.devcontainer/images/grepai.config.yaml" ".devcontainer/images/grepai.config.yaml"
        echo "  ✓ grepai"
    fi

    # docker-compose.yml (container only, preserve custom services)
    if [ "$CONTEXT" = "container" ]; then
        update_compose_from_tarball "$src"
    fi
}

# Copy infrastructure components with protected path filtering
apply_infra_tarball() {
    if [ "$PROFILE" != "infrastructure" ]; then
        return 0
    fi

    local src="$INFRA_EXTRACT_DIR"
    local synced=0
    local skipped=0

    echo ""
    echo "  Infrastructure components:"

    for component in $INFRA_COMPONENTS; do
        if [ ! -d "$src/$component" ]; then
            continue
        fi

        local comp_count=0
        while IFS= read -r -d '' src_file; do
            local rel_path="${src_file#$src/}"

            # Always skip protected paths (prevents restoring deleted files)
            if is_protected "$rel_path"; then
                skipped=$((skipped + 1))
                continue
            fi

            mkdir -p "$(dirname "$rel_path")"
            cp -f "$src_file" "$rel_path"
            synced=$((synced + 1))
            comp_count=$((comp_count + 1))

            case "$rel_path" in
                *.sh) chmod +x "$rel_path" ;;
            esac
        done < <(find "$src/$component" -type f -print0 2>/dev/null)

        echo "    ✓ $component/ ($comp_count files)"
    done

    echo "  Synced: $synced files, Protected: $skipped skipped"
}
```

---

## Phase 5.0: Synthesize (Tarball Orchestration)

**Orchestrates the full update using tarball downloads.**

### 5.1: Download tarballs

```bash
# 1. Always: devcontainer template tarball (1 API call)
DEVCONTAINER_TARBALL_URL="https://api.github.com/repos/kodflow/devcontainer-template/tarball/main"
download_tarball "$DEVCONTAINER_TARBALL_URL" "devcontainer-template"
DEVCONTAINER_EXTRACT_DIR="$EXTRACT_DIR"

# 2. If infrastructure profile: infrastructure template tarball (1 API call)
if [ "$PROFILE" = "infrastructure" ]; then
    INFRA_TARBALL_URL="https://api.github.com/repos/kodflow/infrastructure-template/tarball/main"
    download_tarball "$INFRA_TARBALL_URL" "infrastructure-template"
    INFRA_EXTRACT_DIR="$EXTRACT_DIR"
fi
```

### 5.2: Apply devcontainer components

```bash
echo ""
echo "Applying devcontainer components..."
EXTRACT_DIR="$DEVCONTAINER_EXTRACT_DIR"
apply_devcontainer_tarball
```

### 5.3: docker-compose.yml merge (from tarball)

```bash
# Update compose from tarball (REPLACE devcontainer service, PRESERVE custom services)
# Note: Uses mikefarah/yq (Go version)
# Ollama runs on HOST (installed via initialize.sh), not in container
update_compose_from_tarball() {
    local src="$1"
    local compose_file=".devcontainer/docker-compose.yml"
    local template_compose="$src/.devcontainer/docker-compose.yml"

    if [ ! -f "$template_compose" ]; then
        echo "  ⚠ No docker-compose.yml in tarball"
        return 1
    fi

    if [ ! -f "$compose_file" ]; then
        cp "$template_compose" "$compose_file"
        echo "  ✓ docker-compose.yml created from template"
        return 0
    fi

    local temp_services=$(mktemp --suffix=.yaml)
    local temp_volumes=$(mktemp --suffix=.yaml)
    local temp_networks=$(mktemp --suffix=.yaml)
    local backup_file="${compose_file}.backup"

    # Backup original
    cp "$compose_file" "$backup_file"

    # Extract custom services (anything that's NOT devcontainer)
    yq '.services | to_entries | map(select(.key != "devcontainer")) | from_entries' \
        "$compose_file" > "$temp_services"

    # Extract custom volumes and networks
    yq '.volumes // {}' "$compose_file" > "$temp_volumes"
    yq '.networks // {}' "$compose_file" > "$temp_networks"

    # Start fresh from template
    cp "$template_compose" "$compose_file"

    # Merge back custom services if any exist
    if [ -s "$temp_services" ] && [ "$(yq '. | length' "$temp_services")" != "0" ]; then
        yq -i ".services *= load(\"$temp_services\")" "$compose_file"
        echo "    - Preserved custom services"
    fi

    # Merge back custom volumes if any exist
    if [ -s "$temp_volumes" ] && [ "$(yq '. | length' "$temp_volumes")" != "0" ]; then
        yq -i ".volumes *= load(\"$temp_volumes\")" "$compose_file"
        echo "    - Preserved custom volumes"
    fi

    # Merge back custom networks if any exist
    if [ -s "$temp_networks" ] && [ "$(yq '. | length' "$temp_networks")" != "0" ]; then
        yq -i ".networks *= load(\"$temp_networks\")" "$compose_file"
        echo "    - Preserved custom networks"
    fi

    rm -f "$temp_services" "$temp_volumes" "$temp_networks"

    # Verify
    if [ -s "$compose_file" ] && yq '.services.devcontainer' "$compose_file" > /dev/null 2>&1; then
        rm -f "$backup_file"
        echo "  ✓ docker-compose.yml updated (devcontainer replaced, custom preserved)"
        return 0
    else
        mv "$backup_file" "$compose_file"
        echo "  ✗ Compose validation failed, restored backup"
        return 1
    fi
}
```

### 5.4: Apply infrastructure components

```bash
# If infrastructure profile, apply infra tarball with protected path filtering
if [ "$PROFILE" = "infrastructure" ]; then
    echo ""
    echo "Applying infrastructure components..."
    apply_infra_tarball

    # Update infra version file
    INFRA_COMMIT=$(git ls-remote "https://github.com/$INFRA_REPO.git" "$INFRA_BRANCH" | cut -c1-7)
    DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "{\"commit\": \"$INFRA_COMMIT\", \"updated\": \"$DATE\"}" > .infra-template-version
    echo "  ✓ .infra-template-version updated"
fi
```

### 5.5: Migration: old full hooks to delegation stubs

```bash
# Detect old full hooks (without "Delegation stub" marker) and replace with stubs
for hook in onCreate postCreate postStart postAttach updateContent; do
    hook_file=".devcontainer/hooks/lifecycle/${hook}.sh"
    if [ -f "$hook_file" ] && ! grep -q "Delegation stub" "$hook_file"; then
        src_stub="$DEVCONTAINER_EXTRACT_DIR/.devcontainer/hooks/lifecycle/${hook}.sh"
        if [ -f "$src_stub" ]; then
            cp -f "$src_stub" "$hook_file"
            chmod +x "$hook_file"
            echo "  Migrated ${hook}.sh to delegation stub"
        fi
    fi
done
```

### 5.6: Cleanup deprecated files

```bash
[ -f ".coderabbit.yaml" ] && rm -f ".coderabbit.yaml" && echo "  Removed deprecated .coderabbit.yaml"
```

### 5.7: Update devcontainer version file

```bash
# Get commit SHA via git ls-remote (strip-components removes dir name)
DC_COMMIT=$(git ls-remote "https://github.com/$DEVCONTAINER_REPO.git" "$DEVCONTAINER_BRANCH" | cut -c1-7)
DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ "$CONTEXT" = "container" ]; then
    echo "{\"commit\": \"$DC_COMMIT\", \"updated\": \"$DATE\"}" > .devcontainer/.template-version
else
    echo "{\"commit\": \"$DC_COMMIT\", \"updated\": \"$DATE\"}" > "$UPDATE_TARGET/.template-version"
fi
echo "  ✓ .template-version updated ($DC_COMMIT)"
```

### 5.8: Cleanup temp directories

```bash
# Temp directories are cleaned up automatically by trap EXIT
# Registered via CLEANUP_DIRS during download phase
```

### 5.9: Consolidated report

**Output (devcontainer only):**

```
═══════════════════════════════════════════════
  ✓ DevContainer updated successfully
═══════════════════════════════════════════════

  Profile : devcontainer
  Method  : git tarball (1 API call)
  Source  : kodflow/devcontainer-template
  Version : def5678

  Updated components:
    ✓ hooks        (scripts)
    ✓ commands     (slash commands)
    ✓ agents       (agent definitions)
    ✓ lifecycle    (delegation stubs)
    ✓ image-hooks  (image-embedded hooks)
    ✓ shared-utils (utils.sh)
    ✓ p10k         (powerlevel10k)
    ✓ settings     (settings.json)
    ✓ compose      (devcontainer service)
    ✓ grepai       (bge-m3 config)

═══════════════════════════════════════════════
```

**Output (infrastructure profile):**

```
═══════════════════════════════════════════════
  ✓ DevContainer updated successfully
═══════════════════════════════════════════════

  Profile : infrastructure
  Method  : git tarball (2 API calls)
  Sources :
    - kodflow/devcontainer-template (def5678)
    - kodflow/infrastructure-template (abc1234)

  DevContainer components:
    ✓ hooks, commands, agents, lifecycle
    ✓ image-hooks, shared-utils, p10k, settings
    ✓ compose, grepai

  Infrastructure components:
    ✓ modules/ (12 files)
    ✓ stacks/ (8 files)
    ✓ ansible/ (15 files)
    ✓ packer/ (4 files)
    ✓ ci/ (6 files)
    ✓ tests/ (9 files)
    Protected: 3 skipped (inventory/, terragrunt.hcl)

═══════════════════════════════════════════════
```

---

## Phase 6.0: Hook Synchronization

**Goal:** Synchronize hooks from `~/.claude/settings.json` with the template.

**Problem solved:** Users with an older `settings.json` may have
references to obsolete scripts (bash-validate.sh, phase-validate.sh, etc.)
because `postStart.sh` only copies `settings.json` if it does not exist.

```yaml
hook_sync_workflow:
  1_backup:
    action: "Backup user settings.json"
    command: "cp ~/.claude/settings.json ~/.claude/settings.json.backup"

  2_merge_hooks:
    action: "Replace the hooks section with the template"
    strategy: "REPLACE (not merge) - the template is the source of truth"
    tool: jq
    preserves:
      - permissions
      - model
      - env
      - statusLine
      - disabledMcpjsonServers

  3_restore_on_failure:
    action: "Restore backup if merge fails"
```

**Implementation:**

```bash
sync_user_hooks() {
    local user_settings="$HOME/.claude/settings.json"
    local template_settings=".devcontainer/images/.claude/settings.json"

    if [ ! -f "$user_settings" ]; then
        echo "  ⚠ No user settings.json, skipping hook sync"
        return 0
    fi

    if [ ! -f "$template_settings" ]; then
        echo "  ✗ Template settings.json not found"
        return 1
    fi

    echo "  Synchronizing user hooks with template..."

    # Backup
    cp "$user_settings" "${user_settings}.backup"

    # Replace hooks section only (preserve all other settings)
    if jq --slurpfile tpl "$template_settings" '.hooks = $tpl[0].hooks' \
       "$user_settings" > "${user_settings}.tmp"; then

        # Validate JSON
        if jq empty "${user_settings}.tmp" 2>/dev/null; then
            mv "${user_settings}.tmp" "$user_settings"
            rm -f "${user_settings}.backup"
            echo "  ✓ User hooks synchronized with template"
            return 0
        else
            mv "${user_settings}.backup" "$user_settings"
            rm -f "${user_settings}.tmp"
            echo "  ✗ Hook merge produced invalid JSON, restored backup"
            return 1
        fi
    else
        mv "${user_settings}.backup" "$user_settings"
        echo "  ✗ Hook merge failed, restored backup"
        return 1
    fi
}
```

---

## Phase 7.0: Script Validation

**Goal:** Validate that all scripts referenced in hooks exist.

```yaml
validate_workflow:
  1_extract:
    action: "Extract all script paths from hooks"
    tool: jq
    pattern: ".hooks | .. | .command? // empty"

  2_verify:
    action: "Verify that each script exists"
    for_each: script_path
    check: "[ -f $script_path ]"

  3_report:
    on_missing: "List missing scripts with fix suggestion"
    on_success: "All scripts validated"
```

**Implementation:**

```bash
validate_hook_scripts() {
    local settings_file="$HOME/.claude/settings.json"
    local scripts_dir="$HOME/.claude/scripts"
    local missing_count=0

    if [ ! -f "$settings_file" ]; then
        echo "  ⚠ No settings.json to validate"
        return 0
    fi

    # Extract all script paths from hooks
    local scripts
    scripts=$(jq -r '.hooks | .. | .command? // empty' "$settings_file" 2>/dev/null \
        | grep -oE '/home/vscode/.claude/scripts/[^ "]+' \
        | sed 's/ .*//' \
        | sort -u)

    if [ -z "$scripts" ]; then
        echo "  ⚠ No hook scripts found in settings.json"
        return 0
    fi

    echo "  Validating hook scripts..."

    # Use while read for zsh compatibility (for x in $VAR breaks in zsh)
    echo "$scripts" | while IFS= read -r script_path; do
        [ -z "$script_path" ] && continue
        local script_name=$(basename "$script_path")

        if [ -f "$script_path" ]; then
            echo "    ✓ $script_name"
        else
            echo "    ✗ $script_name (MISSING)"
            missing_count=$((missing_count + 1))
        fi
    done

    if [ $missing_count -gt 0 ]; then
        echo ""
        echo "  ⚠ $missing_count missing script(s) detected!"
        echo "  → Run: /update --component hooks"
        return 1
    fi

    echo "  ✓ All hook scripts validated"
    return 0
}
```

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Per-file curl instead of tarball | **FORBIDDEN** | Use git tarball (1 API call) |
| Add CLI flags for profile | **FORBIDDEN** | Auto-detect only, no flags |
| Overwrite protected paths | **FORBIDDEN** | inventory/, terragrunt.hcl, .env*, CLAUDE.md, etc. |
| Write without validation | **FORBIDDEN** | Corruption risk |
| Non-official source | **FORBIDDEN** | Security |
| Hook sync without backup | **FORBIDDEN** | Always backup first |
| Delete user settings | **FORBIDDEN** | Only merge hooks |
| Skip script validation | **FORBIDDEN** | Error detection MANDATORY |
| Skip profile detection | **FORBIDDEN** | Must auto-detect before sync |
| `for x in $VAR` pattern | **FORBIDDEN** | Breaks in zsh ($SHELL=zsh) |
| Inline execution without bash | **FORBIDDEN** | Always `bash /tmp/script.sh` |

---

## Affected files

**Updated by /update (devcontainer - always):**
```
.devcontainer/
├── docker-compose.yml            # Update devcontainer service
├── hooks/
│   ├── lifecycle/*.sh            # Delegation stubs
│   └── shared/utils.sh          # Shared utilities (host)
├── images/
│   ├── .p10k.zsh
│   ├── grepai.config.yaml       # grepai config (provider, model)
│   ├── hooks/                    # Image-embedded hooks (real logic)
│   │   ├── shared/utils.sh
│   │   └── lifecycle/*.sh
│   └── .claude/
│       ├── agents/*.md
│       ├── commands/*.md
│       ├── scripts/*.sh
│       └── settings.json
└── .template-version
```

**Updated by /update (infrastructure - if profile detected):**
```
modules/                          # Terraform modules
stacks/                           # Terragrunt stacks
ansible/                          # Roles and playbooks
packer/                           # Machine images
ci/                               # CI/CD pipelines
tests/                            # Terratest + Molecule
.infra-template-version           # Infrastructure version
```

**Protected paths (NEVER overwritten if they exist):**
```
inventory/                        # Ansible inventory (project-specific)
terragrunt.hcl                    # Root terragrunt config
.env*                             # Environment files
CLAUDE.md                         # Project documentation
AGENTS.md                         # Agent configuration
README.md                         # Project readme
Makefile                          # Build configuration
docs/                             # Documentation
```

**NEVER modified:**
```
.devcontainer/
├── devcontainer.json      # Project config (customizations)
└── Dockerfile             # Image customizations
```

---

## Complete script (reference)

**IMPORTANT: This script uses `#!/bin/bash`. Always write to a temp file and execute with `bash`:**
```bash
cat > /tmp/update-devcontainer.sh << 'SCRIPT'
# ... (script below) ...
SCRIPT
bash /tmp/update-devcontainer.sh && rm -f /tmp/update-devcontainer.sh
```

```bash
#!/bin/bash
# /update implementation - Git Tarball + Profile-Aware Sync
# Downloads full tarballs (1 API call per source) instead of per-file curl.
# Auto-detects infrastructure profile (modules/, stacks/, ansible/).
# NOTE: Must be executed with bash (not zsh) due to word splitting in for loops.

set -uo pipefail
set +H 2>/dev/null || true  # Disable bash history expansion

# Configuration
DEVCONTAINER_REPO="kodflow/devcontainer-template"
DEVCONTAINER_BRANCH="main"
INFRA_REPO="kodflow/infrastructure-template"
INFRA_BRANCH="main"
INFRA_COMPONENTS="modules stacks ansible packer ci tests"
PROTECTED_PATHS="inventory/ terragrunt.hcl .env CLAUDE.md AGENTS.md README.md Makefile docs/"

# ═══ Phase 1.0: Environment Detection ═══
detect_context() {
    if [ -f /.dockerenv ]; then
        CONTEXT="container"
        UPDATE_TARGET="/workspace/.devcontainer/images/.claude"
        echo "  Environment: Container"
    else
        CONTEXT="host"
        UPDATE_TARGET="$HOME/.claude"
        echo "  Environment: Host machine"
    fi
    [ -n "${DEVCONTAINER:-}" ] && echo "  (DevContainer env var detected)"
    echo "  Target: $UPDATE_TARGET"
}

# ═══ Phase 1.5: Profile Detection ═══
detect_profile() {
    PROFILE="devcontainer"
    INFRA_DIRS_FOUND=""
    for dir in modules stacks ansible; do
        if [ -d "$dir/" ]; then
            INFRA_DIRS_FOUND="${INFRA_DIRS_FOUND} $dir"
            PROFILE="infrastructure"
        fi
    done
    echo "  Profile: $PROFILE"
    if [ "$PROFILE" = "infrastructure" ]; then
        echo "  Infrastructure dirs:$INFRA_DIRS_FOUND"
        echo "  Sources: devcontainer-template + infrastructure-template"
    else
        echo "  Source: devcontainer-template only"
    fi
}

# ═══ Download & Extract Tarball (1 API call) ═══
download_tarball() {
    local tarball_url="$1"
    local label="$2"
    local tmp_dir=$(mktemp -d)
    local tmp_tar="${tmp_dir}/template.tar.gz"

    echo "  Downloading $label tarball..."
    local http_code
    http_code=$(curl -sL -w "%{http_code}" -o "$tmp_tar" "$tarball_url")

    if [ "$http_code" != "200" ]; then
        echo "  ✗ $label download failed (HTTP $http_code)"
        rm -rf "$tmp_dir"
        return 1
    fi

    if [ ! -s "$tmp_tar" ]; then
        echo "  ✗ $label tarball is empty"
        rm -rf "$tmp_dir"
        return 1
    fi

    if ! tar xzf "$tmp_tar" --strip-components=1 -C "$tmp_dir"; then
        echo "  ✗ $label extraction failed"
        rm -rf "$tmp_dir"
        return 1
    fi
    rm -f "$tmp_tar"

    EXTRACT_DIR="$tmp_dir"

    echo "  ✓ $label downloaded and extracted"
    return 0
}

# ═══ Protected path check (for infra sync) ═══
is_protected() {
    local file_path="$1"
    for protected in $PROTECTED_PATHS; do
        case "$file_path" in
            "$protected"*) return 0 ;;
            */"$protected") return 0 ;;
        esac
        local bn
        bn=$(basename "$file_path")
        if [ "$bn" = "$protected" ]; then
            return 0
        fi
    done
    return 1
}

# ═══ Safe glob copy (avoids set -e failures on empty globs) ═══
safe_glob_copy() {
    local pattern="$1" dest="$2" make_exec="${3:-}"
    local dir=$(dirname "$pattern")
    local glob=$(basename "$pattern")
    while IFS= read -r -d '' f; do
        cp -f "$f" "$dest/"
        [ "$make_exec" = "+x" ] && chmod +x "$dest/$(basename "$f")"
    done < <(find "$dir" -maxdepth 1 -name "$glob" -type f -print0 2>/dev/null)
    return 0
}

# ═══ Apply devcontainer components from tarball ═══
apply_devcontainer_tarball() {
    local src="$DEVCONTAINER_EXTRACT_DIR"

    # Scripts (hooks)
    if [ -d "$src/.devcontainer/images/.claude/scripts" ]; then
        mkdir -p "$UPDATE_TARGET/scripts"
        safe_glob_copy "$src/.devcontainer/images/.claude/scripts/*.sh" "$UPDATE_TARGET/scripts" "+x"
        echo "  ✓ hooks"
    fi

    # Commands
    if [ -d "$src/.devcontainer/images/.claude/commands" ]; then
        mkdir -p "$UPDATE_TARGET/commands"
        safe_glob_copy "$src/.devcontainer/images/.claude/commands/*.md" "$UPDATE_TARGET/commands"
        echo "  ✓ commands"
    fi

    # Agents
    if [ -d "$src/.devcontainer/images/.claude/agents" ]; then
        mkdir -p "$UPDATE_TARGET/agents"
        safe_glob_copy "$src/.devcontainer/images/.claude/agents/*.md" "$UPDATE_TARGET/agents"
        echo "  ✓ agents"
    fi

    # Lifecycle stubs (container only)
    if [ "$CONTEXT" = "container" ] && [ -d "$src/.devcontainer/hooks/lifecycle" ]; then
        mkdir -p ".devcontainer/hooks/lifecycle"
        safe_glob_copy "$src/.devcontainer/hooks/lifecycle/*.sh" ".devcontainer/hooks/lifecycle" "+x"
        echo "  ✓ lifecycle"
    fi

    # Image-embedded hooks (container only)
    if [ "$CONTEXT" = "container" ] && [ -d "$src/.devcontainer/images/hooks" ]; then
        mkdir -p ".devcontainer/images/hooks/shared" ".devcontainer/images/hooks/lifecycle"
        [ -f "$src/.devcontainer/images/hooks/shared/utils.sh" ] && \
            cp -f "$src/.devcontainer/images/hooks/shared/utils.sh" ".devcontainer/images/hooks/shared/utils.sh" && \
            chmod +x ".devcontainer/images/hooks/shared/utils.sh"
        safe_glob_copy "$src/.devcontainer/images/hooks/lifecycle/*.sh" ".devcontainer/images/hooks/lifecycle" "+x"
        echo "  ✓ image-hooks"
    fi

    # Shared utils (container only)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/hooks/shared/utils.sh" ]; then
        cp -f "$src/.devcontainer/hooks/shared/utils.sh" ".devcontainer/hooks/shared/utils.sh"
        echo "  ✓ shared-utils"
    fi

    # p10k (container only)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/images/.p10k.zsh" ]; then
        cp -f "$src/.devcontainer/images/.p10k.zsh" ".devcontainer/images/.p10k.zsh"
        echo "  ✓ p10k"
    fi

    # settings.json
    if [ -f "$src/.devcontainer/images/.claude/settings.json" ]; then
        cp -f "$src/.devcontainer/images/.claude/settings.json" "$UPDATE_TARGET/settings.json"
        echo "  ✓ settings"
    fi

    # grepai config (container only)
    if [ "$CONTEXT" = "container" ] && [ -f "$src/.devcontainer/images/grepai.config.yaml" ]; then
        cp -f "$src/.devcontainer/images/grepai.config.yaml" ".devcontainer/images/grepai.config.yaml"
        echo "  ✓ grepai"
    fi

    # docker-compose.yml (container only)
    if [ "$CONTEXT" = "container" ]; then
        update_compose_from_tarball "$src"
    fi
}

# ═══ Compose merge from tarball ═══
update_compose_from_tarball() {
    local src="$1"
    local compose_file=".devcontainer/docker-compose.yml"
    local template_compose="$src/.devcontainer/docker-compose.yml"

    if [ ! -f "$template_compose" ]; then
        return 0
    fi

    if [ ! -f "$compose_file" ]; then
        cp "$template_compose" "$compose_file"
        echo "  ✓ compose (created from template)"
        return 0
    fi

    local temp_services=$(mktemp --suffix=.yaml)
    local temp_volumes=$(mktemp --suffix=.yaml)
    local temp_networks=$(mktemp --suffix=.yaml)
    local backup_file="${compose_file}.backup"
    cp "$compose_file" "$backup_file"

    # Extract custom services, volumes, and networks
    yq '.services | to_entries | map(select(.key != "devcontainer")) | from_entries' \
        "$compose_file" > "$temp_services"
    yq '.volumes // {}' "$compose_file" > "$temp_volumes"
    yq '.networks // {}' "$compose_file" > "$temp_networks"

    cp "$template_compose" "$compose_file"

    # Merge back custom services
    if [ -s "$temp_services" ] && [ "$(yq '. | length' "$temp_services")" != "0" ]; then
        yq -i ".services *= load(\"$temp_services\")" "$compose_file"
    fi

    # Merge back custom volumes
    if [ -s "$temp_volumes" ] && [ "$(yq '. | length' "$temp_volumes")" != "0" ]; then
        yq -i ".volumes *= load(\"$temp_volumes\")" "$compose_file"
    fi

    # Merge back custom networks
    if [ -s "$temp_networks" ] && [ "$(yq '. | length' "$temp_networks")" != "0" ]; then
        yq -i ".networks *= load(\"$temp_networks\")" "$compose_file"
    fi

    rm -f "$temp_services" "$temp_volumes" "$temp_networks"

    if [ -s "$compose_file" ] && yq '.services.devcontainer' "$compose_file" > /dev/null 2>&1; then
        rm -f "$backup_file"
        echo "  ✓ compose (devcontainer replaced, custom preserved)"
    else
        mv "$backup_file" "$compose_file"
        echo "  ✗ compose validation failed, restored backup"
        return 1
    fi
}

# ═══ Apply infrastructure components with protected paths ═══
apply_infra_tarball() {
    if [ "$PROFILE" != "infrastructure" ]; then
        return 0
    fi

    local src="$INFRA_EXTRACT_DIR"
    local synced=0
    local skipped=0

    echo "  Infrastructure components:"
    for component in $INFRA_COMPONENTS; do
        [ ! -d "$src/$component" ] && continue

        local comp_count=0
        while IFS= read -r -d '' src_file; do
            local rel_path="${src_file#$src/}"

            # Always skip protected paths (prevents restoring deleted files)
            if is_protected "$rel_path"; then
                skipped=$((skipped + 1))
                continue
            fi

            mkdir -p "$(dirname "$rel_path")"
            cp -f "$src_file" "$rel_path"
            synced=$((synced + 1))
            comp_count=$((comp_count + 1))

            case "$rel_path" in
                *.sh) chmod +x "$rel_path" ;;
            esac
        done < <(find "$src/$component" -type f -print0 2>/dev/null)

        echo "    ✓ $component/ ($comp_count files)"
    done

    echo "  Synced: $synced files, Protected: $skipped skipped"
}

# ═══ Hook synchronization (Phase 6.0) ═══
sync_user_hooks() {
    local user_settings="$HOME/.claude/settings.json"
    local template_settings=".devcontainer/images/.claude/settings.json"

    if [ ! -f "$user_settings" ]; then
        echo "  ⚠ No user settings.json, skipping hook sync"
        return 0
    fi

    if [ ! -f "$template_settings" ]; then
        echo "  ✗ Template settings.json not found"
        return 1
    fi

    echo "  Synchronizing user hooks with template..."
    cp "$user_settings" "${user_settings}.backup"

    if jq --slurpfile tpl "$template_settings" '.hooks = $tpl[0].hooks' \
       "$user_settings" > "${user_settings}.tmp"; then
        if jq empty "${user_settings}.tmp" 2>/dev/null; then
            mv "${user_settings}.tmp" "$user_settings"
            rm -f "${user_settings}.backup"
            echo "  ✓ User hooks synchronized"
            return 0
        else
            mv "${user_settings}.backup" "$user_settings"
            rm -f "${user_settings}.tmp"
            echo "  ✗ Invalid JSON, restored backup"
            return 1
        fi
    else
        mv "${user_settings}.backup" "$user_settings"
        echo "  ✗ Hook merge failed, restored backup"
        return 1
    fi
}

# ═══ Script validation (Phase 7.0) ═══
validate_hook_scripts() {
    local settings_file="$HOME/.claude/settings.json"
    local missing_count=0

    if [ ! -f "$settings_file" ]; then
        echo "  ⚠ No settings.json to validate"
        return 0
    fi

    local scripts
    scripts=$(jq -r '.hooks | .. | .command? // empty' "$settings_file" 2>/dev/null \
        | grep -oE '/home/vscode/.claude/scripts/[^ "]+' \
        | sed 's/ .*//' | sort -u)

    if [ -z "$scripts" ]; then
        echo "  ⚠ No hook scripts found"
        return 0
    fi

    echo "  Validating hook scripts..."
    while IFS= read -r script_path; do
        [ -z "$script_path" ] && continue
        local script_name=$(basename "$script_path")
        if [ -f "$script_path" ]; then
            echo "    ✓ $script_name"
        else
            echo "    ✗ $script_name (MISSING)"
            missing_count=$((missing_count + 1))
        fi
    done <<< "$scripts"

    if [ $missing_count -gt 0 ]; then
        echo "  ⚠ $missing_count missing script(s)!"
        return 1
    fi

    echo "  ✓ All scripts validated"
    return 0
}

# ═══════════════════════════════════════════════
#   MAIN EXECUTION
# ═══════════════════════════════════════════════

# Cleanup temp directories on exit (normal or error)
CLEANUP_DIRS=""
cleanup() {
    for d in $CLEANUP_DIRS; do
        rm -rf "$d" 2>/dev/null
    done
}
trap cleanup EXIT

echo "═══════════════════════════════════════════════"
echo "  /update - DevContainer Environment Update"
echo "═══════════════════════════════════════════════"
echo ""

# Phase 1.0: Environment Detection
echo "Phase 1.0: Environment Detection"
detect_context
echo ""

# Phase 1.5: Profile Detection
echo "Phase 1.5: Profile Detection"
detect_profile
echo ""

# Phase 3.0: Download tarballs
echo "Phase 3.0: Download (git tarball)"
DEVCONTAINER_TARBALL="https://api.github.com/repos/$DEVCONTAINER_REPO/tarball/$DEVCONTAINER_BRANCH"
download_tarball "$DEVCONTAINER_TARBALL" "devcontainer-template"
DEVCONTAINER_EXTRACT_DIR="$EXTRACT_DIR"
CLEANUP_DIRS="$DEVCONTAINER_EXTRACT_DIR"

if [ "$PROFILE" = "infrastructure" ]; then
    INFRA_TARBALL="https://api.github.com/repos/$INFRA_REPO/tarball/$INFRA_BRANCH"
    download_tarball "$INFRA_TARBALL" "infrastructure-template"
    INFRA_EXTRACT_DIR="$EXTRACT_DIR"
    CLEANUP_DIRS="$CLEANUP_DIRS $INFRA_EXTRACT_DIR"
fi
echo ""

# Phase 4.0: Extract & Apply
echo "Phase 4.0: Apply devcontainer components"
apply_devcontainer_tarball

# Migration: old full hooks to delegation stubs
if [ "$CONTEXT" = "container" ]; then
    for hook in onCreate postCreate postStart postAttach updateContent; do
        hook_file=".devcontainer/hooks/lifecycle/${hook}.sh"
        if [ -f "$hook_file" ] && ! grep -q "Delegation stub" "$hook_file"; then
            src_stub="$DEVCONTAINER_EXTRACT_DIR/.devcontainer/hooks/lifecycle/${hook}.sh"
            if [ -f "$src_stub" ]; then
                cp -f "$src_stub" "$hook_file"
                chmod +x "$hook_file"
                echo "  Migrated ${hook}.sh to delegation stub"
            fi
        fi
    done
fi

# Infrastructure components
if [ "$PROFILE" = "infrastructure" ]; then
    echo ""
    echo "Phase 4.1: Apply infrastructure components"
    apply_infra_tarball
fi
echo ""

# Phase 6.0: Synchronize user hooks
echo "Phase 6.0: Synchronizing user hooks..."
sync_user_hooks
echo ""

# Phase 7.0: Validate hook scripts
echo "Phase 7.0: Validating hook scripts..."
validate_hook_scripts
echo ""

# Version tracking (use git ls-remote for commit SHA)
echo "Updating version files..."
DC_COMMIT=$(git ls-remote "https://github.com/$DEVCONTAINER_REPO.git" "$DEVCONTAINER_BRANCH" | cut -c1-7)
DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ "$CONTEXT" = "container" ]; then
    echo "{\"commit\": \"$DC_COMMIT\", \"updated\": \"$DATE\"}" > .devcontainer/.template-version
else
    echo "{\"commit\": \"$DC_COMMIT\", \"updated\": \"$DATE\"}" > "$UPDATE_TARGET/.template-version"
fi
echo "  ✓ .template-version ($DC_COMMIT)"

if [ "$PROFILE" = "infrastructure" ] && [ -n "${INFRA_EXTRACT_DIR:-}" ]; then
    INFRA_COMMIT=$(git ls-remote "https://github.com/$INFRA_REPO.git" "$INFRA_BRANCH" | cut -c1-7)
    echo "{\"commit\": \"$INFRA_COMMIT\", \"updated\": \"$DATE\"}" > .infra-template-version
    echo "  ✓ .infra-template-version ($INFRA_COMMIT)"
fi

# Cleanup deprecated files
[ -f ".coderabbit.yaml" ] && rm -f ".coderabbit.yaml" && echo "  Removed deprecated .coderabbit.yaml"

# Temp directories cleaned up automatically by trap EXIT

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✓ Update complete"
echo "  Profile: $PROFILE"
echo "  Method: git tarball"
if [ "$PROFILE" = "infrastructure" ]; then
    echo "  Sources: $DEVCONTAINER_REPO + $INFRA_REPO"
else
    echo "  Source: $DEVCONTAINER_REPO"
fi
echo "  Version: $DC_COMMIT"
echo "═══════════════════════════════════════════════"
```
