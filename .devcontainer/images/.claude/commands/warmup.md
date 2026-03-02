---
name: warmup
description: |
  Project context pre-loading with RLM decomposition.
  Reads CLAUDE.md hierarchy using funnel strategy (root → leaves).
  Use when: starting a session, preparing for complex tasks, or updating documentation.
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Grep(**/*)"
  - "Write(**/*)"
  - "Edit(**/*)"
  - "Task(*)"
  - "TaskCreate(*)"
  - "TaskUpdate(*)"
  - "TaskList(*)"
  - "TaskGet(*)"
  - "Bash(git:*)"
  - "mcp__taskmaster__*"
---

# /warmup - Project Context Pre-loading (RLM Architecture)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Validate CLAUDE.md conventions against current library documentation
- Check for outdated API references in existing documentation

---

## Overview

Project context pre-loading with **RLM** patterns:

- **Peek** - Discover the CLAUDE.md hierarchy
- **Funnel** - Funnel reading (root → leaves)
- **Parallelize** - Parallel analysis by domain
- **Synthesize** - Consolidated context ready to use

**Principle**: Load context → Be more effective on tasks

---

## Arguments

| Pattern | Action |
|---------|--------|
| (none) | Pre-load all project context |
| `--update` | Update all CLAUDE.md + create missing ones |
| `--dry-run` | Show what would be updated (with --update) |
| `--help` | Display help |

---

## --help

```
═══════════════════════════════════════════════════════════════
  /warmup - Project Context Pre-loading (RLM)
═══════════════════════════════════════════════════════════════

Usage: /warmup [options]

Options:
  (none)            Pre-load complete context
  --update          Update + create missing CLAUDE.md
  --dry-run         Show changes (with --update)
  --help            Display this help

Line Thresholds (CLAUDE.md):
  IDEAL       :   0-150 lines (simple directories)
  ACCEPTABLE  : 151-200 lines (medium complexity)
  WARNING     : 201-250 lines (review recommended)
  CRITICAL    : 251-300 lines (must be condensed)
  FORBIDDEN   :  301+ lines (split required)

Exclusions (STRICT .gitignore respect):
  - vendor/, node_modules/, .git/
  - All patterns from .gitignore are honored
  - bin/, dist/, build/ (generated outputs)

RLM Patterns:
  1. Peek       - Discover the CLAUDE.md hierarchy
  2. Funnel     - Funnel reading (root → leaves)
  3. Parallelize - Analysis by domain
  4. Synthesize - Consolidated context

Examples:
  /warmup                       Pre-load context
  /warmup --update              Update + create missing
  /warmup --update --dry-run    Preview changes

Workflow:
  /warmup → /plan → /do → /git

═══════════════════════════════════════════════════════════════
```

**IF `$ARGUMENTS` contains `--help`**: Display the help above and STOP.

---

## Normal Mode (Pre-loading)

### Phase 1.0: Peek (Hierarchy Discovery)

```yaml
peek_workflow:
  1_discover:
    action: "Discover all CLAUDE.md files in the project"
    tool: Glob
    pattern: "**/CLAUDE.md"
    output: [claude_files]

  2_build_tree:
    action: "Build the context tree by depth"
    algorithm: |
      FOR each file:
        depth = path.count('/') - base.count('/')
      Sort by ascending depth
      depth 0: /CLAUDE.md (root)
      depth 1: /src/CLAUDE.md, /.devcontainer/CLAUDE.md
      depth 2+: subdirectories

  3_detect_project:
    action: "Identify the project type"
    tools: [Glob]
    patterns:
      - "go.mod" → Go
      - "package.json" → Node.js
      - "Cargo.toml" → Rust
      - "pyproject.toml" → Python
      - "*.tf" → Terraform
      - "pom.xml" → Java (Maven)
      - "build.gradle" → Java/Kotlin (Gradle)
      - "build.sbt" → Scala
      - "mix.exs" → Elixir
      - "composer.json" → PHP
      - "Gemfile" → Ruby
      - "pubspec.yaml" → Dart/Flutter
      - "CMakeLists.txt" → C/C++ (CMake)
      - "*.csproj" → C# (.NET)
      - "Package.swift" → Swift
      - "DESCRIPTION" → R
      - "cpanfile" → Perl
      - "*.rockspec" → Lua
      - "fpm.toml" → Fortran
      - "alire.toml" → Ada
      - "*.cob" → COBOL
      - "*.lpi" → Pascal
      - "*.vbproj" → VB.NET
```

