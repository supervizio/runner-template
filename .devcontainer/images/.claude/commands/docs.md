---
name: docs
description: |
  Documentation Server with Deep Analysis (RLM Multi-Agent).
  Launches N parallel agents to analyze every aspect of the project.
  Scoring mechanism identifies what's important to document.
  Adapts structure based on project type (template vs application).
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "Grep(**/*)"
  - "Write(docs/**)"
  - "Write(mkdocs.yml)"
  - "Write(~/.claude/docs/config.json)"
  - "Task(*)"
  - "Bash(mkdocs:*)"
  - "Bash(cd:*)"
  - "Bash(mkdir:*)"
  - "Bash(kill:*)"
  - "Bash(pgrep:*)"
  - "Bash(pkill:*)"
  - "Bash(curl:*)"
  - "Bash(sleep:*)"
  - "mcp__grepai__grepai_search"
  - "mcp__grepai__grepai_trace_callers"
  - "mcp__grepai__grepai_trace_callees"
  - "mcp__grepai__grepai_trace_graph"
  - "mcp__context7__*"
  - "AskUserQuestion"
---

# /docs - Documentation Server (Deep Analysis)

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Fetch up-to-date API references for libraries used in the project
- Verify framework documentation accuracy before generating docs

Generate and serve **comprehensive** project documentation using MkDocs Material.

**Key Difference:** This skill launches **N parallel analysis agents**, each specialized
for a different aspect (languages, commands, hooks, agents, architecture, etc.).
Results are scored and consolidated into real, useful documentation with Mermaid
diagrams, concrete examples, and progressive architecture zoom.

$ARGUMENTS

---

## Core Principles

```yaml
principles:
  deep_analysis:
    rule: "Launch N agents with context: fork, each writing JSON to /tmp/docs-analysis/"
    iterations: "Phase 4.1: 8 haiku agents parallel, Phase 4.2: 1 sonnet agent with context"
    output: "File-based JSON results with scoring, 1-line summaries in main context"

  no_superficial_content:
    rule: "NEVER list without explaining"
    bad: "Available commands: /git, /review, /plan"
    good: "### /git - Full workflow with phases, arguments, examples"

  product_pitch_first:
    rule: "index.md MUST answer 'What problem does this solve?' before anything technical"
    structure: "Problem → Solution → Key features → Quick start → What's inside → Support"
    reason: "Readers decide in 30 seconds if the project is relevant to them"
    entry_point: "Landing page provides: About, Access, Usage, Resources, Support"

  progressive_zoom:
    rule: "Architecture docs follow Google Maps analogy: macro → micro"
    levels:
      - "Level 1: System context — big blocks, external dependencies"
      - "Level 2: Components — modules, services, their roles"
      - "Level 3: Internal — implementation details, algorithms, data structures"
    reason: "Reader picks the zoom level they need"

  diagrams_mandatory:
    rule: "Every architecture or flow page MUST include at least one Mermaid diagram"
    types: ["flowchart", "sequence", "C4 context", "ER diagram", "state machine"]
    reason: "Visual comprehension is 60,000x faster than text"

  link_dont_copy:
    rule: "Reference source files via links, not inline copies"
    bad: "```yaml\n# Copy of docker-compose.yml\nservices:\n  app: ...\n```"
    good: "See [`docker-compose.yml`](../docker-compose.yml) for full service definition."
    reason: "Copied content desynchronizes immediately"

  project_specific:
    rule: "Every analysis is unique to THIS project"
    reason: "Questions asked for template != questions for app using template"

  scoring_mechanism:
    rule: "Identify what's IMPORTANT to surface"
    criteria:
      - "Complexity (1-10): How complex is this component?"
      - "Usage frequency (1-10): How often will users need this?"
      - "Uniqueness (1-10): How specific to this project?"
      - "Documentation gap (1-10): How underdocumented currently?"
      - "Diagram bonus (+3): complexity >= 7 AND no diagram exists yet"
    thresholds:
      primary: "Score >= 24 → full page + mandatory diagram"
      standard: "Score 16-23 → own page, diagram recommended"
      reference: "Score < 16 → aggregated in reference section"

  adaptive_structure:
    template_project: "How to use, languages, commands, agents, hooks"
    library_project: "API reference, usage examples, integration guides, internal architecture"
    application_project: "Architecture, API, deployment, data flow, cluster, configuration"
```

---

## Arguments

| Argument | Action |
|----------|--------|
| (none) | Freshness check → incremental or full analysis → serve on :8080 |
| `--update` | Force full re-analysis, ignore freshness (regenerate everything) |
| `--serve` | (Re)start server with existing docs (kill + restart, no analysis) |
| `--stop` | Stop running MkDocs server |
| `--status` | Show freshness report, stale pages, server status |
| `--port <n>` | Custom port (default: 8080) |
| `--quick` | Skip analysis entirely, serve existing docs as-is |
| `--help` | Show help |

---

## --help

```
═══════════════════════════════════════════════════════════════
  /docs - Documentation Server (Deep Analysis)
