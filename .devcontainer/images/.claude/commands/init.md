---
name: init
description: |
  Conversational project discovery + doc generation.
  Open-ended dialogue builds rich context, then synthesizes all project docs.
  Use when: creating new project, starting work, verifying setup.
allowed-tools:
  - Write
  - Edit
  - "Bash(git:*)"
  - "Bash(docker:*)"
  - "Bash(terraform:*)"
  - "Bash(kubectl:*)"
  - "Bash(node:*)"
  - "Bash(python:*)"
  - "Bash(go:*)"
  - "Bash(grepai:*)"
  - "Bash(curl:*)"
  - "Bash(pgrep:*)"
  - "Bash(nohup:*)"
  - "Bash(mkdir:*)"
  - "Bash(rm:*)"
  - "Bash(wc:*)"
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Grep(**/*)"
  - "Task(*)"
  - "TaskCreate(*)"
  - "TaskUpdate(*)"
  - "TaskList(*)"
  - "TaskGet(*)"
  - "mcp__github__*"
  - "mcp__codacy__*"
  - "Bash(codacy-analysis-cli:*)"
  - "mcp__taskmaster__*"
---

# /init - Conversational Project Discovery

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Identify detected framework conventions and best practices
- Fetch current stable versions and recommended configurations

---

## Overview

Conversational initialization with **progressive context building**:

1. **Detect** - Template or already personalized?
2. **Discover** - Open-ended conversation to understand the project
3. **Synthesize** - Review accumulated context with user
4. **Generate** - Produce all project docs from rich context
5. **Validate** - Environment, tools, deps, config

---

## Usage

```
/init                # Everything automatic
```

**Intelligent behavior:**
- Detects template → starts discovery conversation
- Detects personalized → skips to validation
- Detects problems → auto-fix when possible
- No flags, no unnecessary questions

---

## Phase 1.0: Detect (Repository Identity → Template vs Personalized)

**Step 1: Identify the repository via git remote.**

```yaml
detect_repository:
  command: "git remote get-url origin 2>/dev/null"
  check: "does the URL contain 'kodflow/devcontainer-template'?"

  decision:
    if_is_devcontainer_template:
      action: "Continue to Step 2 (template marker check)"
      message: "devcontainer-template repo detected."
    if_is_other_project:
      action: "RESET — erase all generated docs, restart Phase 1 from scratch"
      message: "Different project detected. Resetting for fresh initialization."
      reset_files:
        - "/workspace/CLAUDE.md"
        - "/workspace/AGENTS.md"
      reset_directories:
        - "/workspace/docs/"    # rm -rf — template docs don't apply to new projects
      note: "README.md is NOT erased — only its description will be updated in Phase 3"
```

**Step 2 (only for devcontainer-template repo): Check template markers.**

```yaml
detect_template:
  check_markers:
    - file: "/workspace/CLAUDE.md"
      template_marker: "Kodflow DevContainer Template"
    - file: "/workspace/docs/vision.md"
      template_marker: "batteries-included VS Code Dev Container"

  decision:
    if_template_detected:
      action: "Run Phase 1 (Discovery Conversation)"
      message: "Template detected. Let's discover your project."
    if_personalized:
      action: "Skip to Phase 4 (Validation)"
      message: "Project already personalized. Validating..."
```

**Output Phase 0 (other project — reset):**

```
═══════════════════════════════════════════════════════════════
  /init - Project Detection
═══════════════════════════════════════════════════════════════

  Checking: git remote origin
  Result  : {remote_url} (NOT devcontainer-template)

  → Different project detected
  → Resetting docs for fresh initialization...
    ✗ CLAUDE.md        (reset)
    ✗ AGENTS.md        (reset)
    ✗ docs/            (removed)

  → Starting discovery conversation...

═══════════════════════════════════════════════════════════════
```

**Output Phase 0 (devcontainer-template — template markers):**

```
═══════════════════════════════════════════════════════════════
  /init - Project Detection
═══════════════════════════════════════════════════════════════

  Checking: git remote origin
  Result  : kodflow/devcontainer-template

  Checking: /workspace/CLAUDE.md
  Result  : Template markers found

  → Project needs personalization
  → Starting discovery conversation...

═══════════════════════════════════════════════════════════════
```

---

## Phase 2.0: Discovery Conversation

**RULES (ABSOLUTE):**

- Ask **ONE question at a time** as plain text output
- **NEVER** use AskUserQuestion tool
- **NEVER** offer predefined options or multiple-choice lists
- After **EACH** user response, display the updated **Project Context** block
- Adapt the next question based on accumulated context
- Minimum **4** exchanges, maximum **10**
- Questions must be open-ended and conversational

### Question Strategy

**Fixed questions (always asked first):**

```yaml
round_1:
  question: |
    Tell me about your project. What are you building
    and what problem does it solve?
  extracts: [purpose, problem]

round_2:
  question: |
    Who will use this? Describe the people or systems
    that will interact with it.
  extracts: [users]

round_3:
  question: |
    What should we call this project?
  extracts: [name]
```

**Adaptive questions (selected based on gaps in context):**

```yaml
adaptive_pool:
  tech_stack:
    trigger: "tech stack unknown"
    question: "What languages, frameworks, or tools are you planning to use?"
    extracts: [tech_stack]

  data_storage:
    trigger: "data storage relevant AND unknown"
    question: "How will your project store and manage data?"
    extracts: [database]

  deployment:
    trigger: "deployment unknown"
    question: "Where and how will this run in production?"
    extracts: [deployment]

  quality:
    trigger: "quality priorities unknown"
    question: "What matters most for quality — test coverage, performance, security, or something else?"
    extracts: [quality]

  constraints:
    trigger: "constraints unknown"
    question: "Are there any constraints I should know about — team size, timeline, compliance requirements?"
    extracts: [constraints]

  architecture:
    trigger: "complex project AND architecture unclear"
    question: "Do you have a particular architecture in mind — monolith, microservices, event-driven, or something else?"
    extracts: [architecture]

  follow_up:
    trigger: "previous answer was brief"
    question: "Can you tell me more about {topic}? I want to make sure I capture the full picture."
    extracts: [varies]
```

### Project Context Block

**Display this block after EVERY exchange, updated with new information:**

```
═════════════════════════════════════════════════════
  PROJECT CONTEXT
═════════════════════════════════════════════════════
  Name        : {name or "---"}
  Purpose     : {1-2 sentence summary or "---"}
  Problem     : {problem statement or "---"}
  Users       : {target users or "---"}
  Tech Stack  : {languages, frameworks or "---"}
  Database    : {database choices or "---"}
  Deployment  : {cloud/hosting or "---"}
  Architecture: {architecture approach or "---"}
  Quality     : {quality priorities or "---"}
  Constraints : {known constraints or "---"}
  [Discovery — exchange {N}/10]
═════════════════════════════════════════════════════
```

### Transition Criteria

Move to Phase 2 when **ALL** of these are true:

- Name is known
- Purpose/Problem is known
- Users are known
- At least one tech element is concrete
- At least 4 exchanges completed

**OR:** User signals readiness / 10 exchanges reached.

---

## Phase 3.0: Vision Synthesis

**Review the accumulated context with the user before generating files.**

```yaml
synthesis_workflow:
  step_1:
    action: "Display FINAL Project Context with all fields populated"
    output: |
      ═════════════════════════════════════════════════════
        FINAL PROJECT CONTEXT
      ═════════════════════════════════════════════════════
        Name        : {name}
        Purpose     : {purpose}
        Problem     : {problem}
        Users       : {users}
        Tech Stack  : {tech_stack}
        Database    : {database}
        Deployment  : {deployment}
        Architecture: {architecture}
        Quality     : {quality}
        Constraints : {constraints}
      ═════════════════════════════════════════════════════

  step_2:
    message: |
      Here is what I understand about your project.
      Review and tell me if anything needs to change.
      Say "generate" when you're ready for me to create
      your project documentation.

  step_3:
    loop: "Process any refinements, update context, repeat"
    exit: "User says 'generate' or confirms"
```

---

## Phase 4.0: File Generation

**Generate all files DIRECTLY from accumulated context. No templates.**

```yaml
generation_rules:
  - NO mustache/handlebars placeholders
  - NO template files referenced
  - Content is SYNTHESIZED from the full conversation context
  - Every file must contain real, specific, actionable content
  - Write vision.md FIRST, then remaining files in parallel
```

### Files to Generate

```yaml
files:
  # PRIMARY OUTPUT - written first
  - path: "/workspace/docs/vision.md"
    description: "Rich project vision synthesized from conversation"
    structure:
      - "# Vision: {name}"
      - "## Purpose — what and why"
      - "## Problem Statement — pain points addressed"
      - "## Target Users — who benefits and how"
      - "## Goals — prioritized list"
      - "## Success Criteria — measurable targets table"
      - "## Design Principles — guiding decisions"
      - "## Non-Goals — explicit exclusions"
      - "## Key Decisions — tech choices with rationale"

  # SUPPORTING FILES - written in parallel after vision.md
  - path: "/workspace/CLAUDE.md"
    description: "Project overview, tech stack, how to work"
    structure:
      - "# {name}"
      - "## Purpose — 2-3 sentences"
      - "## Tech Stack — languages, frameworks, databases"
      - "## How to Work — /init, /feature, /fix"
      - "## Key Principles — MCP-first, semantic search, specialists"
      - "## Verification — test, lint, security commands"
      - "## Documentation — links to vision, architecture, workflows"

  - path: "/workspace/AGENTS.md"
    description: "Map tech stack to available specialist agents"
    structure:
      - "# Specialist Agents"
      - "## Primary — agents matching tech stack"
      - "## Supporting — review, devops, security agents"
      - "## Usage — when to invoke each agent"

  - path: "/workspace/docs/architecture.md"
    description: "System context, components, data flow"
    structure:
      - "# Architecture: {name}"
      - "## System Context — high-level view"
      - "## Components — key modules/services"
      - "## Data Flow — how data moves"
      - "## Technology Stack — detailed breakdown"
      - "## Constraints — technical boundaries"

  - path: "/workspace/docs/workflows.md"
    description: "Development processes adapted to tech stack"
    structure:
      - "# Development Workflows"
      - "## Setup — prerequisites, installation"
      - "## Development Loop — code, test, commit"
      - "## Testing Strategy — unit, integration, e2e"
      - "## Deployment — build, release process"
      - "## CI/CD — pipeline stages"

  - path: "/workspace/README.md"
    description: "Update description section only, preserve existing structure"
    mode: "edit"
    note: "Only update the project description. Keep all other content."

  # CONDITIONAL FILES
  - path: "/workspace/.env.example"
    condition: "database OR cloud services mentioned"
    description: "Environment variable template"
    structure:
      - "# {name} Environment Variables"
      - "APP_NAME={name}"
      - "# Database, cloud, API vars as relevant"

  - path: "/workspace/Makefile"
    condition: "language with build tooling (Go, Rust, Python, Node)"
    description: "Build targets adapted to tech stack"
    structure:
      - "# {name} targets"
      - "Standard targets: build, test, lint, fmt, clean"
      - "Language-specific targets as relevant"
```

---

## Phase 4.5: CodeRabbit Configuration (AI Tools 1/3)

**Generate `.coderabbit.yaml` if missing, personalized from project context.**
**See also:** Phase 4.6 (Qodo Merge) and Phase 4.7 (Codacy) for the full AI tools configuration block.

```yaml
coderabbit_config:
  trigger: "ALWAYS (after file generation)"
  schema: "https://www.coderabbit.ai/integrations/schema.v2.json"

  1_check_exists:
    action: "Glob('/workspace/.coderabbit.yaml')"
    if_exists:
      status: "SKIP"
      message: "CodeRabbit config already exists."
    if_missing:
      status: "GENERATE"
      message: "Generating .coderabbit.yaml from project context..."

  2_detect_stack:
    action: "Map tech_stack from conversation to CodeRabbit tool names"
    mapping:
      # Language → tools to highlight in path_instructions
      "Go":         { linters: ["golangci-lint"], filePatterns: ["**/*.go"] }
      "Rust":       { linters: ["clippy"], filePatterns: ["**/*.rs"] }
      "Python":     { linters: ["ruff", "pylint"], filePatterns: ["**/*.py"] }
      "Node/TS":    { linters: ["eslint", "biome"], filePatterns: ["**/*.ts", "**/*.js"] }
      "Java":       { linters: ["pmd"], filePatterns: ["**/*.java"] }
      "Kotlin":     { linters: ["detekt"], filePatterns: ["**/*.kt"] }
      "Swift":      { linters: ["swiftlint"], filePatterns: ["**/*.swift"] }
      "PHP":        { linters: ["phpstan"], filePatterns: ["**/*.php"] }
      "Ruby":       { linters: ["rubocop"], filePatterns: ["**/*.rb"] }
      "C/C++":      { linters: ["cppcheck", "clang"], filePatterns: ["**/*.c", "**/*.cpp", "**/*.h"] }
      "C#":         { linters: [], filePatterns: ["**/*.cs"] }
      "Dart":       { linters: [], filePatterns: ["**/*.dart"] }
      "Elixir":     { linters: [], filePatterns: ["**/*.ex", "**/*.exs"] }
      "Lua":        { linters: ["luacheck"], filePatterns: ["**/*.lua"] }
      "Scala":      { linters: [], filePatterns: ["**/*.scala"] }
      "Fortran":    { linters: ["fortitudeLint"], filePatterns: ["**/*.f90"] }
      "Shell":      { linters: ["shellcheck"], filePatterns: ["**/*.sh"] }
      "Terraform":  { linters: ["tflint", "checkov"], filePatterns: ["**/*.tf"] }
      "Docker":     { linters: ["hadolint"], filePatterns: ["**/Dockerfile*"] }
      "Protobuf":   { linters: ["buf"], filePatterns: ["**/*.proto"] }
      "SQL":        { linters: ["sqlfluff"], filePatterns: ["**/*.sql"] }

  3_build_path_instructions:
    action: |
      For EACH detected language/framework, generate a path_instructions entry:
        - path: "{glob pattern from mapping}"
          instructions: "{language-specific review guidance based on project context}"

      ALSO add generic entries for:
        - path: "**/*.md" → "Check documentation accuracy"
        - path: "**/*.sh" → "Validate shell safety: strict mode, quoting, error handling, and command injection risks"
        - path: "**/*.yml" → "Validate CI/CD configuration"
        - path: "**/Dockerfile*" → "Check hadolint compliance, multi-stage builds"

  4_build_labels:
    action: |
      Generate labeling_instructions from project context:
        - ALWAYS include: "dependencies", "breaking-change", "security", "concurrency", "database", "performance", "shell", "correctness"
        - ADD project-specific labels based on architecture:
          - Microservices → "api", "service-{name}"
          - Monorepo → "package-{name}"
          - Frontend → "ui", "accessibility"
          - Backend → "api", "database"

  5_build_code_guidelines:
    action: |
      Populate knowledge_base.code_guidelines.filePatterns from detected stack:
        - Merge all filePatterns from step 2
        - Add: "**/*.yml", "**/*.yaml", "**/*.md", "**/*.json"

  6_generate_file:
    action: "Write /workspace/.coderabbit.yaml"
    template: |
      The file MUST strictly conform to the schema at:
      https://www.coderabbit.ai/integrations/schema.v2.json

      Structure (all sections required):
        language: "en-US"
        tone_instructions: "{derived from project quality priorities}"
        early_access: true
        enable_free_tier: true
        inheritance: false
        reviews:
          profile: "assertive"
          request_changes_workflow: true
          high_level_summary: true
          high_level_summary_instructions: "{from project context}"
          auto_title_instructions: "{conventional commits with project scopes}"
          labeling_instructions: [{from step 4}]
          auto_apply_labels: true
          path_filters: [standard exclusions]
          path_instructions: [{from step 3}]
          auto_review: { enabled: true, base_branches: ["main"] }
          finishing_touches: { docstrings: { enabled: true }, unit_tests: { enabled: true } }
          pre_merge_checks: { title: { mode: "warning" }, description: { mode: "warning" } }
          tools: {ALL tools enabled: true — CodeRabbit auto-detects relevance}
        chat: { art: false, auto_reply: true }
        knowledge_base: { code_guidelines: { filePatterns: [{from step 5}] } }
        code_generation: { docstrings/unit_tests path_instructions from detected stack }
        issue_enrichment: { planning: { enabled: true }, labeling: {from step 4} }

    schema_rules:
      - "pre_merge_checks uses: title, description, issue_assessment, docstrings, custom_checks"
      - "ast-grep has NO enabled property — use: essential_rules, rule_dirs, packages"
      - "issue_enrichment.labeling_instructions is INSIDE issue_enrichment.labeling (nested)"
      - "issue_enrichment.auto_apply_labels is INSIDE issue_enrichment.labeling (nested)"
      - "ALL other tools use: enabled (boolean)"

  7_validate:
    action: |
      python3 - <<'PY'
      import json, pathlib, urllib.request, yaml
      from jsonschema import validate

      cfg_path = pathlib.Path("/workspace/.coderabbit.yaml")
      cfg = yaml.safe_load(cfg_path.read_text())
      schema = json.load(urllib.request.urlopen("https://www.coderabbit.ai/integrations/schema.v2.json"))
      validate(instance=cfg, schema=schema)
      print("valid")
      PY
    on_failure: "Fix YAML syntax or schema violations and retry"
```

**Output Phase 4.5 (generated):**

```text
═══════════════════════════════════════════════════════════════
  CodeRabbit Configuration
═══════════════════════════════════════════════════════════════

  Status: GENERATED (new file)

  Detected Stack:
    ├─ Go       → golangci-lint
    ├─ Shell    → shellcheck
    └─ Docker   → hadolint

  Customizations:
    ├─ 5 path_instructions (language-specific)
    ├─ 8 labels (dependencies, breaking-change, security, concurrency, database, performance, shell, correctness)
    ├─ 3 filePatterns for code guidelines
    └─ Tone: "concise, technical, Go-idiomatic"

  Schema: valid (https://www.coderabbit.ai/integrations/schema.v2.json)

═══════════════════════════════════════════════════════════════
```

**Output Phase 4.5 (skipped):**

```text
═══════════════════════════════════════════════════════════════
  CodeRabbit Configuration
═══════════════════════════════════════════════════════════════

  Status: SKIPPED (file already exists)

═══════════════════════════════════════════════════════════════
```

---

## Phase 4.6: Qodo Merge (PR-Agent) Configuration (AI Tools 2/3)

**Generate `.pr_agent.toml` if missing, personalized from project context.**
**Official docs:** https://qodo-merge-docs.qodo.ai/usage-guide/configuration_options/
**Canonical defaults:** https://github.com/qodo-ai/pr-agent/blob/main/pr_agent/settings/configuration.toml

```yaml
qodo_merge_config:
  trigger: "ALWAYS (after CodeRabbit config)"
  docs: "https://qodo-merge-docs.qodo.ai/usage-guide/configuration_options/"
  canonical_defaults: "https://github.com/qodo-ai/pr-agent/blob/main/pr_agent/settings/configuration.toml"

  1_check_exists:
    action: "Glob('/workspace/.pr_agent.toml')"
    if_exists:
      status: "SKIP"
      output: "Phase 4.6 skipped output"
    if_missing:
      status: "GENERATE"
      steps: [2_detect_stack, 3_build_reviewer_instructions, 4_build_suggestion_instructions, 5_generate_file, 6_validate]

  2_detect_stack:
    action: "Map languages to review conventions for extra_instructions"
    mapping:
      "Go":      "enforce Go error handling (no bare returns), unused vars, panic prevention in production paths"
      "Rust":    "enforce ownership safety, flag unsafe blocks, check panic paths and unwrap/expect"
      "Python":  "enforce type hints, exception handling, no bare except"
      "Node/TS": "enforce strict TypeScript, async/await error handling, no floating promises"
      "Java":    "enforce null checks, resource management (try-with-resources), exception handling"
      "C#":      "enforce nullable reference types, async/await patterns, IDisposable"
      "Shell":   "enforce strict mode (set -euo pipefail), quoting, shellcheck compliance"
      "Docker":  "enforce Dockerfile best practices, non-root user, multi-stage builds, minimal images"
      "Ruby":    "enforce frozen string literals, exception handling, RuboCop compliance"
      "PHP":     "enforce strict types, null safety, PSR compliance"

  3_build_reviewer_instructions:
    action: "Combine base P0/P1/P2 triage + stack-specific rules"
    base: |
      Staff-level reviewer. Diff-first, evidence-driven.
      Triage: P0 (blocker), P1 (major), P2 (minor).
      Cap at 10 findings. If P0 exists, hide P2 entirely.
      Each finding: What/Where + Why + Fix.
    stack_specific: "Merged from step 2 per detected language"

  4_build_suggestion_instructions:
    action: "Adapt code suggestion rules to detected stack"
    base: |
      P0 blockers only. Minimal diffs. No refactors.
      Must compile and preserve existing behavior.
      Keep changes localized to smallest surface area.

  5_generate_file:
    action: "Write /workspace/.pr_agent.toml"
    sections:
      - "[pr_reviewer]": "enable_review_labels_security, enable_review_labels_effort, require_security_review, require_tests_review, extra_instructions"
      - "[pr_code_suggestions]": "num_code_suggestions=6, extra_instructions"
      - "[pr_description]": "enable_semantic_files_types, collapsible_file_list=adaptive, generate_ai_title=false"
      - "[pr_questions]": "enable_help_text=true"
      - "[rag_arguments]": "NOTE: RAG requires Enterprise tier (commented out by default)"
      - "[pr_compliance]": "enable_codebase_duplication, enable_global_pr_compliance, enable_generic_custom_compliance_checklist"
      - "[github_action_config]": "auto_review, auto_describe, auto_improve"
      - "[config]": "output_relevant_configurations=false"

  6_validate:
    action: |
      python3 -c "
      import tomllib, pathlib
      cfg = tomllib.loads(pathlib.Path('/workspace/.pr_agent.toml').read_text())
      sections = list(cfg.keys())
      print(f'valid ({len(sections)} sections: {", ".join(sections)})')
      "
    reference: "Cross-check keys against canonical: https://github.com/qodo-ai/pr-agent/blob/main/pr_agent/settings/configuration.toml"
    on_failure: "Fix TOML syntax and retry"
```

**Output Phase 4.6 (generated):**

```text
═══════════════════════════════════════════════════════════════
  Qodo Merge (PR-Agent) Configuration
═══════════════════════════════════════════════════════════════

  Status: GENERATED (new file)

  Detected Stack:
    ├─ Go       → error handling, panic prevention
    ├─ Shell    → strict mode, shellcheck
    └─ Docker   → hadolint compliance

  Sections:
    ├─ [pr_reviewer] (P0/P1/P2 triage + stack-specific extra_instructions)
    ├─ [pr_code_suggestions] (6 suggestions, P0 blockers only)
    ├─ [pr_description] (semantic files, adaptive collapse)
    ├─ [pr_compliance] (duplication + global compliance)
    └─ [github_action_config] (auto review/describe/improve)

  Validation: valid (TOML syntax)
  Reference: https://github.com/qodo-ai/pr-agent/blob/main/pr_agent/settings/configuration.toml

═══════════════════════════════════════════════════════════════
```

**Output Phase 4.6 (skipped):**

```text
═══════════════════════════════════════════════════════════════
  Qodo Merge (PR-Agent) Configuration
═══════════════════════════════════════════════════════════════

  Status: SKIPPED (file already exists)

═══════════════════════════════════════════════════════════════
```

---

## Phase 4.7: Codacy Configuration (AI Tools 3/3)

**Generate `.codacy.yaml` if missing, personalized from project context.**
**Official docs:** https://docs.codacy.com/repositories-configure/codacy-configuration-file/
**CLI validation:** `codacy-analysis-cli validate-configuration --directory $(pwd)`

```yaml
codacy_config:
  trigger: "ALWAYS (after Qodo Merge config)"
  docs: "https://docs.codacy.com/repositories-configure/codacy-configuration-file/"
  validation_cli: "codacy-analysis-cli validate-configuration --directory $(pwd)"

  1_check_exists:
    action: "Glob('/workspace/.codacy.yaml') OR Glob('/workspace/.codacy.yml')"
    if_exists:
      status: "SKIP"
      output: "Phase 4.7 skipped output"
    if_missing:
      status: "GENERATE"
      steps: [2_detect_excludes, 3_detect_engines, 4_generate_file, 5_validate]

  2_detect_excludes:
    action: "Build exclude_paths from project context"
    always:
      - "CLAUDE.md"
      - "AGENTS.md"
      - "README.md"
      - "docs/**"
      - ".devcontainer/**/*.md"
      - ".claude/**/*.md"
      - ".devcontainer/images/.claude/**/*.md"
    if_detected:
      go: ["vendor/**"]
      node: ["node_modules/**", "dist/**"]
      java: ["target/**", "build/**"]
      rust: ["target/**"]
      python: ["__pycache__/**", ".venv/**"]
      dotnet: ["bin/**", "obj/**"]

  3_detect_engines:
    action: "Optional engine overrides (Codacy auto-detects by default)"
    note: |
      Only add explicit engines section if user has specific preferences.
      Codacy supports 40+ tools out-of-the-box. Override only when:
        - Disabling a tool that produces false positives for the stack
        - Enabling a tool that is not auto-detected
        - Configuring tool-specific options

  4_generate_file:
    action: "Write /workspace/.codacy.yaml"
    format: "YAML with --- header (required by Codacy)"
    structure: |
      ---
      exclude_paths:
        - "{from step 2}"
      # engines section only if step 3 produced overrides

  5_validate:
    primary: "codacy-analysis-cli validate-configuration --directory $(pwd)"
    fallback: |
      python3 -c "
      import yaml, pathlib
      cfg = yaml.safe_load(pathlib.Path('/workspace/.codacy.yaml').read_text())
      excludes = cfg.get('exclude_paths', [])
      print(f'valid ({len(excludes)} exclusions)')
      "
    on_failure: "Fix YAML syntax and retry"
```

**Output Phase 4.7 (generated):**

```text
═══════════════════════════════════════════════════════════════
  Codacy Configuration
═══════════════════════════════════════════════════════════════

  Status: GENERATED (new file)

  Exclusions:
    ├─ 7 always-excluded paths (docs, prompts)
    └─ 2 stack-specific exclusions (vendor, node_modules)

  Engines: auto-detect (no overrides)

  Validation: valid (codacy-analysis-cli)
  Docs: https://docs.codacy.com/repositories-configure/codacy-configuration-file/

═══════════════════════════════════════════════════════════════
```

**Output Phase 4.7 (skipped):**

```text
═══════════════════════════════════════════════════════════════
  Codacy Configuration
═══════════════════════════════════════════════════════════════

  Status: SKIPPED (file already exists)

═══════════════════════════════════════════════════════════════
```

---

## Phase 4.8: GitHub Branch Protection (CI Gates)

**Configure branch protection ruleset and tighten CI gates for merge quality.**
**API docs:** https://docs.github.com/en/rest/repos/rules

```yaml
branch_protection_config:
  trigger: "ALWAYS (after Codacy config)"
  api: "https://docs.github.com/en/rest/repos/rules"

  1_check_exists:
    action: |
      GITHUB_TOKEN=$(jq -r '.mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN // empty' /workspace/mcp.json 2>/dev/null)
      [ -z "$GITHUB_TOKEN" ] && { echo "No GITHUB_TOKEN — skipping"; exit 1; }
      REMOTE=$(git remote get-url origin 2>/dev/null)
      [ -z "$REMOTE" ] && { echo "No git remote — skipping"; exit 1; }
      OWNER=$(echo "$REMOTE" | sed 's|.*github.com[:/]\([^/]*\)/.*|\1|')
      REPO=$(echo "$REMOTE" | sed 's|.*/\([^.]*\)\.git$|\1|; s|.*/\([^/]*\)$|\1|')
      if [ -z "$OWNER" ] || [ -z "$REPO" ]; then echo "Cannot parse owner/repo from $REMOTE"; exit 1; fi
      TMPFILE=$(mktemp)
      trap 'rm -f "$TMPFILE"' EXIT
      HTTP_CODE=$(curl -sS -w "%{http_code}" -o "$TMPFILE" \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/$OWNER/$REPO/rulesets")
      if [ "$HTTP_CODE" = "200" ]; then
        jq -e '.[] | select(.name == "main-protection")' "$TMPFILE" > /dev/null 2>&1
      elif [ "$HTTP_CODE" = "404" ]; then
        false  # Not found → trigger CONFIGURE
      else
        echo "GitHub API error (HTTP $HTTP_CODE)"; cat "$TMPFILE"; exit 2
      fi
    exit_codes:
      0: "Ruleset found (jq matched)"
      1: "No token, no remote, bad owner/repo, or ruleset not found (404/jq miss)"
      2: "HTTP/auth error (non-200, non-404)"
    if_exists:
      status: "SKIP"
      message: "Ruleset main-protection already exists."
    if_missing:
      status: "CONFIGURE"
      steps: [2_extract_tokens, 3_detect_owner_repo, 4_configure_codacy_gate, 5_update_coderabbit, 6_create_ruleset, 7_validate]
    if_api_error:
      status: "SKIP"
      message: "GitHub API error — cannot verify rulesets. Check token permissions."
    if_no_token:
      status: "SKIP"
      message: "No GITHUB_TOKEN in mcp.json — cannot configure branch protection."

  2_extract_tokens:
    action: "Extract tokens from /workspace/mcp.json using jq"
    github: "jq -r '.mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN // empty' /workspace/mcp.json"
    codacy: "jq -r '.mcpServers.codacy.env.CODACY_ACCOUNT_TOKEN // empty' /workspace/mcp.json"
    notes:
      - "GITHUB_TOKEN must be non-empty — abort phase if empty"
      - "CODACY_TOKEN may be empty — step 4 is conditional"

  3_detect_owner_repo:
    action: "Parse owner/repo from git remote origin"
    command: |
      REMOTE=$(git remote get-url origin 2>/dev/null)
      [ -z "$REMOTE" ] && { echo "No git remote — skipping"; exit 1; }
      OWNER=$(echo "$REMOTE" | sed 's|.*github.com[:/]\([^/]*\)/.*|\1|')
      REPO=$(echo "$REMOTE" | sed 's|.*/\([^.]*\)\.git$|\1|; s|.*/\([^/]*\)$|\1|')
      if [ -z "$OWNER" ] || [ -z "$REPO" ]; then echo "Cannot parse owner/repo from $REMOTE"; exit 1; fi
    handles: "SSH (git@github.com:owner/repo.git) and HTTPS (https://github.com/owner/repo)"
    on_failure: "Log warning, skip phase"

  4_configure_codacy_gate:
    action: "Set Codacy diff coverage gate to 80% via Codacy API v3"
    condition: "CODACY_TOKEN is non-empty"
    sets_flag: "CODACY_CONFIGURED=true on success (used by step 6 to conditionally add status checks)"
    command: |
      CODACY_CONFIGURED=false
      [ -z "$CODACY_TOKEN" ] && { echo "Codacy gate skipped (no token)"; exit 0; }
      curl -fsSL -X PATCH \
        -H "api-token: $CODACY_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"diffCoverageThreshold": 80}' \
        "https://api.codacy.com/api/v3/organizations/gh/$OWNER/repositories/$REPO/settings/quality/pull-requests" \
        && CODACY_CONFIGURED=true
      export CODACY_CONFIGURED
    on_success: "Codacy diff coverage gate set to 80%, CODACY_CONFIGURED=true"
    on_failure: "Log warning, CODACY_CONFIGURED remains false — Codacy checks excluded from ruleset"
    if_no_token: "SKIP — CODACY_CONFIGURED=false, Codacy checks excluded from ruleset"

  5_update_coderabbit:
    action: "Edit .coderabbit.yaml — harden pre_merge_checks from warning to error"
    condition: "Glob('/workspace/.coderabbit.yaml') returns a match"
    edit:
      target_keys:
        - "reviews.pre_merge_checks.title.mode"
        - "reviews.pre_merge_checks.description.mode"
      from: "warning"
      to: "error"
    preserve:
      - "reviews.request_changes_workflow: true (must remain true)"
      - "All other keys unchanged"
    if_file_missing: "SKIP — log: .coderabbit.yaml not found"

  5b_validate_coderabbit:
    action: "Re-validate .coderabbit.yaml after edit (same logic as Phase 4.5 step 7)"
    condition: "Glob('/workspace/.coderabbit.yaml') returns a match"
    command: |
      python3 - <<'PY'
      import json, pathlib, urllib.request, yaml
      from jsonschema import validate

      cfg_path = pathlib.Path("/workspace/.coderabbit.yaml")
      cfg = yaml.safe_load(cfg_path.read_text())
      schema = json.load(urllib.request.urlopen("https://www.coderabbit.ai/integrations/schema.v2.json"))
      validate(instance=cfg, schema=schema)
      print("valid")
      PY
    on_success: "YAML valid after pre_merge_checks edit"
    if_file_missing: "SKIP — log: .coderabbit.yaml not found"
    on_failure: "Revert edit (restore warning mode), log error, continue"

  6_create_ruleset:
    action: "POST to GitHub Rulesets API to create main-protection"
    note: "Codacy status checks are only included if CODACY_CONFIGURED flag is set (step 4 succeeded)"
    command: |
      # Build rules array — Codacy checks only if step 4 configured successfully
      RULES='[{"type":"pull_request","parameters":{"required_approving_review_count":1,"dismiss_stale_reviews_on_push":true,"require_last_push_approval":false,"required_review_thread_resolution":true}}'
      if [ "$CODACY_CONFIGURED" = "true" ]; then
        RULES="$RULES"',{"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":true,"do_not_enforce_on_create":false,"required_status_checks":[{"context":"Codacy Static Code Analysis"},{"context":"Codacy Diff Coverage"}]}}'
      fi
      RULES="$RULES]"
      curl -fsSL -X POST \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -H "Content-Type: application/json" \
        -d "{
          \"name\": \"main-protection\",
          \"target\": \"branch\",
          \"enforcement\": \"active\",
          \"conditions\": {
            \"ref_name\": {
              \"include\": [\"refs/heads/main\"],
              \"exclude\": []
            }
          },
          \"rules\": $RULES
        }" \
        "https://api.github.com/repos/$OWNER/$REPO/rulesets"
    on_failure: "Display HTTP error — may require GitHub Pro/Team plan for rulesets"

  7_validate:
    action: "Confirm ruleset is active"
    command: |
      curl -fsSL \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/$OWNER/$REPO/rulesets" \
        | jq -e '.[] | select(.name == "main-protection" and .enforcement == "active")'
    on_success: "Ruleset confirmed active"
    on_failure: "Log warning: could not verify ruleset"