**Output Phase 1:**

```
═══════════════════════════════════════════════════════════════
  /warmup - Peek Analysis
═══════════════════════════════════════════════════════════════

  Project: /workspace
  Type   : <detected_type>

  CLAUDE.md Hierarchy (<n> files):
    depth 0 : /CLAUDE.md (project root)
    depth 1 : /.devcontainer/CLAUDE.md, /src/CLAUDE.md
    depth 2 : /.devcontainer/features/CLAUDE.md
    ...

  Strategy: Funnel (root → leaves, decreasing detail)

═══════════════════════════════════════════════════════════════
```

---

### Phase 1.5: Taskmaster + Feature Context (Conditional)

```yaml
phase_1.5_taskmaster:
  condition: "mcp__taskmaster__ available AND .taskmaster/ exists"
  action: "mcp__taskmaster__get_tasks(status: pending) + mcp__taskmaster__get_tasks(status: in-progress)"
  output: "Inject active tasks into working context"

phase_1.5_features:
  condition: ".claude/features.json exists"
  action: |
    Read .claude/features.json
    IF version == 1: note "Schema v1 detected — run /feature to auto-migrate to v2"
    IF version == 2: run infer_hierarchy (see /feature Hierarchy Inference)
  output: |
    Inject active features as hierarchy tree:
      F001  [L0] DDD Architecture       | completed
      ├─ F002  [L1] HTTP Server         | in_progress
      └─ F003  [L1] Database layer      | completed
    Orphans (level > 0 with no parent) shown with ⚠ warning.
```

---

### Phase 2.0: Funnel (Funnel Reading)

```yaml
funnel_strategy:
  principle: "Read from most general to most specific"

  levels:
    depth_0:
      files: ["/CLAUDE.md"]
      extract: ["project_rules", "structure", "workflow", "safeguards"]
      detail_level: "HIGH"

    depth_1:
      files: ["src/CLAUDE.md", ".devcontainer/CLAUDE.md"]
      extract: ["conventions", "key_files", "domain_rules"]
      detail_level: "MEDIUM"

    depth_2_plus:
      files: ["**/CLAUDE.md"]
      extract: ["specific_rules", "attention_points"]
      detail_level: "LOW"

  extraction_rules:
    include:
      - "MANDATORY/ABSOLUTE rules"
      - "Directory structure"
      - "Specific conventions"
      - "Guardrails"
    exclude:
      - "Complete code examples"
      - "Implementation details"
      - "Long code blocks"
```

**Reading algorithm:**

```
FOR depth FROM 0 TO max_depth:
    files = filter(claude_files, depth)

    PARALLEL FOR each file IN files:
        content = Read(file)
        context[file] = extract_essential(content, detail_level)

    consolidate(context, depth)
```

---

### Phase 3.0: Parallelize (Analysis by Domain)

```yaml
parallel_analysis:
  mode: "PARALLEL (single message, 4 Task calls)"

  agents:
    - task: "source-analyzer"
      type: "Explore"
      scope: "src/"
      prompt: |
        Analyze the source code structure:
        - Main packages/modules
        - Detected architectural patterns
        - Attention points (TODO, FIXME, HACK)
        Return: {packages[], patterns[], attention_points[]}

    - task: "config-analyzer"
      type: "Explore"
      scope: ".devcontainer/"
      prompt: |
        Analyze the DevContainer configuration:
        - Installed features
        - Configured services
        - Available MCP servers
        Return: {features[], services[], mcp_servers[]}

    - task: "test-analyzer"
      type: "Explore"
      scope: "tests/ OR **/*_test.go OR **/*.test.ts"
      prompt: |
        Analyze the test coverage:
        - Test files found
        - Test patterns used
        Return: {test_files[], patterns[], coverage_estimate}

    - task: "docs-analyzer"
      type: "Explore"
      scope: "~/.claude/docs/"
      prompt: |
        Analyze the knowledge base:
        - Available pattern categories
        - Number of patterns per category
        Return: {categories[], pattern_count}
```