═══════════════════════════════════════════════════════════════

  DESCRIPTION
    Generates comprehensive documentation using multi-agent
    parallel analysis. Each agent specializes in one aspect
    (languages, commands, hooks, architecture, etc.). Results
    are scored and consolidated into rich documentation with
    Mermaid diagrams and progressive architecture zoom.

  USAGE
    /docs [OPTIONS]

  OPTIONS
    (none)              Freshness check + incremental/full + serve
    --update            Force full regeneration (ignore freshness)
    --serve             (Re)start server (kill existing + restart, no analysis)
    --stop              Stop running MkDocs server
    --status            Freshness report + stale pages + server status
    --port <n>          Custom port (default: 8080)
    --quick             Serve existing docs as-is, skip analysis
    --help              Show this help

  ANALYSIS AGENTS (file-based, context: fork)
    Phase 4.1 (8 haiku agents, parallel → /tmp/docs-analysis/):
      languages     install.sh → tools, versions, why
      commands      commands/*.md → workflows, args
      agents        agents/*.md → capabilities
      hooks         lifecycle/*.sh → automation
      mcp           mcp.json → integrations
      patterns      ~/.claude/docs/ → patterns KB
      structure     codebase → directory map
      config        env, settings → configuration
    Phase 4.2 (1 sonnet agent, reads Phase 4.1 results):
      architecture  code → components, flows, protocols

  SCORING (what to document)
    Complexity:     1-10 (how complex?)
    Usage:          1-10 (how often needed?)
    Uniqueness:     1-10 (how project-specific?)
    Gap:            1-10 (how underdocumented?)
    Diagram bonus:  +3 (complexity >= 7, no diagram yet)
    Total >= 24     → Primary (full page + mandatory diagram)
    Total 16-23     → Standard (own page, diagram recommended)
    Total < 16      → Reference (aggregated)

  EXAMPLES
    /docs                   # Freshness check → update stale pages → serve
    /docs --update          # Force full regeneration from scratch
    /docs --serve           # (Re)start server after manual edits or --stop
    /docs --status          # Show what's stale without regenerating
    /docs --quick           # Serve existing docs immediately
    /docs --stop            # Stop server

═══════════════════════════════════════════════════════════════
```

**IF `$ARGUMENTS` contains `--help`**: Display the help above and STOP.

---

## Template Variables

All `{VARIABLE}` placeholders used in output templates and generated files:

```yaml
variables:
  # Derived from project analysis (Phase 2.0-4.0)
  PROJECT_NAME: "From CLAUDE.md title, package.json name, go.mod module, or git repo name"
  PROJECT_TYPE: "template | library | application | empty (detected in Phase 2.0)"
  GENERATED_DESCRIPTION: "2-3 sentence summary synthesized from agent analysis results"

  # Derived from scoring (Phase 5.0)
  SECTIONS_WITH_SCORES: "Formatted list: section name + score, sorted descending"

  # Derived from agent results (Phase 4.0)
  N: "Number of analysis agents that completed successfully"
  D: "Total count of Mermaid diagrams generated across all pages"

  # Derived from git (Phase 2.0)
  GIT_REMOTE_URL: "From git remote get-url origin (for repo_url in mkdocs.yml)"
  REPO_NAME: "Auto-detected from remote URL host (GitHub/GitLab/Bitbucket)"

  # Freshness (Phase 3.0)
  LAST_COMMIT_SHA: "Git SHA from generation marker in docs/index.md"
  MARKER_DATE: "ISO8601 date from generation marker"
  MARKER_COMMIT: "Short SHA from generation marker"
  DAYS_AGO: "Days since last generation"
  COMMITS_SINCE: "Number of commits between marker SHA and HEAD"
  CHANGED_COUNT: "Number of files changed since marker commit"
  STALE_COUNT: "Number of doc pages affected by changed files"
  STALE_LIST: "Formatted list of stale page paths"
  BROKEN_COUNT: "Number of broken internal links in docs/"
  BROKEN_LIST: "Formatted list of broken links with source page"
  OUTDATED_COUNT: "Number of dependency version mismatches"
  OUTDATED_LIST: "Formatted list: dep name, docs version vs actual version"
  TOTAL_PAGES: "Total number of pages in docs/"

  # From Phase 1.0 config (~/.claude/docs/config.json)
  PUBLIC_REPO: "Boolean — controls GitHub links in header/footer/nav and repo_url in mkdocs.yml"
  INTERNAL_PROJECT: "Boolean — controls feature table style (simple vs comparison)"

  # From architecture-analyzer (Phase 4.0, stored in config)
  APIS: "Array of {name, path, method, transport, format, description}"
  API_COUNT: "len(APIS) — controls nav: 0=hidden, 1='API' direct, N='APIs' dropdown"
  TRANSPORTS: "Array of {protocol, direction, port, tls, used_by_apis[]}"
  FORMATS: "Array of {name, content_type, used_by_apis[], deduced: boolean}"
  PROJECT_TAGLINE: "One-sentence tagline synthesized from analysis"

  # Color system (derived from accent_color via color_derivation algorithm)
  ACCENT_HEX: "hex from config accent_color (e.g. '#df41fb')"
  COLOR_PRIMARY_BORDER: "ACCENT_HEX (e.g. '#df41fb')"
  COLOR_PRIMARY_BG: "ACCENT_HEX + '1a' (10% alpha, e.g. '#df41fb1a')"
  COLOR_DATA_BORDER: "triadic left: hsl_to_hex((H-120+360)%360, S, L)"
  COLOR_DATA_BG: "COLOR_DATA_BORDER + '1a' (10% alpha)"
  COLOR_ASYNC_BORDER: "triadic right: hsl_to_hex((H+120)%360, S, L)"
  COLOR_ASYNC_BG: "COLOR_ASYNC_BORDER + '1a' (10% alpha)"
  COLOR_EXTERNAL_BORDER: "'#6c7693' (fixed desaturated gray)"
  COLOR_EXTERNAL_BG: "'#6c76931a' (fixed)"
  COLOR_ERROR_BORDER: "'#e83030' (fixed red)"
  COLOR_ERROR_BG: "'#e830301a' (fixed)"
  COLOR_TEXT: "'#d4d8e0' (constant — light text for dark mode)"
  COLOR_LABEL_BG: "'#1e2129' (constant — slate dark)"
  COLOR_EDGE: "'#d4d8e0' (constant — same as text)"

  # User-configurable
  PORT: "MkDocs serve port (default: 8080, override with --port)"

  # Runtime
  RUNNING: "pgrep -f 'mkdocs serve' returns 0"
  STOPPED: "pgrep -f 'mkdocs serve' returns non-zero"
  TIMESTAMP: "date -Iseconds of last analysis run"
  PERCENTAGE: "(pages_with_content / total_nav_entries) * 100"
```

---

## Color Derivation Algorithm

Given `accent_color` from Phase 1.0 config, derive the full semantic palette:

```yaml
color_derivation:
  input: "ACCENT_HEX from ~/.claude/docs/config.json accent_color"

  algorithm:
    1_parse_hsl: "Convert ACCENT_HEX to HSL (H, S, L)"
    2_primary:
      border: "ACCENT_HEX (unchanged)"
      background: "ACCENT_HEX + '1a' (append 10% alpha suffix)"
    3_data_triadic_left:
      border: "hsl_to_hex((H - 120 + 360) % 360, S, L)"
      background: "data_border + '1a'"
    4_async_triadic_right:
      border: "hsl_to_hex((H + 120) % 360, S, L)"
      background: "async_border + '1a'"
    5_fixed_roles:
      external: { border: "#6c7693", background: "#6c76931a" }
      error: { border: "#e83030", background: "#e830301a" }
    6_constants:
      text: "#d4d8e0"
      label_bg: "#1e2129"
      edge: "#d4d8e0"

  preset_table:
    "#9D76FB":  { data: "#76fb9d", async: "#fb9d76" }  # Purple (default)
    "#6BA3FF":  { data: "#a3ff6b", async: "#ff6ba3" }  # Blue
    "#4DD0E1":  { data: "#d0e14d", async: "#e14dd0" }  # Teal
    "#66BB6A":  { data: "#bb6a66", async: "#6a66bb" }  # Green
    "#FFB74D":  { data: "#b74dff", async: "#4dffb7" }  # Orange

  semantic_mapping:
    Person: "primary"
    System: "primary"
    Container: "primary"
    Component: "primary"
    System_Ext: "external"
    Person_Ext: "external"
    ContainerDb: "data"
    ComponentDb: "data"
    ContainerQueue: "async"
    ComponentQueue: "async"
    Deployment_Node: "external (border only, fill #2d2d2d)"

  application_layers:
    css_theme: "theme.css.tpl → stylesheets/theme.css (MkDocs + C4 global)"
    init_block: "%%{init}%% directive in flowchart/sequence/state diagrams"
    classDef: "classDef declarations in flowcharts for semantic node roles"
    UpdateElementStyle: "Per-element inline in C4 diagrams (belt-and-suspenders with CSS)"
```

---

## Architecture Overview

```
/docs Execution Flow
────────────────────────────────────────────────────────────────

Phase 1.0: Configuration Gate
├─ Read ~/.claude/docs/config.json
├─ If missing/incomplete: ask 3 mandatory questions (AskUserQuestion)
│   ├─ Q1: "Is this repository public?"  → public_repo
│   ├─ Q2: "Is this an internal project?" → internal_project
│   └─ Q3: "Choose your accent color"    → accent_color
├─ Persist answers to ~/.claude/docs/config.json
├─ Derive semantic color palette from accent_color (triadic HSL)
└─ Load config into template variables (PUBLIC_REPO, INTERNAL_PROJECT, ACCENT_COLOR)

Phase 2.0: Project Detection
├─ Detect project type (template/library/app/empty)
└─ Choose analysis strategy + agent list

Phase 3.0: Freshness Check
├─ Read generation marker from docs/index.md
├─ git diff <last_sha>..HEAD → changed files
├─ Map changed files → stale doc pages
├─ Check broken links + outdated deps
└─ Decision: INCREMENTAL (stale pages only) or FULL

Phase 4.1: Category Analyzers (8 haiku agents, ONE message)
├─ Task(docs-analyzer-languages)   ──┐
├─ Task(docs-analyzer-commands)    ──┤
├─ Task(docs-analyzer-agents)      ──┤
├─ Task(docs-analyzer-hooks)       ──┤ ALL PARALLEL
├─ Task(docs-analyzer-mcp)         ──┤ → /tmp/docs-analysis/*.json
├─ Task(docs-analyzer-patterns)    ──┤
├─ Task(docs-analyzer-structure)   ──┤
└─ Task(docs-analyzer-config)      ──┘

Phase 4.2: Architecture Analyzer (1 sonnet agent, reads Phase 4.1)
└─ Task(docs-analyzer-architecture) → /tmp/docs-analysis/architecture.json

Phase 5.0: Consolidation + Scoring
├─ Read all JSON from /tmp/docs-analysis/
├─ Build dependency DAG, topological sort
├─ Apply scoring formula (with diagram bonus)
├─ Identify high-priority sections
└─ Build documentation tree

Phase 6.0: Content Generation (dependency order)
├─ Generate index.md (product pitch first)
├─ For each scored section:
│   ├─ If score >= 24: Primary — full page + mandatory diagram
│   ├─ If score 16-23: Standard — own page, diagram recommended
│   └─ If score < 16: Reference — aggregated in reference section
├─ Generate architecture pages (C4 progressive zoom)
└─ Generate nav structure

Phase 7.0: Verification (DocAgent-inspired)
├─ Verify: completeness, accuracy, quality, no placeholders
├─ Feedback loop: fix issues and re-verify (max 2 iterations)
└─ Proceed with warnings if max iterations reached

Phase 8.0: Serve
├─ Final checks
└─ Start MkDocs on specified port
```

---

## Phase 1.0: Configuration Gate

```yaml
phase_1_0_config:
  description: "Mandatory configuration gate — runs before any analysis"
  mandatory: true
  skip_if: "~/.claude/docs/config.json exists AND contains all keys (public_repo, internal_project, accent_color)"

  config_file: "~/.claude/docs/config.json"
  config_schema:
    public_repo: "boolean — controls GitHub links, repo_url, footer icon, nav GitHub tab"
    internal_project: "boolean — controls feature table style (simple description vs competitive comparison)"
    accent_color: "hex string — accent color for MkDocs theme and Mermaid diagrams (e.g. '#df41fb')"
    apis: "array — auto-filled by architecture-analyzer in Phase 4.0 (never asked to user)"

  workflow:
    1_check_existing:
      action: "Read ~/.claude/docs/config.json"
      if_exists_and_complete:
        action: "Load config into template variables, skip to Phase 2.0"
        message: "Config loaded: public_repo={public_repo}, internal_project={internal_project}"
      if_missing_or_incomplete:
        action: "Proceed to questions"

    2_ask_questions:
      tool: "AskUserQuestion"
      questions:
        - question: "Is this repository public?"
          header: "Visibility"
          options:
            - label: "Public"
              description: "GitHub links visible in header, footer, and nav"
            - label: "Private"
              description: "No GitHub links exposed, no repo URL in documentation"
          persist_as: "public_repo (Public → true, Private → false)"

        - question: "Is this an internal project?"
          header: "Audience"
          options:
            - label: "Internal"
              description: "Simple feature table (Feature | Description), no competitor comparison"
            - label: "External"
              description: "Competitive comparison table (Us vs Competitors) with ✅/⚠️/❌"
          persist_as: "internal_project (Internal → true, External → false)"

        - question: "Choose your documentation accent color"
          header: "Theme Color"
          options:
            - label: "Purple (Recommended)"
              description: "#9D76FB — Material dark-theme purple, elegant on slate"
            - label: "Blue"
              description: "#6BA3FF — professional, tech-forward"
            - label: "Teal"
              description: "#4DD0E1 — calm, data-centric"
            - label: "Green"
              description: "#66BB6A — growth, reliability"
            - label: "Orange"
              description: "#FFB74D — energetic, action-oriented"
          persist_as: "accent_color (hex string from option description, or custom hex if 'Other')"

    3_persist:
      action: "Write ~/.claude/docs/config.json"
      content: |
        {
          "public_repo": {Q1_ANSWER},
          "internal_project": {Q2_ANSWER},
          "accent_color": "{Q3_ANSWER}",
          "apis": []
        }
      note: "apis array populated automatically by architecture-analyzer in Phase 4.0"

  output_variables:
    PUBLIC_REPO: "boolean from config → controls repo_url, GitHub nav tab, footer link"
    INTERNAL_PROJECT: "boolean from config → controls index.md feature table style"
    ACCENT_COLOR: "hex string from config → input for color derivation algorithm"

  conditional_effects:
    public_repo_false:
      - "mkdocs.yml: no repo_url, no repo_name, no edit_uri"
      - "mkdocs.yml: no icon.repo"
      - "mkdocs.yml: no GitHub tab in nav"
      - "mkdocs.yml: no extra.social GitHub link"
      - "index.md: no GitHub link in footer"
      - "Comparison table: no 'Open Source' row"
    internal_project_true:
      - "index.md: simple Feature | Description table"
      - "No competitor research needed"
      - "No comparison table generation"
    internal_project_false:
      - "index.md: comparison table Us ★ | Compet A | Compet B | Compet C"
      - "Phase 4.0 agents research competitors for the comparison"
      - "Comparison uses ✅ (full) | ⚠️ (partial) | ❌ (none)"
```

---

## Phase 2.0: Project Detection

```yaml
phase_2_0_detect:
  description: "Identify project type and handle existing docs/"
  mandatory: true

  existing_docs_handling:
    check: "ls docs/ 2>/dev/null"
    decision:
      if_mkdocs_generated:
        signal: "docs/ contains mkdocs-generated content (index.md with '<!-- generated by /docs -->')"
        action: "Overwrite — regenerate all content"
        message: "Previous /docs output detected. Regenerating..."
      if_user_content:
        signal: "docs/ contains files without generation marker (from /init or manual)"
        action: "Preserve user files in docs/_preserved/, generate around them"
        message: "Existing documentation found. Preserving user content in docs/_preserved/."
      if_empty_or_missing:
        action: "Create docs/ fresh"

  detection_signals:
    template_project:
      patterns:
        - ".devcontainer/features/**/install.sh"
        - ".devcontainer/images/.claude/"
        - ".claude/commands/*.md"
      anti_patterns:
        - "src/**/*.{go,py,ts,rs,java,rb,php}"
      result: "PROJECT_TYPE=template"

    library_project:
      patterns:
        - "{package.json,go.mod,Cargo.toml,pyproject.toml}"
        - "src/**/*.{go,py,ts,rs}"
        - "{lib,pkg,src}/**/*"
      anti_patterns:
        - "**/openapi.{yaml,yml,json}"
        - "**/routes/**"
      result: "PROJECT_TYPE=library"

    application_project:
      patterns:
        - "src/**/*.{go,py,ts,rs}"
        - "**/openapi.{yaml,yml,json}"
        - "{cmd,app,server,api}/**/*"
      result: "PROJECT_TYPE=application"

    empty_project:
      patterns:
        - "Only CLAUDE.md and basic files"
      result: "PROJECT_TYPE=empty"

  output:
    project_type: "template | library | application | empty"
    analysis_agents: "[list of agents to launch based on type]"