```

**Output Phase 4.8 (configured):**

```text
═══════════════════════════════════════════════════════════════
  GitHub Branch Protection (CI Gates)
═══════════════════════════════════════════════════════════════

  Status: CONFIGURED (ruleset created)

  Ruleset: main-protection
    ├─ Target  : refs/heads/main
    ├─ Enforce : active
    ├─ Reviews : 1 required approver (dismiss stale on push)
    {{#if CODACY_CONFIGURED}}
    └─ Checks  : Codacy Static Code Analysis
                 Codacy Diff Coverage
    {{else}}
    └─ Checks  : (none — Codacy not configured)
    {{/if}}

  {{#if CODACY_CONFIGURED}}
  Codacy Gate:
    └─ diffCoverageThreshold: 80% (set via API)
  {{else}}
  Codacy Gate:
    └─ SKIPPED (no CODACY_ACCOUNT_TOKEN)
  {{/if}}

  CodeRabbit:
    └─ pre_merge_checks: title + description → mode: error

  Qodo:
    └─ No gate required

═══════════════════════════════════════════════════════════════
```

**Output Phase 4.8 (skipped):**

```text
═══════════════════════════════════════════════════════════════
  GitHub Branch Protection (CI Gates)
═══════════════════════════════════════════════════════════════

  Status: SKIPPED (ruleset main-protection already exists)

═══════════════════════════════════════════════════════════════
```

---

## Phase 4.9: Taskmaster Init + Feature Bootstrap (Conditional)

```yaml
phase_4.9_taskmaster_init:
  condition: "mcp__taskmaster__ available AND /workspace/.taskmaster/config.json absent"
  actions:
    1_initialize:
      action: "mcp__taskmaster__initialize_project"
    2_parse_prd:
      condition: "/workspace/docs/vision.md exists"
      action: |
        mcp__taskmaster__parse_prd(input: /workspace/docs/vision.md)
        Converts project vision into a structured task backlog.

phase_4.9_feature_bootstrap:
  condition: "/workspace/.claude/features.json absent"
  actions:
    1_create_db:
      action: |
        Ensure directory exists: mkdir -p /workspace/.claude
        Create /workspace/.claude/features.json with: { "version": 2, "features": [] }
    2_propose_features:
      action: |
        Based on the discovery conversation, propose /feature --add
        for each identified feature of the project.
        For each feature, ask user to specify:
          - level (0 = architectural, 1 = subsystem, 2+ = component)
          - workdirs (directories this feature owns)
          - audit_dirs (directories this feature audits, default = workdirs)
        Show inferred parent-child relationships after all features are added.
        Ask user to confirm each feature before adding.
```

---

## Phase 5.0: Environment Validation

**Verify the environment (parallel via Task agents).**

```yaml
parallel_checks:
  agents:
    - name: "tools-checker"
      checks: [git, node, go, terraform, docker, grepai]
      output: "{tool, required, installed, status}"

    - name: "deps-checker"
      checks: [npm ci, go mod, terraform init]
      output: "{manager, status, issues}"

    - name: "config-checker"
      checks: [.env, CLAUDE.md, mcp.json]
      output: "{file, status, issue}"

    - name: "grepai-checker"
      checks: [Ollama, daemon, index]
      output: "{component, status, details}"

    - name: "secret-checker"
      checks: [op CLI, OP_SERVICE_ACCOUNT_TOKEN, vault access, project secrets]
      output: "{op_installed, token_set, vault_name, project_path, secrets_count, status}"
```

---

## Phase 6.0: Report

```
═══════════════════════════════════════════════════════════════
  /init - Complete
═══════════════════════════════════════════════════════════════

  Project: {name}
  Purpose: {purpose summary}

  Generated:
    ✓ docs/vision.md
    ✓ CLAUDE.md
    ✓ AGENTS.md
    ✓ docs/architecture.md
    ✓ docs/workflows.md
    ✓ README.md (updated)
    ✓ .coderabbit.yaml (generated if missing)
    ✓ .pr_agent.toml (generated if missing)
    ✓ .codacy.yaml (generated if missing)
    {{#if phase4_8_configured}}✓ Branch protection: main-protection ruleset (CI gates){{/if}}
    {conditional files}

  Environment:
    ✓ Tools installed ({tool list})
    ✓ Dependencies ready
    ✓ grepai indexed ({N} files)

  1Password:
    ✓ op CLI installed
    ✓ Vault connected ({N} project secrets)

  Ready to develop!
    → /feature "description" to start

═══════════════════════════════════════════════════════════════
```

---

## Phase 7.0: GrepAI Calibration

**MANDATORY** after project discovery. Calibrate grepai config based on project size and structure.

```yaml
grepai_calibration:
  1_count_files:
    command: |
      find /workspace -type f \
        -not -path '*/.git/*' -not -path '*/node_modules/*' \
        -not -path '*/vendor/*' -not -path '*/.grepai/*' \
        -not -path '*/__pycache__/*' -not -path '*/target/*' \
        -not -path '*/.venv/*' -not -path '*/dist/*' | wc -l
    output: file_count

  2_select_profile:
    rules:
      - "file_count < 10000   → profile: small"
      - "file_count < 100000  → profile: medium"
      - "file_count < 500000  → profile: large"
      - "file_count >= 500000 → profile: massive"

    profiles:
      small:
        chunking: { size: 1024, overlap: 100 }
        hybrid: { enabled: true, k: 60 }
        debounce_ms: 1000
      medium:
        chunking: { size: 1024, overlap: 100 }
        hybrid: { enabled: true, k: 60 }
        debounce_ms: 2000
      large:
        chunking: { size: 512, overlap: 50 }
        hybrid: { enabled: true, k: 60 }
        debounce_ms: 3000
      massive:
        chunking: { size: 512, overlap: 50 }
        hybrid: { enabled: false }
        debounce_ms: 5000

  3_detect_languages:
    action: "Scan for go.mod, package.json, Cargo.toml, etc."
    output: "Filter trace.enabled_languages to only detected languages"

  4_customize_boost:
    action: |
      Scan project structure (ls -d */):
      - If src/ exists → bonus /src/ 1.2
      - If pkg/ exists → bonus /pkg/ 1.15
      - If internal/ exists → bonus /internal/ 1.1
      - If app/ exists → bonus /app/ 1.15
      - If lib/ exists → bonus /lib/ 1.15
      Add project-specific ignore patterns (e.g., .next/, .nuxt/, .angular/)

  5_write_config:
    action: "Generate .grepai/config.yaml with selected profile"
    template: "/etc/grepai/config.yaml (base) + profile overrides"

  6_restart_daemon:
    action: |
      pkill -f 'grepai watch' 2>/dev/null || true
      rm -f /workspace/.grepai/index.gob /workspace/.grepai/symbols.gob
      nohup grepai watch >/tmp/grepai.log 2>&1 &
      sleep 3
      grepai status
```

**Output Phase 6:**

```
═══════════════════════════════════════════════════════════════
  GrepAI Calibration
═══════════════════════════════════════════════════════════════

  Files detected : 47,230
  Profile        : medium
  Model          : bge-m3 (1024d, 72% accuracy)

  Config applied:
    chunking    : 1024 tokens / 100 overlap
    hybrid      : ON (k=60)
    debounce    : 2000ms
    languages   : .go, .ts, .py (3 detected)

  Boost customized:
    +1.2  /src/
    +1.15 /pkg/
    +1.1  /internal/

  Daemon: restarted (indexing 47,230 files...)

═══════════════════════════════════════════════════════════════
```

---

## Auto-fix (automatic)

When a problem is detected, auto-fix if possible:

| Problem | Auto Action |
|---------|-------------|
| `.env` missing | `cp .env.example .env` |
| deps not installed | `npm ci` / `go mod download` |
| grepai not running | `nohup grepai watch &` |
| Ollama not reachable | Display HOST instructions |
| grepai uncalibrated | Run Phase 6 calibration |

---

## Guardrails

| Action | Status |
|--------|--------|
| Skip detection | FORBIDDEN |
| Closed questions / AskUserQuestion | FORBIDDEN |
| Placeholders in generated files | FORBIDDEN |
| Skip vision synthesis review | FORBIDDEN |
| Destructive fix without asking | FORBIDDEN |