**IMPORTANT**: Launch all 4 agents in ONE SINGLE message.

---

### Phase 4.0: Synthesize (Consolidated Context)

```yaml
synthesize_workflow:
  1_merge:
    action: "Merge agent results"
    inputs:
      - "context_tree (Phase 2)"
      - "source_analysis (Phase 3)"
      - "config_analysis (Phase 3)"
      - "test_analysis (Phase 3)"
      - "docs_analysis (Phase 3)"

  2_prioritize:
    action: "Prioritize information"
    levels:
      - CRITICAL: "Absolute rules, guardrails, mandatory conventions"
      - HIGH: "Project structure, patterns used, available MCP"
      - MEDIUM: "Features, services, test coverage"
      - LOW: "Specific details, minor attention points"

  3_format:
    action: "Format context for session"
    output: "Session context ready"
```

**Final Output (Normal Mode):**

```
═══════════════════════════════════════════════════════════════
  /warmup - Context Loaded Successfully
═══════════════════════════════════════════════════════════════

  Project: <project_name>
  Type   : <detected_type>

  Context Summary:
    ├─ CLAUDE.md files read: <n>
    ├─ Source packages: <n>
    ├─ Test files: <n>
    ├─ Design patterns: <n>
    └─ MCP servers: <n>

  Key Rules Loaded:
    ✓ MCP-FIRST: Always use MCP before CLI
    ✓ GREPAI-FIRST: Semantic search before Grep
    ✓ Code in /src: All code MUST be in /src
    ✓ SAFEGUARDS: Never delete .claude/ or .devcontainer/

  Attention Points Detected:
    ├─ <n> TODO items in src/
    ├─ <n> FIXME in config
    └─ <n> deprecated APIs flagged

  Ready for:
    → /plan <feature>
    → /review
    → /do <task>

  Skill Discipline:
    Red flags (NEVER rationalize these):
    - "This is just a simple question" → Questions are tasks
    - "I remember this skill" → Skills evolve, read current version
    - "The skill is overkill" → Simple tasks become complex
    - "I'll do one thing first" → Check skills BEFORE acting

═══════════════════════════════════════════════════════════════
```

---

## Mode --update (Documentation Update)

### Phase 1.0: Full Code Scan

```yaml
scan_workflow:
  0_load_gitignore:
    action: "Load .gitignore patterns"
    command: "cat /workspace/.gitignore 2>/dev/null"
    rule: "ALL patterns are STRICTLY respected"

  1_discover_code:
    action: "Scan all code files (respecting .gitignore)"
    tools: [Bash, Glob]
    command: |
      # Uses git ls-files to respect .gitignore
      git ls-files --cached --others --exclude-standard \
        '*.go' '*.ts' '*.py' '*.sh' '*.rs' '*.java'
    patterns:
      - "src/**/*.go"
      - "src/**/*.ts"
      - "src/**/*.py"
      - "**/*.sh"
    exclude_source: ".gitignore (STRICT)"
    always_excluded:
      - ".git/"

  2_extract_metadata:
    action: "Extract metadata per directory"
    parallel_per_directory:
      - "Public functions/types"
      - "Patterns used"
      - "TODO/FIXME/HACK"
      - "Critical imports"
      - "Obsolete elements"

  3_check_claude_files:
    action: "Verify consistency with existing CLAUDE.md files"
    for_each: claude_files
    checks:
      - "Documented structure vs actual structure"
      - "Referenced files still exist"
      - "Documented conventions are followed"
      - "Obsolete information to remove"
```