```

---

## Phase 3.0: Freshness Check

```yaml
phase_3_0_freshness:
  description: "Detect stale docs and decide incremental vs full regeneration"
  skip_if: "--update flag (force full) OR no docs/ exists (first run)"

  generation_marker:
    location: "First line of docs/index.md"
    format: "<!-- /docs-generated: {JSON} -->"
    fields:
      date: "ISO8601 timestamp of last generation"
      commit: "Git SHA at time of generation"
      pages: "Number of pages generated"
      agents: "Number of agents used"
    example: '<!-- /docs-generated: {"date":"2026-02-06T14:30:00Z","commit":"abc1234","pages":12,"agents":9} -->'

  freshness_checks:
    1_code_drift:
      command: "git diff --name-only {marker.commit}..HEAD"
      output: "List of files changed since last generation"
      mapping: |
        For each changed file, find doc pages that reference it:
        - Grep docs/*.md for the filename
        - Mark matching pages as STALE

    2_broken_links:
      action: |
        For each relative link in docs/*.md:
          Check if target file exists on disk
        For each code path mentioned in docs:
          Check if the path still exists
      output: "List of broken internal links"

    3_outdated_deps:
      action: |
        Compare versions mentioned in docs vs actual:
        - package.json dependencies vs docs mentions
        - go.mod versions vs docs mentions
        - Cargo.toml versions vs docs mentions
        - install.sh versions vs docs mentions
      output: "List of version mismatches"

    4_dead_external_links:
      action: |
        For each external URL in docs/*.md:
          curl -s -o /dev/null -w "%{http_code}" <url>
          → 404 = DEAD, 301 = MOVED, 200 = OK
      output: "List of dead/moved external links"
      note: "Only check if < 50 external links (avoid rate limiting)"

  decision:
    if_no_marker:
      action: "FULL generation (first run)"
    if_zero_stale:
      action: "SKIP analysis, serve existing docs"
      message: "Docs are up to date (last generated {date}, {commits} commits, 0 stale)."
    if_stale_pages:
      action: "INCREMENTAL — only re-analyze and regenerate stale pages"
      optimization: |
        Only launch agents whose scope covers the changed files:
        - src/ changed → architecture-analyzer
        - commands/ changed → commands-analyzer
        - hooks/ changed → hooks-analyzer
        - package.json changed → config-analyzer + dependencies
        - etc.
    if_update_flag:
      action: "FULL generation regardless of freshness"

  output_template: |
    ═══════════════════════════════════════════════════════════════
      /docs - Freshness Check
    ═══════════════════════════════════════════════════════════════

      Last generated : {MARKER_DATE} ({DAYS_AGO} days ago)
      Last commit    : {MARKER_COMMIT} → HEAD ({COMMITS_SINCE} commits)

      Code drift:
        Changed files  : {CHANGED_COUNT}
        Stale pages    : {STALE_COUNT} / {TOTAL_PAGES}
        {STALE_LIST}

      Broken links   : {BROKEN_COUNT}
        {BROKEN_LIST}

      Outdated deps  : {OUTDATED_COUNT}
        {OUTDATED_LIST}

      Decision: {INCREMENTAL|FULL|UP_TO_DATE}
        → {ACTION_DESCRIPTION}

    ═══════════════════════════════════════════════════════════════
```


---

## Phase 4.0: Parallel Analysis Agents (File-Based Dispatch)

**Architecture:** Each analyzer is a separate agent file in `.claude/agents/docs-analyzer-*.md`
with `context: fork` (isolated context) and file-based output to `/tmp/docs-analysis/`.
This prevents context saturation — each agent writes JSON results to disk and returns
a 1-line summary to the main context.

**INCREMENTAL MODE:** Only launch agents whose scope covers stale pages.

### Setup

Create output directory before launching agents:

```bash
mkdir -p /tmp/docs-analysis
```

### Phase 4.1: Category Analyzers (8 parallel haiku agents)

**CRITICAL:** Launch ALL 8 agents in a SINGLE message with multiple Task calls.

```yaml
phase_4_1_dispatch:
  agents:
    - subagent_type: "docs-analyzer-languages"
      max_turns: 12
      prompt: "Analyze language features. Write JSON to /tmp/docs-analysis/languages.json."
      trigger: "PROJECT_TYPE in [template, library, application]"

    - subagent_type: "docs-analyzer-commands"
      max_turns: 12
      prompt: "Analyze Claude commands/skills. Write JSON to /tmp/docs-analysis/commands.json."
      trigger: "Always"

    - subagent_type: "docs-analyzer-agents"
      max_turns: 12
      prompt: "Analyze specialist agents. Write JSON to /tmp/docs-analysis/agents.json."
      trigger: "PROJECT_TYPE == template OR .claude/agents/ exists"

    - subagent_type: "docs-analyzer-hooks"
      max_turns: 12
      prompt: "Analyze lifecycle and Claude hooks. Write JSON to /tmp/docs-analysis/hooks.json."
      trigger: "PROJECT_TYPE == template OR .devcontainer/hooks/ exists"

    - subagent_type: "docs-analyzer-mcp"
      max_turns: 10
      prompt: "Analyze MCP server configuration. Write JSON to /tmp/docs-analysis/mcp.json."
      trigger: "mcp.json exists"

    - subagent_type: "docs-analyzer-patterns"
      max_turns: 10
      prompt: "Analyze design patterns KB. Write JSON to /tmp/docs-analysis/patterns.json."
      trigger: "~/.claude/docs/ exists"

    - subagent_type: "docs-analyzer-structure"
      max_turns: 10
      prompt: "Map project structure. Write JSON to /tmp/docs-analysis/structure.json."
      trigger: "Always"

    - subagent_type: "docs-analyzer-config"
      max_turns: 10
      prompt: "Analyze configuration and env vars. Write JSON to /tmp/docs-analysis/config.json."
      trigger: "Always"

  output: "Each agent writes JSON to /tmp/docs-analysis/{name}.json"
  return: "Each agent returns 1-line: 'DONE: {name} - N items, score X/10'"
  wait: "ALL Phase 4.1 agents must complete before Phase 4.2"
```

### Phase 4.2: Architecture Analyzer (1 sonnet agent)

**Runs AFTER Phase 4.1 completes.** The architecture analyzer reads Phase 4.1 JSON results
from `/tmp/docs-analysis/` to gain project context before performing deep analysis.

```yaml
phase_4_2_dispatch:
  agent:
    subagent_type: "docs-analyzer-architecture"
    max_turns: 20
    prompt: |
      Deep architecture analysis. Phase 4.1 results are available in
      /tmp/docs-analysis/*.json — read them first for project context.
      Write your results to /tmp/docs-analysis/architecture.json.
    trigger: "PROJECT_TYPE in [library, application] OR src/ exists"

  output: "/tmp/docs-analysis/architecture.json"
  return: "1-line: 'DONE: architecture - N components, M APIs, score X/10'"
```

### Agent File Reference

| Agent File | Model | Max Turns | Scope |
|------------|-------|-----------|-------|
| `docs-analyzer-languages.md` | haiku | 12 | `.devcontainer/features/languages/` |
| `docs-analyzer-commands.md` | haiku | 12 | `.claude/commands/` |
| `docs-analyzer-agents.md` | haiku | 12 | `.claude/agents/` |
| `docs-analyzer-hooks.md` | haiku | 12 | `.devcontainer/hooks/` |
| `docs-analyzer-mcp.md` | haiku | 10 | `mcp.json`, `mcp.json.tpl` |
| `docs-analyzer-patterns.md` | haiku | 10 | `~/.claude/docs/` |
| `docs-analyzer-structure.md` | haiku | 10 | Project root (depth 3) |
| `docs-analyzer-config.md` | haiku | 10 | `.env`, `devcontainer.json`, `docker-compose.yml` |
| `docs-analyzer-architecture.md` | sonnet | 20 | `src/`, APIs, data flows, C4 diagrams |

### Output Format

All agents write to `/tmp/docs-analysis/{name}.json` with structure:

```json
{
  "agent": "{name}",
  "...": "agent-specific data",
  "scoring": {"complexity": 7, "usage": 9, "uniqueness": 8, "gap": 6},
  "summary": "One-line summary"
}
```

---

## Phase 5.0: Consolidation and Scoring

```yaml
phase_5_0_consolidation:
  description: "Merge agent results and apply enhanced scoring"

  scoring_formula:
    base: "complexity + usage + uniqueness + gap"
    diagram_bonus: "+3 if complexity >= 7 AND no diagram exists yet"
    total_max: 43
    thresholds:
      primary: ">= 24 (full page + mandatory Mermaid diagram)"
      standard: "16-23 (own page, diagram recommended)"
      reference: "< 16 (aggregated in reference section)"

  diagram_requirement:
    rule: |
      IF score >= 24 AND component is architectural:
        MUST include at least one Mermaid diagram
      IF score >= 24 AND component has data flow:
        MUST include sequence or flowchart diagram
      IF cluster/scaling detected:
        MUST include deployment diagram

  # DocAgent-inspired: dependencies-first ordering ensures components are
  # documented only after their dependencies have been processed.
  dependency_ordering:
    rule: "Topological sort of component dependencies before content generation"
    reason: "A module's docs can reference its dependency's docs via links"
    implementation:
      - "Build dependency DAG from agent results (imports, calls, data flow)"
      - "Topological sort → processing order for Phase 6.0"
      - "Earlier components provide context for later ones"

  consolidation_steps:
    1_collect:
      action: "Read all JSON files from /tmp/docs-analysis/*.json"

    2_deduplicate:
      action: "Merge overlapping information (structure + architecture)"

    3_score:
      action: "Calculate total score per component with diagram bonus"

    4_prioritize:
      action: "Sort by score descending, then by dependency order"

    5_identify_diagrams:
      action: "For each primary section, determine required diagram types"

    5b_cross_link_transport_api:
      action: |
        Build cross-reference maps between APIs and Transports:
        - For each API: resolve its transport protocol and exchange format
        - For each Transport: list all APIs that use it
        - For each Format: list all APIs that use it
        These maps drive the "Used by" columns in transport.md
        and the "Transport/Format" columns in api/overview.md

    5c_persist_apis:
      action: |
        Update ~/.claude/docs/config.json apis array with detected APIs:
        Read existing config → merge apis field → write back.
        This enables subsequent incremental runs to skip full API detection.

    6_structure:
      action: "Build documentation tree adapted to PROJECT_TYPE"

  output_structure:
    common:
      - "index.md (always — hero + conditional features)"
      - "transport.md (always — auto-detected protocols and formats)"
      - "api/ (conditional: only if API_COUNT > 0)"
      - "architecture/ (if application/library, primary: score >= 24)"
    template:
      - "getting-started/ (primary: score >= 24)"
      - "languages/ (primary: score >= 24)"
      - "commands/ (primary: score >= 24)"
      - "agents/ (standard: score >= 16)"
      - "automation/ (hooks + mcp, standard: score >= 16)"
      - "patterns/ (if KB exists, standard: score >= 16)"
      - "reference/ (aggregated: score < 16)"
    application:
      - "architecture/ (always for app)"
      - "api/ (if endpoints detected)"
      - "deployment/ (if cluster/docker detected)"
      - "guides/ (standard: score >= 16)"
      - "reference/ (aggregated: score < 16)"
    library:
      - "architecture/ (if complex internal structure)"
      - "api/ (always for library)"
      - "examples/ (standard: score >= 16)"
      - "guides/ (standard: score >= 16)"
      - "reference/ (aggregated: score < 16)"
```

---

## Phase 6.0: Content Generation

```yaml
phase_6_0_generate:
  description: "Generate documentation from consolidated results"

  rules:
    no_placeholders:
      - "NEVER write 'Coming Soon'"
      - "NEVER write 'TBD' or 'TODO'"
      - "NEVER create empty sections"

    content_requirements:
      - "Every page must have real content from agent analysis"
      - "Every code block must be functional"
      - "Every table must have data"
      - "Every architecture page must have at least one Mermaid diagram"
      - "Every flow description must have a sequence or flowchart diagram"

    link_not_copy:
      - "Reference source files via relative links"
      - "NEVER copy entire config files inline"
      - "Quote only the relevant excerpt (max 15 lines) with link to full file"

    editorial_rules:
      - "No generic filler: 'This module handles X' → explain HOW it handles X"
      - "Every section must contain information extractable ONLY from this project"
      - "Prefer 'The auth module exposes /login and /logout, uses JWT stored in Redis'"
      - "Over 'The auth module manages authentication'"

  #---------------------------------------------------------------------------
  # DOCUMENTATION PHILOSOPHY (Divio System)
  #---------------------------------------------------------------------------
  # Every page falls into one of four categories (never mix them):
  #   Tutorial    → learning-oriented, practical steps for beginners
  #   How-to      → task-oriented, steps for working developers
  #   Reference   → factual, structured lookup during active work
  #   Explanation → theoretical, conceptual understanding
  # Maintaining clear boundaries prevents "gravitational pull" toward
  # merging types, which degrades both author and reader experience.
  #---------------------------------------------------------------------------

  #---------------------------------------------------------------------------
  # UNIVERSAL TEMPLATES (applied to all project types)
  #---------------------------------------------------------------------------
  universal_templates:

    index_md:
      description: "Hero landing page with conditional feature section"
      generation_marker:
        first_line: '<!-- /docs-generated: {"date":"{TIMESTAMP}","commit":"{LAST_COMMIT_SHA}","pages":{TOTAL_PAGES},"agents":{N}} -->'
        rule: "ALWAYS insert as first line of index.md — enables freshness detection"
      structure:
        - "<!-- /docs-generated: {JSON_MARKER} -->"
        - "# {PROJECT_NAME}"
        - "{PROJECT_TAGLINE} — bold, one sentence"
        - "[ Get Started → ] button linking to #how-it-works anchor"
        - ""
        - "## Features (conditional on INTERNAL_PROJECT)"
        - "IF INTERNAL_PROJECT == true:"
        - "  Simple table: Feature | Description"
        - "  List all detected features with one-line descriptions"
        - "IF INTERNAL_PROJECT == false:"
        - "  Comparison table: Feature | {PROJECT_NAME} ★ | Competitor A | B | C"
        - "  Each cell: ✅ full support | ⚠️ partial | ❌ not available"
        - "  Include Price row"
        - "  Include Open Source row ONLY IF PUBLIC_REPO == true"
        - "  Competitors identified by agent analysis (contextually relevant)"
        - ""
        - "## How it works"
        - "{Mermaid flowchart: high-level system overview}"
        - "{2-3 sentences explaining the diagram}"
        - ""
        - "## Quick Start"
        - "{3-5 numbered steps to get running}"
        - ""
        - "--- footer ---"
        - "{PROJECT_NAME} · {LICENSE}"
        - "IF PUBLIC_REPO == true: · GitHub ↗ link to {GIT_REMOTE_URL}"
      conditional_rules:
        public_repo_false:
          - "No GitHub link in footer"
          - "No 'Open Source' row in comparison table"
        internal_project_true:
          - "Use simple Feature | Description table"
          - "No competitor columns, no comparison research"
        internal_project_false:
          - "Use comparison table with up to 3 competitors"
          - "Competitors contextually researched by agents"
      anti_patterns:
        - "Starting with technical details before the pitch"
        - "Listing features without explaining their benefit"
        - "Quick start that requires more than 5 steps"
        - "GitHub link when PUBLIC_REPO is false"
        - "Comparison table when INTERNAL_PROJECT is true"

    #---------------------------------------------------------------------------
    # C4 ARCHITECTURE TEMPLATES (Mermaid C4 diagrams)
    #---------------------------------------------------------------------------
    # Templates: .devcontainer/images/.claude/templates/docs/architecture/
    # Theme: docs/stylesheets/theme.css (derived from theme.css.tpl + accent_color)
    #
    # DECISION FRAMEWORK — which C4 levels to generate:
    #   ALWAYS: Level 1 (Context) + Level 2 (Container)
    #   CONDITIONAL: Level 3 (Component) — only if container has >5 modules
    #   CONDITIONAL: Dynamic — only for critical flows (max 3)
    #   CONDITIONAL: Deployment — only if infra signals detected
    #   NEVER: Level 4 (Code) — use IDE tools instead
    #
    # ELEMENT LIMITS:
    #   - Max 15 elements per diagram (split if more)
    #   - Every relationship has protocol label ("JSON/HTTPS", "JDBC")
    #   - Title format: "[Type] — {PROJECT_NAME}"
    #   - UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
    #
    # CROSS-LINKING with Transport page:
    #   - Container table Transport/Format columns link to transport.md#{anchor}
    #   - Communication Map links to transport.md for protocol details
    #---------------------------------------------------------------------------

    architecture_hub_md:
      description: "C4 hub page — progressive zoom navigation"
      template: "architecture/README.md.tpl"
      structure:
        - "# Architecture"
        - "Progressive zoom table: Level | Diagram | Audience | Focus"
        - "Mermaid legend diagram showing C4 element types"
        - "Links to context, container, component, dynamic, deployment"

    c4_context_md:
      description: "C4 Level 1 — System Context"
      condition: "ALWAYS generated"
      template: "architecture/c4-context.md.tpl"
      diagram_type: "C4Context"
      structure:
        - "# System Context"
        - "C4Context Mermaid diagram: Person, System, System_Ext, Rel"
        - "Key Interactions table: From | To | Protocol | Purpose"
        - "External Dependencies table: System | Type | Purpose | Criticality"
      rules:
        - "Exactly ONE internal System element (the project)"
        - "Every Rel has protocol label"
        - "Max 15 elements"

    c4_container_md:
      description: "C4 Level 2 — Container Diagram"
      condition: "ALWAYS generated"
      template: "architecture/c4-container.md.tpl"
      diagram_type: "C4Container"
      structure:
        - "# Container Diagram"
        - "C4Container Mermaid: System_Boundary, Container, ContainerDb, ContainerQueue"
        - "Containers table: Container | Technology | Responsibility | Transport | Format"
        - "Data Stores table: Store | Technology | Purpose | Access Pattern"
        - "Communication Map: Source | Destination | Protocol | Format | Direction"
      rules:
        - "All containers inside System_Boundary"
        - "Every container has Technology specified"
        - "Transport/Format columns link to transport.md"
        - "Integrate deployment details (don't create separate diagram unless complex)"

    c4_component_md:
      description: "C4 Level 3 — Component Diagram (conditional)"
      condition: "Container has >5 significant modules AND is critical path"
      template: "architecture/c4-component.md.tpl"
      diagram_type: "C4Component"
      structure:
        - "One section per qualifying container"
        - "C4Component Mermaid: Container_Boundary, Component, ComponentDb"
        - "Components table: Component | Technology | Responsibility | Key Files"
        - "Design Patterns table: Pattern | Where | Why"
      rules:
        - "Max 12 components per diagram"
        - "Focus on what's hard to discover from code"
        - "Reference ~/.claude/docs/ patterns when applicable"

    c4_dynamic_md:
      description: "C4 Dynamic — Critical flow diagrams"
      condition: "Critical user journeys or complex data flows detected"
      template: "architecture/c4-dynamic.md.tpl"
      diagram_type: "C4Dynamic"
      structure:
        - "One C4Dynamic per critical flow (max 3 flows)"
        - "Flow Steps table: Step | From | To | Action | Protocol"
        - "Error Scenarios table: Step | Condition | Response | HTTP Code"
      rules:
        - "Max 10 steps per flow"
        - "Number steps in Rel labels: '1. Submit credentials'"
        - "Show error/failure paths for critical flows"
        - "Statement order determines sequence (Mermaid ignores RelIndex)"

    c4_deployment_md:
      description: "C4 Deployment — Infrastructure topology"
      condition: "Deployment signals detected (docker-compose replicas, K8s, Terraform)"
      template: "architecture/c4-deployment.md.tpl"
      diagram_type: "C4Deployment"
      structure:
        - "C4Deployment Mermaid: Deployment_Node (nested), Container, ContainerDb"
        - "Infrastructure table: Node | Type | Spec | Containers"
        - "Scaling Strategy table: Aspect | Strategy | Details"
        - "Network table: Source | Destination | Port | Protocol | TLS"
        - "Recommended Configuration: Scenario | Nodes | CPU | RAM | Storage"
      rules:
        - "Max 3 nesting levels for Deployment_Node"
        - "Production environment only (not dev/staging)"
        - "Include replica counts"

  #---------------------------------------------------------------------------
  # MERMAID COLOR DIRECTIVES (non-C4 diagrams)
  #---------------------------------------------------------------------------
  # C4 diagrams are styled by theme.css (CSS) + UpdateElementStyle (inline).
  # Non-C4 diagrams (flowchart, sequence, state) need %%{init}%% + classDef.
  #---------------------------------------------------------------------------
  mermaid_color_directives:
    applies_to:
      - "flowchart"
      - "sequenceDiagram"
      - "stateDiagram-v2"
    does_NOT_apply_to:
      - "C4Context"
      - "C4Container"
      - "C4Component"
      - "C4Dynamic"
      - "C4Deployment"

    init_block: |
      %%{init: {'theme': 'dark', 'themeVariables': {
        'primaryColor': '{{COLOR_PRIMARY_BG}}',
        'primaryBorderColor': '{{COLOR_PRIMARY_BORDER}}',
        'primaryTextColor': '{{COLOR_TEXT}}',
        'lineColor': '{{COLOR_EDGE}}',
        'textColor': '{{COLOR_TEXT}}',
        'secondaryColor': '{{COLOR_DATA_BG}}',
        'secondaryBorderColor': '{{COLOR_DATA_BORDER}}',
        'secondaryTextColor': '{{COLOR_TEXT}}',
        'tertiaryColor': '{{COLOR_ASYNC_BG}}',
        'tertiaryBorderColor': '{{COLOR_ASYNC_BORDER}}',
        'tertiaryTextColor': '{{COLOR_TEXT}}',
        'noteBkgColor': '{{COLOR_LABEL_BG}}',
        'noteTextColor': '{{COLOR_TEXT}}',
        'noteBorderColor': '{{COLOR_EXTERNAL_BORDER}}',
        'actorBkg': '{{COLOR_PRIMARY_BG}}',
        'actorBorder': '{{COLOR_PRIMARY_BORDER}}',
        'actorTextColor': '{{COLOR_TEXT}}',
        'activationBkgColor': '{{COLOR_PRIMARY_BG}}',
        'activationBorderColor': '{{COLOR_PRIMARY_BORDER}}',
        'signalColor': '{{COLOR_EDGE}}',
        'signalTextColor': '{{COLOR_TEXT}}'
      }}}%%

    classDef_block: |
      classDef primary fill:{{COLOR_PRIMARY_BG}},stroke:{{COLOR_PRIMARY_BORDER}},color:{{COLOR_TEXT}}
      classDef data fill:{{COLOR_DATA_BG}},stroke:{{COLOR_DATA_BORDER}},color:{{COLOR_TEXT}}
      classDef async fill:{{COLOR_ASYNC_BG}},stroke:{{COLOR_ASYNC_BORDER}},color:{{COLOR_TEXT}}
      classDef external fill:{{COLOR_EXTERNAL_BG}},stroke:{{COLOR_EXTERNAL_BORDER}},color:{{COLOR_TEXT}}
      classDef error fill:{{COLOR_ERROR_BG}},stroke:{{COLOR_ERROR_BORDER}},color:{{COLOR_TEXT}}

    usage_rules:
      - "Every flowchart MUST start with the %%{init}%% block"
      - "Every flowchart MUST include classDef declarations"
      - "Assign semantic classes to nodes: A:::primary, B:::data, C:::async"
      - "Sequence and state diagrams need only %%{init}%% (no classDef)"
      - "The OVERVIEW_DIAGRAM in index.md MUST follow these rules"

    c4_inline_rules:
      - "Every C4 diagram MUST include UpdateElementStyle for each element"
      - "Mapping: Person/System/Container/Component → primary colors"
      - "Mapping: *Db → data colors, *Queue → async colors"
      - "Mapping: *_Ext → external colors"
      - "Mapping: error flows → error colors (in C4Dynamic)"
      - "Template: UpdateElementStyle(alias, $fontColor=\"{{COLOR_TEXT}}\", $bgColor=\"{{COLOR_*_BG}}\", $borderColor=\"{{COLOR_*_BORDER}}\")"
      - "Template: UpdateRelStyle(from, to, $textColor=\"{{COLOR_TEXT}}\", $lineColor=\"{{COLOR_EDGE}}\")"

  #---------------------------------------------------------------------------
  # PROJECT-TYPE SPECIFIC STRUCTURES
  #---------------------------------------------------------------------------
  generation_by_project_type:

    template:
      structure:
        index.md: "Product pitch: what this template provides, key features, quick start"
        getting-started/:
          README.md: "Installation methods (template, one-liner, manual)"
          workflow.md: "Feature development workflow with diagram"
          configuration.md: "Environment setup, tokens, MCP config"
        architecture/:
          README.md: "System context: DevContainer + Claude + MCP ecosystem"
          components.md: "Features, hooks, agents, commands — how they connect"
          flow.md: "Container lifecycle flow with sequence diagram"
        languages/:
          README.md: "Overview of all languages with comparison table"
          "{lang}.md": "One page per language: tools, linters, versions, why"
        commands/:
          README.md: "All commands overview with when-to-use decision tree"
          "{cmd}.md": "Full command doc: phases, args, examples, diagrams"
        agents/:
          README.md: "Agent ecosystem: orchestrators → specialists → executors"
          language-specialists.md: "All language agents with capabilities"
          devops-specialists.md: "All DevOps agents with domains"
          executors.md: "All executor agents with analysis types"
        automation/:
          README.md: "Automation overview: hooks + MCP + pre-commit"
          hooks.md: "All lifecycle hooks with execution order diagram"
          mcp-servers.md: "All MCP integrations with tools and auth"
        patterns/:
          README.md: "Design patterns KB: categories, counts, usage"
          by-category.md: "Patterns organized by category with links"
        reference/:
          conventions.md: "Coding conventions, commit format, branch naming"
          troubleshooting.md: "Common issues and solutions"

    library:
      structure:
        index.md: "Product pitch: what this library does, install, basic example"
        architecture/:
          README.md: "System context: library boundary and dependencies"
          components.md: "Internal module breakdown with diagram"
          flow.md: "Data flow through the library with sequence diagram"
        api/:
          README.md: "API overview: main types, functions, interfaces"
          "{module}.md": "Per-module: exported API, parameters, return types, examples"
        examples/:
          README.md: "Example index with difficulty levels"
          "{example}.md": "Each example: problem, solution, code, explanation"
        guides/:
          installation.md: "Installation and setup"
          usage.md: "Usage patterns and best practices"
          migration.md: "Version migration guide (if applicable)"

    application:
      structure:
        index.md: "Product pitch: what this app does, who it's for, quick start"
        architecture/:
          README.md: "Level 1: system context with C4 diagram"
          components.md: "Level 2: component breakdown with internal diagrams"
          flow.md: "Data flows with sequence diagrams per major flow"
          deployment.md: "Level 3: cluster, scaling, network (if applicable)"
          decisions.md: "Key architectural decisions with rationale"
        api/:
          README.md: "API overview: base URL, auth, rate limiting"
          endpoints.md: "All endpoints: method, path, request/response formats"
          protocols.md: "Communication protocols: HTTP, gRPC, WebSocket, etc."
        deployment/:
          README.md: "Deployment guide: prerequisites, steps"
          configuration.md: "All config options: env vars, files, secrets"
          cluster.md: "Cluster setup: nodes, replication, fault tolerance"
          network.md: "Network: ports, TLS, segmentation, load balancing"
        guides/:
          README.md: "User guides index"
          getting-started.md: "First steps after deployment"
          operations.md: "Day-to-day operations and maintenance"

  #---------------------------------------------------------------------------
  # COMMON PAGES (all project types)
  #---------------------------------------------------------------------------
  common_pages:
    transport.md:
      description: "Protocols and exchange formats — auto-detected from code"
      condition: "Always generated (at minimum documents HTTP/JSON)"
      template: ".devcontainer/images/.claude/templates/docs/transport.md.tpl"
      cross_linking:
        to_api: "Each 'Used by' cell links to api/{slug}.md"
        from_api: "API overview Transport/Format columns link back here"

    api/:
      overview.md:
        description: "API overview with transport cross-links"
        condition: "API_COUNT >= 1"
        template: ".devcontainer/images/.claude/templates/docs/api/overview.md.tpl"
      "{api_slug}.md":
        description: "Per-API detail page with endpoints"
        condition: "API_COUNT > 1 (one page per API)"
        template: ".devcontainer/images/.claude/templates/docs/api/detail.md.tpl"

    changelog.md:
      description: "Changelog from git conventional commits"
      condition: "Always generated"
      source: "git log --oneline with conventional commit parsing"
      structure:
        - "# Changelog"
        - "## [version] - date (grouped by feat/fix/docs/refactor)"

  #---------------------------------------------------------------------------
  # CROSS-LINKING RULES (Transport ↔ API)
  #---------------------------------------------------------------------------
  cross_linking:
    transport_to_api:
      rule: "Each protocol/format 'Used by' cell links to relevant api/{slug}.md"
      anchor_convention: "protocol.toLowerCase() for transport anchors"
    api_to_transport:
      rule: "API overview Transport/Format columns link to transport.md#{anchor}"
      anchor_convention: "format.toLowerCase() for format anchors"
    slug_convention: "api_name.toLowerCase().replace(/\\s+/g, '-') for API slugs"
```

---

## Phase 7.0: Verification (DocAgent-inspired)

```yaml
phase_7_0_verify:
  description: "Iterative quality verification before serving"
  inspiration: "DocAgent multi-agent pattern: Writer → Verifier feedback loop"
  max_iterations: 2

  verifier_checks:
    completeness:
      - "Every primary section (score >= 24) has a full page"
      - "Every standard section (score >= 16) has an own page"
      - "No section references information not present in agent results"
    accuracy:
      - "Mermaid diagrams match actual component names from code"
      - "File paths in links point to real files"
      - "Version numbers match what install scripts actually install"
    quality:
      - "No generic filler ('This module handles X' without explaining HOW)"
      - "Every table has >= 2 rows of real data"
      - "Every code block is syntactically valid"
    no_placeholders:
      - "No 'Coming Soon', 'TBD', 'TODO', 'WIP' in any page"
      - "No '{VARIABLE}' patterns remaining in generated content"
      - "No empty sections or stub pages"
    cross_linking:
      - "Every Transport column in api/overview.md links to valid transport.md anchor"
      - "Every 'Used by' cell in transport.md links to valid api/*.md page"
      - "GitHub links only present when PUBLIC_REPO == true"
      - "Comparison table only present when INTERNAL_PROJECT == false"
      - "Simple feature table only present when INTERNAL_PROJECT == true"
    config_consistency:
      - "~/.claude/docs/config.json exists and contains public_repo + internal_project"
      - "apis[] array matches detected APIs in generated pages"
      - "mkdocs.yml repo_url present only if PUBLIC_REPO == true"
      - "mkdocs.yml nav has no GitHub tab if PUBLIC_REPO == false"

  feedback_loop:
    on_failure:
      action: "Fix the specific issue and re-verify (up to max_iterations)"
      strategy: "Targeted fix — only regenerate the failing section, not all docs"
    on_success:
      action: "Proceed to Phase 8.0 (Serve)"
    on_max_iterations:
      action: "Proceed with warnings listed in serve output"
```

---

## Phase 8.0: Validation + Serve

```yaml
phase_8_0_validate_and_serve:
  description: "Final validation then start MkDocs server"

  validation:
    mandatory_checks:
      - "Every nav entry points to existing file"
      - "No file < 20 lines (likely placeholder)"
      - "No 'TODO', 'TBD', 'Coming Soon' in content"
      - "All code blocks have language tag"
      - "All internal links resolve"
      - "Every architecture page has at least one Mermaid diagram"
      - "index.md has generation marker as first line (<!-- /docs-generated: ... -->)"
      - "index.md starts with hero section after marker (not technical details)"
      - "No full config files copied inline (use links)"
      - "transport.md exists and has >= 1 protocol row"
      - "If API_COUNT >= 1: api/overview.md exists with endpoint table"
      - "If API_COUNT > 1: one api/{slug}.md per detected API"
      - "If PUBLIC_REPO == false: no repo_url in mkdocs.yml"
      - "If PUBLIC_REPO == false: no GitHub icon or tab in nav/footer"
      - "If INTERNAL_PROJECT == true: index.md has simple feature table (no comparison)"
      - "If INTERNAL_PROJECT == false: index.md has comparison table with competitors"
      - "Cross-links between transport.md and api/*.md pages resolve bidirectionally"

    warnings:
      - "File > 300 lines → suggest splitting"
      - "Architecture page without sequence diagram"
      - "API page without request/response examples"
      - "Deployment page without recommended config table"
      - "Transport page without protocol details subsections"

  serve:
    pre_check:
      - "pkill -f 'mkdocs serve' 2>/dev/null || true"

    command: "mkdocs serve -a 0.0.0.0:{PORT}"

    output_template: |
      ═══════════════════════════════════════════════════════════════
        /docs - Server Running (Deep Analysis Complete)
      ═══════════════════════════════════════════════════════════════

        Project Type: {PROJECT_TYPE}
        Analysis:     {N} agents completed
        Diagrams:     {D} Mermaid diagrams generated

        URL: http://localhost:{PORT}

        Generated Sections (by score):
        {SECTIONS_WITH_SCORES}

        Commands:
          /docs --update      Re-analyze and regenerate
          /docs --serve       (Re)start server
          /docs --stop        Stop server
          /docs --status      Show coverage stats

      ═══════════════════════════════════════════════════════════════
```

---

## Mode --serve

```yaml
serve:
  description: "(Re)start server with existing docs — no analysis, no regeneration"

  workflow:
    1_check_docs: "Verify docs/ exists with content (abort if empty)"
    2_kill_existing: "pkill -f 'mkdocs serve' 2>/dev/null || true"
    3_start_server: "mkdocs serve -a 0.0.0.0:{PORT}"

  use_case: "Restart server after manual doc edits, --stop, or port change"

  output_template: |
    ═══════════════════════════════════════════════════════════════
      /docs --serve - Server (Re)started
    ═══════════════════════════════════════════════════════════════

      URL: http://localhost:{PORT}

      Commands:
        /docs --update      Re-analyze and regenerate
        /docs --stop        Stop server
        /docs --status      Show coverage stats

    ═══════════════════════════════════════════════════════════════
```

**IF `$ARGUMENTS` contains `--serve`**: Execute Mode --serve and STOP (do not run analysis phases).

---

## Mode --stop

```yaml
stop:
  command: "pkill -f 'mkdocs serve'"
  output: "Server stopped. Restart: /docs --serve"
```

---

## Mode --status

```yaml
status:
  checks:
    - "Server running? (pgrep -f 'mkdocs serve')"
    - "Docs structure exists? (ls docs/)"
    - "Generation marker? (head -1 docs/index.md)"
    - "Git diff since marker commit"
    - "Content files count"
    - "Mermaid diagrams count"
    - "Broken internal links"
    - "Outdated dependency versions"

  output_template: |
    ═══════════════════════════════════════════════════════════════
      /docs - Status Report
    ═══════════════════════════════════════════════════════════════

      Server      : {RUNNING|STOPPED}
      Structure   : {EXISTS|MISSING}

      Freshness:
        Generated   : {TIMESTAMP} ({DAYS_AGO} days ago)
        Commit      : {MARKER_COMMIT} → HEAD ({COMMITS_SINCE} commits)
        Stale pages : {STALE_COUNT} / {TOTAL_PAGES}
        Broken links: {BROKEN_COUNT}
        Outdated    : {OUTDATED_COUNT} deps

      Content:
        Pages       : {TOTAL_PAGES} files
        Diagrams    : {D} Mermaid blocks
        Coverage    : {PERCENTAGE}%

      {IF_STALE: "Run /docs to update stale pages (incremental)"}
      {IF_FRESH: "Docs are up to date."}

    ═══════════════════════════════════════════════════════════════
```

---

## Mode --quick

**Alias for `--serve`.** Both skip analysis and (re)start the server with existing docs.

```yaml
quick:
  description: "Skip deep analysis, (re)start server with existing docs"
  alias_for: "--serve"

  workflow:
    1_check_docs: "Verify docs/ exists with content (abort if empty)"
    2_kill_existing: "pkill -f 'mkdocs serve' 2>/dev/null || true"
    3_start_server: "mkdocs serve -a 0.0.0.0:{PORT}"

  use_case: "Fast iteration when docs already generated"
```

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Create empty/placeholder page | **FORBIDDEN** | Broken UX |
| Launch agents sequentially | **FORBIDDEN** | Degraded performance |
| Skip scoring | **FORBIDDEN** | Loss of prioritization |
| Generate without analysis | **FORBIDDEN** | Superficial content |
| "Coming Soon" / "TBD" | **FORBIDDEN** | Empty promises |
| Create standalone section with score < 16 | **FORBIDDEN** | Navigation pollution |
| Ignore PROJECT_TYPE | **FORBIDDEN** | Unsuitable structure |
| Architecture page without diagram | **FORBIDDEN** | Degraded comprehension |
| Copy entire config file inline | **FORBIDDEN** | Desynchronization |
| Generic sentence without specific info | **FORBIDDEN** | Hollow content |
| index.md starting with technical content | **FORBIDDEN** | Product pitch first |
| Skip architecture-analyzer for app | **FORBIDDEN** | Architecture is critical |
| Skip freshness check (Phase 3.0) | **FORBIDDEN** | Unnecessary regeneration |
| Generate without marker in index.md | **FORBIDDEN** | Freshness impossible afterwards |
| Full regen when incremental suffices | **AVOID** | Waste of tokens/time |
| Skip Phase 1.0 (config questions) | **FORBIDDEN** | Config drives all conditional content |
| GitHub links when PUBLIC_REPO=false | **FORBIDDEN** | Private repo URL leak |
| Comparison table when INTERNAL_PROJECT=true | **FORBIDDEN** | No competitors for internal project |
| Simple table when INTERNAL_PROJECT=false | **FORBIDDEN** | Must show competitive advantage |
| API menu when API_COUNT=0 | **FORBIDDEN** | Empty nav section |
| Transport page without cross-links to API | **FORBIDDEN** | Cross-linking is the key feature |
| API page without cross-links to Transport | **FORBIDDEN** | Bidirectional is MANDATORY |
| Palette toggle in mkdocs.yml | **FORBIDDEN** | Dark-only, scheme: slate only |
| Hardcoded colors in C4 templates | **FORBIDDEN** | Use COLOR_* variables |
| c4-fix.css in mkdocs.yml | **FORBIDDEN** | Replaced by theme.css |
| Flowchart/sequence without %%{init}%% | **FORBIDDEN** | Inconsistent colors |
| C4 without UpdateElementStyle | **FORBIDDEN** | C4 ignores Mermaid themes |
| Background hex without "1a" suffix | **FORBIDDEN** | Pattern: border=full, bg=10% alpha |
| Skip accent_color question | **FORBIDDEN** | Color drives the entire theme |

---

## MkDocs Configuration

```yaml
# mkdocs.yml (generated at project root)
# See template: .devcontainer/images/.claude/templates/docs/mkdocs.yml.tpl
site_name: "{PROJECT_NAME}"
site_description: "{GENERATED_DESCRIPTION}"
docs_dir: docs

# CONDITIONAL — only if PUBLIC_REPO == true:
# repo_url: "{GIT_REMOTE_URL}"
# repo_name: "{REPO_NAME}"
# edit_uri: "edit/main/docs/"

theme:
  name: material
  palette:
    scheme: slate
    primary: custom
    accent: custom
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.tabs.link
  # CONDITIONAL — only if PUBLIC_REPO == true:
  # icon:
  #   repo: fontawesome/brands/github

plugins:
  - search

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.details
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true

nav:
  # GENERATED by nav_algorithm — never hand-edited
  # ---
  # nav_algorithm:
  #   1. "Docs" tab: index.md + scored sections from Phase 6.0
  #   2. "Transport" tab: transport.md (always present)
  #   3. API tab (conditional on API_COUNT):
  #      - API_COUNT == 0 → no nav item
  #      - API_COUNT == 1 → "API: api/overview.md" (direct link)
  #      - API_COUNT > 1  → "APIs:" dropdown with Overview + per-API pages
  #   4. "Changelog" tab: changelog.md (always present)
  #   5. "GitHub" tab: external link to GIT_REMOTE_URL (only if PUBLIC_REPO == true)
  #   6. Validate: every nav entry points to an existing file
  #
  # Example output (public repo, external project, 2 APIs):
  #   - Docs:
  #     - Home: index.md
  #     - Architecture:
  #       - Overview: architecture/README.md
  #       - Components: architecture/components.md
  #   - Transport: transport.md
  #   - APIs:
  #     - Overview: api/overview.md
  #     - HTTP API: api/http-api.md
  #     - Raft API: api/raft-api.md
  #   - Changelog: changelog.md
  #   - GitHub: https://github.com/org/repo

extra_css:
  - stylesheets/theme.css

extra:
  generator: false
  # CONDITIONAL — only if PUBLIC_REPO == true:
  # social:
  #   - icon: fontawesome/brands/github
  #     link: "{GIT_REMOTE_URL}"

# CONDITIONAL copyright:
#   PUBLIC_REPO true:  "{PROJECT_NAME} · {LICENSE} · <a href='{GIT_REMOTE_URL}'>GitHub</a>"
#   PUBLIC_REPO false: "{PROJECT_NAME} · {LICENSE}"
```

---

## Error Messages

```yaml
errors:
  analysis_failed:
    message: |
      Analysis agent failed: {AGENT_NAME}

      Error: {ERROR_MESSAGE}

      Continuing with partial results...

  empty_section_detected:
    message: |
      Empty section detected: {SECTION}

      Score: {SCORE}/43

      This section has no real content.
      Moving to reference section.

  missing_diagram:
    message: |
      Architecture page without diagram: {PAGE}

      Score: {SCORE}/43 (includes +3 diagram bonus)

      Generating Mermaid diagram from agent analysis data.
      The diagram uses real component names from the codebase.
```

---

## Sources and References

This skill's design draws from the following methodologies and research:

| Source | Contribution | Reference |
|--------|-------------|-----------|
| **C4 Model** (Simon Brown) | Progressive architecture zoom (Context → Container → Component), diagram practices | [Practical C4 Modeling Tips](https://revision.app/blog/practical-c4-modeling-tips) |
| **DocAgent** (arXiv 2504.08725) | Multi-agent coordination: Reader → Searcher → Writer → Verifier, dependency-first ordering, iterative feedback loops | [DocAgent: Multi-Agent Collaboration](https://arxiv.org/html/2504.08725v1) |
| **Divio Documentation System** | Four documentation types (Tutorial, How-to, Reference, Explanation), boundary maintenance | [Divio Documentation Structure](https://docs.divio.com/documentation-system/structure/) |
| **MkDocs** | Configuration options: repo_url, edit_uri, nav structure, validation, plugins | [MkDocs Configuration Guide](https://www.mkdocs.org/user-guide/configuration/) |
| **MkDocs Material** | Theme: dark/light palette, navigation features, code copy, search, Mermaid diagrams | [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) |
| **Product Documentation Tips** | Entry point pattern (About/Access/Usage/Resources/Support), chunking, navigation depth | [10 Tips for Product Documentation](https://developerhub.io/blog/10-tips-for-structuring-your-product-documentation/) |
| **Mermaid** | Diagram types: flowchart, sequence, C4 context, ER, state machine, deployment | [Mermaid Documentation](https://mermaid.js.org/) |