---

### Phase 2.0: Creating Missing CLAUDE.md Files

**Default behavior of --update** (not a separate option).

```yaml
create_missing_workflow:
  trigger: "Always executed with --update"

  gitignore_respect:
    rule: "STRICT - All .gitignore patterns are honored"
    implementation: |
      # Read and parse .gitignore
      gitignore_patterns = parse_gitignore("/workspace/.gitignore")

      # Use git ls-files to list only tracked files
      tracked_dirs = git ls-files --directory | get_unique_dirs()

      # OR use git check-ignore to validate
      for dir in candidate_dirs:
        if git check-ignore -q "$dir":
          skip(dir)  # Ignored by .gitignore

  scan_directories:
    action: "Find directories without CLAUDE.md (respecting .gitignore)"
    tool: Bash + Glob
    command: |
      # List only directories NOT ignored by git
      find /workspace -type d \
        -not -path '*/.git/*' \
        -exec sh -c 'git check-ignore -q "$1" 2>/dev/null || echo "$1"' _ {} \; \
        | while read dir; do
            # Check if it contains source code
            if ls "$dir"/*.{go,ts,py,rs,java,sh,html,tf} 2>/dev/null | head -1 > /dev/null; then
              [ ! -f "$dir/CLAUDE.md" ] && echo "$dir"
            fi
          done

    include_criteria:
      code_files:
        - "*.go, *.ts, *.py, *.rs, *.java"
        - "*.sh (scripts)"
        - "*.html, *.css (web)"
        - "Dockerfile*, *.tf (infra)"

    exclude_sources:
      primary: ".gitignore (STRICT)"
      always_excluded:
        - ".git/"
        - "**/testdata/**"
        - "**/__pycache__/**"

  create_template:
    format: |
      # <Directory Name>

      ## Purpose
      TODO: Describe the purpose of this directory.

      ## Structure
      ```text
      <auto-generated tree>
      ```

      ## Key Files
      | File | Description |
      |------|-------------|
      | <files> | TODO |

    max_lines: 30  # Minimal template, enriched later

  output: |
    ═══════════════════════════════════════════════════════════
      /warmup --update - Phase 2.0: Missing CLAUDE.md
    ═══════════════════════════════════════════════════════════

    .gitignore patterns loaded: <n> patterns

    Directories without CLAUDE.md (not in .gitignore):
      ├─ /workspace/website/ (HTML/CSS detected)
      ├─ /workspace/api/ (Proto files detected)
      └─ /workspace/setup/scripts/ (Shell scripts detected)

    Skipped (in .gitignore):
      ├─ /workspace/vendor/ (gitignored)
      ├─ /workspace/node_modules/ (gitignored)
      └─ /workspace/bin/ (gitignored)

    Action: Create template CLAUDE.md for each?
      [Apply all] [Select individually] [Skip]

    ═══════════════════════════════════════════════════════════
```

**ABSOLUTE RULE: .gitignore is the source of truth for exclusions.**

| Exclusion source | Priority | Examples |
|------------------|----------|----------|
| `.gitignore` | **STRICT** | vendor/, node_modules/, *.log |
| Always excluded | Hardcoded | .git/, testdata/, __pycache__/ |

**Creation heuristics:**

| Detected content | Create CLAUDE.md? | Condition |
|------------------|-------------------|-----------|
| Source code (*.go, *.ts, *.py) | YES | If not gitignored |
| Scripts (*.sh) | YES | If not gitignored |
| Web assets (*.html, *.css) | YES | If not gitignored |
| Infra config (Dockerfile, *.tf) | YES | If not gitignored |
| Any gitignored directory | NO | .gitignore respected |

---

### Phase 3.0: Obsolescence Detection

```yaml
obsolete_detection:
  file_references:
    description: "Files mentioned in CLAUDE.md but deleted"
    action: |
      FOR each CLAUDE.md:
        extract referenced file paths
        verify each file exists
        mark as obsolete if not found

  structure_changes:
    description: "Directory structure changed"
    action: |
      FOR each CLAUDE.md with 'Structure' section:
        compare documented structure vs actual
        identify differences

  api_changes:
    description: "APIs/functions renamed or removed"
    action: |
      use grepai to search for references
      if 0 results → possibly obsolete

  deprecated_patterns:
    description: "Deprecated patterns still documented"
    action: |
      verify imports/usages in code
      compare with what is documented
```

---

### Phase 4.0: Generating Updates

```yaml
update_generation:
  for_each: directory_with_claude_md

  format: |
    # <Directory Name>

    ## Purpose
    <Short description of the directory's role>

    ## Structure
    ```text
    <current tree>
    ```

    ## Key Files
    | File | Description |
    |------|-------------|
    | <file> | <description> |

    ## Conventions
    - <convention 1>
    - <convention 2>

    ## Attention Points
    - <attention point detected in code>

  constraints:
    max_lines: 200  # ACCEPTABLE threshold
    critical_threshold: 300  # Must be condensed or split
    no_implementation_details: true
    no_obsolete_info: true
    maintain_existing_structure: true
```

---

### Phase 5.0: Applying Changes

```yaml
apply_workflow:
  dry_run:
    condition: "--dry-run flag present"
    action: "Display differences without modifying"
    output: |
      ═══════════════════════════════════════════════════════════
        /warmup --update --dry-run
      ═══════════════════════════════════════════════════════════

      Files to update:
        ├─ /src/CLAUDE.md
        │   - Remove: "<file>" (deleted)
        │   + Add: "<file>" (new)
        │
        └─ /.devcontainer/features/CLAUDE.md
            + Add: New feature detected

      Total: <n> files, <n> changes
      Run without --dry-run to apply.
      ═══════════════════════════════════════════════════════════

  interactive:
    condition: "No --dry-run flag"
    for_each_file:
      action: "Display diff and ask for confirmation"
      tool: AskUserQuestion
      options:
        - "Apply this change"
        - "Skip this file"
        - "Edit manually"
        - "Apply all remaining"

    on_apply:
      action: "Write the updated file"
      tool: Edit or Write
      backup: true

  timestamp_injection:
    action: "Add/update ISO timestamp on first line"
    algorithm: |
      FOR each updated CLAUDE.md:
        timestamp = "<!-- updated: " + now().toISO8601() + "Z -->"
        IF first_line matches '<!-- updated: .* -->':
          replace first_line with timestamp
        ELSE:
          insert timestamp as first line
    format: "<!-- updated: YYYY-MM-DDTHH:MM:SSZ -->"
    example: "<!-- updated: 2026-02-11T14:30:00Z -->"
    purpose: |
      Allows /git Phase 3.8 to detect staleness.
      Files updated less than 5 minutes ago are ignored.

  validation:
    post_apply:
      - "Verify file lines: IDEAL(0-150), ACCEPTABLE(151-200), WARNING(201-250), CRITICAL(251-300)"
      - "Flag files > 300 lines as FORBIDDEN (must split)"
      - "Verify no obsolete references"
      - "Verify structure section matches reality"
      - "Verify timestamp injected in first line"
```

### Phase 6.0: GrepAI Config Update (Project-Specific Exclusions)

**Updates the grepai configuration with project-specific exclusions.**

```yaml
grepai_config_update:
  trigger: "Always executed with --update"
  config_path: "/workspace/.grepai/config.yaml"
  template_path: "/etc/grepai/config.yaml"

  workflow:
    1_detect_project_patterns:
      action: "Analyze project-specific patterns"
      checks:
        - ".gitignore patterns not covered by template"
        - "Dynamically generated directories (logs, cache)"
        - "Framework-specific directories (Next.js .next/, Nuxt .nuxt/)"

    2_compare_with_template:
      action: "Compare current config vs template"
      detect:
        - "New exclusions to add"
        - "Obsolete exclusions to remove"

    3_merge_exclusions:
      action: "Merge exclusions"
      rules:
        - "Keep all template exclusions"
        - "Add project-specific exclusions"
        - "Mark additions with comment # Project-specific"

    4_apply_config:
      action: "Write the updated config"
      tool: Write
      backup: true

  project_detection:
    nextjs:
      detect: "next.config.{js,ts,mjs}"
      add: [".next", ".vercel"]
    nuxt:
      detect: "nuxt.config.{js,ts}"
      add: [".nuxt", ".output"]
    vite:
      detect: "vite.config.{js,ts}"
      add: [".vite"]
    turbo:
      detect: "turbo.json"
      add: [".turbo"]
    nx:
      detect: "nx.json"
      add: [".nx", "nx-cloud.env"]
    docker:
      detect: "docker-compose*.{yml,yaml}"
      add: [".docker"]
    terraform:
      detect: "*.tf"
      add: [".terraform", "*.tfstate*"]

  output: |
    ═══════════════════════════════════════════════════════════
      /warmup --update - Phase 6.0: GrepAI Config
    ═══════════════════════════════════════════════════════════

    Config: /workspace/.grepai/config.yaml

    Project patterns detected:
      ├─ Next.js → adding .next, .vercel
      └─ Terraform → adding .terraform

    Exclusions updated:
      + .next (Project-specific)
      + .vercel (Project-specific)
      + .terraform (Project-specific)

    ✓ grepai config updated

    ═══════════════════════════════════════════════════════════
```

---

### Phase 7.0: Learn (Extract Conventions)

**Extract non-obvious conventions from code into CLAUDE.md files.**

```yaml
learn_workflow:
  trigger: "Always executed with --update (after all other phases)"
  purpose: "Auto-discover implicit patterns and inject into CLAUDE.md hierarchy"

  1_analyze_patterns:
    action: "Scan codebase for implicit conventions not yet documented"
    tools: [Grep, Glob, grepai_search]
    targets:
      - "Naming conventions (files, functions, variables)"
      - "Error handling patterns (try/catch, Result, early return)"
      - "Import ordering conventions"
      - "File organization patterns (co-location, barrel exports)"
      - "Hidden dependencies (env vars, config files)"
      - "Configuration patterns (defaults, overrides)"

  2_compare_with_documented:
    action: "Read existing CLAUDE.md files and filter already-documented patterns"
    rule: "Only keep patterns with 3+ occurrences AND not already in CLAUDE.md"
    tools: [Read, Grep]

  3_scope_learnings:
    rules:
      project_wide: "root CLAUDE.md (cross-cutting concerns)"
      package_scope: "package/CLAUDE.md (package-specific conventions)"
      feature_scope: "feature/CLAUDE.md (feature-specific patterns)"
    principle: "Place learning at the narrowest applicable scope"

  4_inject_learnings:
    action: "Append learnings to appropriate CLAUDE.md under '## Learned Conventions' section"
    constraints:
      - "Max 5 learnings per CLAUDE.md per update"
      - "Each learning = 1-2 lines max"
      - "Respect line thresholds (150/200/250/300)"
      - "If threshold exceeded → skip injection, warn user"
    format: "- **{pattern_name}**: {description} ({n} occurrences)"

  output: |
    ═══════════════════════════════════════════════════════════
      /warmup --update - Phase 7.0: Learn
    ═══════════════════════════════════════════════════════════

    Patterns analyzed: <n> source files

    Conventions discovered:
      ├─ {pattern_1} (5 occurrences) → src/CLAUDE.md
      ├─ {pattern_2} (8 occurrences) → CLAUDE.md
      └─ {pattern_3} (3 occurrences) → SKIPPED (already documented)

    Injected: <n> learnings into <n> CLAUDE.md files
    Skipped: <n> (already documented or below threshold)

    ═══════════════════════════════════════════════════════════
```

---

**Final Output (--update Mode):**

```
═══════════════════════════════════════════════════════════════
  /warmup --update - Documentation Updated
═══════════════════════════════════════════════════════════════

  Files analyzed: <n> source files, <n> CLAUDE.md

  Changes applied:
    ✓ /src/CLAUDE.md - Updated structure
    ✓ /src/handlers/CLAUDE.md - Removed obsolete refs
    ○ /tests/CLAUDE.md - Skipped (user choice)

  Obsolete items removed:
    - <obsolete_file> reference
    - <old_function> signature

  New attention points added:
    + <n> TODO items documented
    + <n> FIXME flagged

  GrepAI config:
    ✓ Project-specific exclusions added

  Learned conventions:
    ✓ <n> patterns discovered, <n> injected

  Validation:
    ✓ Line thresholds: 0 FORBIDDEN, 0 CRITICAL, 0 WARNING
    ✓ Structure sections match reality
    ✓ No broken file references

═══════════════════════════════════════════════════════════════
```

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Skip Phase 1 (Peek) | **FORBIDDEN** | Hierarchy discovery is MANDATORY |
| Modify .claude/commands/ | **FORBIDDEN** | Protected files |
| Delete CLAUDE.md | **FORBIDDEN** | Only updates allowed |
| Ignore .gitignore | **FORBIDDEN** | Source of truth for exclusions |
| Create CLAUDE.md in gitignored dir | **FORBIDDEN** | vendor/, node_modules/, etc. |
| CLAUDE.md > 300 lines | **FORBIDDEN** | Must be split |
| CLAUDE.md 251-300 lines | **CRITICAL** | Condensation MANDATORY |
| CLAUDE.md 201-250 lines | **WARNING** | Review recommended |
| Random reading | **FORBIDDEN** | Funnel (root→leaves) MANDATORY |
| Implementation details | **FORBIDDEN** | Context, not code |
| --update without backup | **WARNING** | Risk of loss |

**CLAUDE.md line thresholds:**

```
┌────────────┬─────────┬───────────────────────────────────────┐
│   Level    │ Lines   │             Action                    │
├────────────┼─────────┼───────────────────────────────────────┤
│ IDEAL      │ 0-150   │ No action needed                      │
├────────────┼─────────┼───────────────────────────────────────┤
│ ACCEPTABLE │ 151-200 │ Medium directory, acceptable           │
├────────────┼─────────┼───────────────────────────────────────┤
│ WARNING    │ 201-250 │ Review recommended at next pass        │
├────────────┼─────────┼───────────────────────────────────────┤
│ CRITICAL   │ 251-300 │ Condensation MANDATORY                 │
├────────────┼─────────┼───────────────────────────────────────┤
│ FORBIDDEN  │ 301+    │ Must be split or restructured          │
└────────────┴─────────┴───────────────────────────────────────┘
```

**Threshold justification:**

| Criterion | 250 lines (WARNING) | 300 lines (CRITICAL) |
|-----------|---------------------|----------------------|
| Read time | ~10 min | ~15 min |
| LLM tokens | ~2500 | ~3000 |
| Flexibility | Complex projects OK | Absolute limit |

**When 300+ lines?** → The directory must be split into subdirectories with their own CLAUDE.md.

---

## Workflow Integration

```
/warmup                     # Pre-load context
    ↓
/plan "feature X"           # Plan with context
    ↓
/do                         # Execute the plan
    ↓
/warmup --update            # Update documentation
    ↓
/git --commit               # Commit changes
```

**Integration with other skills:**

| Before /warmup | After /warmup |
|----------------|---------------|
| Container start | /plan, /review, /do |
| /init | Any complex task |

---

## Design Patterns Applied

| Pattern | Category | Usage |
|---------|----------|-------|
| Cache-Aside | Cloud | Check cache before loading |
| Lazy Loading | Performance | Load by phases (funnel) |
| Progressive Disclosure | DevOps | Increasing detail by depth |

**References:**
- `~/.claude/docs/cloud/cache-aside.md`
- `~/.claude/docs/performance/lazy-load.md`
- `~/.claude/docs/devops/feature-toggles.md`
