---
name: plan
description: |
  Enter Claude Code planning mode with RLM decomposition.
  Analyzes codebase, designs approach, creates step-by-step plan.
  Use when: starting a new feature, refactoring, or complex task.
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "Grep(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Task(*)"
  - "WebFetch(*)"
  - "WebSearch(*)"
  - "mcp__github__*"
  - "mcp__playwright__*"
  - "Write(.claude/plans/*.md)"
  - "Write(.claude/contexts/*.md)"
---

# /plan - Claude Code Planning Mode (RLM Architecture)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

---

## Overview

Planning mode with **RLM** patterns:

- **Peek** - Quick codebase scan
- **Decompose** - Split into subtasks
- **Parallelize** - Multi-domain exploration
- **Synthesize** - Structured plan

**Principle**: Plan -> Validate -> Implement (never the reverse)

---

## Arguments

| Pattern | Action |
|---------|--------|
| `<description>` | Plans the implementation of the feature/fix |
| `--context` | Auto-detect most recent `.claude/contexts/*.md` |
| `--context=<name>` | Load specific `.claude/contexts/{name}.md` |
| `--help` | Show help |

---

## --help

```
═══════════════════════════════════════════════════════════════
  /plan - Claude Code Planning Mode (RLM)
═══════════════════════════════════════════════════════════════

Usage: /plan <description> [options]

Options:
  <description>     What to implement
  --context         Load most recent .claude/contexts/*.md
  --context=<name>  Load specific .claude/contexts/{name}.md
  --help            Show this help

RLM Patterns:
  1. Peek       - Quick codebase scan
  2. Decompose  - Split into subtasks
  3. Parallelize - Parallel exploration
  4. Synthesize - Structured plan

Workflow:
  /search <topic> → /plan <feature> → (approve) → /do

Examples:
  /plan "Add user authentication with JWT"
  /plan "Refactor database layer" --context
  /plan "Fix memory leak in worker process"

═══════════════════════════════════════════════════════════════
```

---

## Phase 1.0: Peek (RLM Pattern)

**Quick scan BEFORE deep exploration:**

```yaml
peek_workflow:
  0_recover_context:
    rule: "Before exploring, check .claude/contexts/*.md for related research"
    action: "Glob .claude/contexts/*.md — read most recent or matching slug"
    importance: "CRITICAL after context compaction — research survives on disk"

  1_context_check:
    action: "Check if .claude/contexts/*.md exists (--context flag or auto-detect)"
    tool: [Glob, Read]
    output: "context_available"
    logic:
      "--context=<name>": "Read .claude/contexts/{name}.md"
      "--context (no value)": "Read most recent .claude/contexts/*.md"
      "no flag": "Check if any .claude/contexts/*.md matches description keywords"

  2_structure_scan:
    action: "Scan project structure"
    tools: [Glob]
    patterns:
      - "src/**/*"
      - "tests/**/*"
      - "package.json | go.mod | Cargo.toml"

  3_pattern_grep:
    action: "Identify relevant patterns"
    tools: [Grep]
    searches:
      - Keywords from description
      - Related function names
      - Existing patterns
```

**Phase 1 Output:**

```
═══════════════════════════════════════════════════════════════
  /plan - Peek Analysis
═══════════════════════════════════════════════════════════════

  Description: "Add user authentication with JWT"

  Context:
    ✓ .claude/contexts/{slug}.md loaded (from /search)
    ✓ 47 source files scanned
    ✓ 23 test files found

  Patterns identified:
    - Existing auth: src/middleware/auth.ts
    - User model: src/models/user.ts
    - Routes: src/routes/*.ts

  Keywords matched: 15 occurrences

═══════════════════════════════════════════════════════════════
```

---

## Phase 2.0: Decompose (RLM Pattern)

**Split the task into subtasks:**

```yaml
decompose_workflow:
  1_analyze_description:
    action: "Extract objectives"
    example:
      description: "Add user authentication with JWT"
      objectives:
        - "Setup JWT utilities"
        - "Create auth middleware"
        - "Add login/logout endpoints"
        - "Protect existing routes"
        - "Add tests"

  2_identify_domains:
    action: "Categorize by domain"
    domains:
      - backend: "API, middleware, database"
      - frontend: "UI components, state"
      - infrastructure: "config, deployment"
      - testing: "unit, integration, e2e"

  3_order_dependencies:
    action: "Order by dependency"
    output: "ordered_tasks[]"
```

---

## Phase 3.0: Parallelize (RLM Pattern)

**Multi-domain exploration in parallel:**

```yaml
parallel_exploration:
  mode: "PARALLEL (single message, multiple Task calls)"

  agents:
    - task: "backend-explorer"
      type: "Explore"
      prompt: |
        Analyze backend for: {description}
        Find: related files, existing patterns, dependencies
        Return: {files[], patterns[], recommendations[]}

    - task: "frontend-explorer"
      type: "Explore"
      prompt: |
        Analyze frontend for: {description}
        Find: components, state, API calls
        Return: {files[], components[], state_management}

    - task: "test-explorer"
      type: "Explore"
      prompt: |
        Analyze tests for: {description}
        Find: existing coverage, test patterns
        Return: {coverage, patterns[], gaps[]}

    - task: "patterns-consultant"
      type: "Explore"
      prompt: |
        Consult ~/.claude/docs/ for: {description}
        Find: applicable design patterns
        Return: {patterns[], references[]}
```

**IMPORTANT**: Launch ALL agents in a SINGLE message.

---

## Phase 4.0: Pattern Consultation

**Consult `~/.claude/docs/` for patterns when applicable:**

> **Escape clause:** For trivial tasks (single-file edits, config changes, version bumps),
> skip pattern consultation and proceed directly to Phase 5.0 (Synthesize).
> Apply this phase only when architecture or design decisions are involved.

```yaml
pattern_consultation:
  1_identify_category:
    mapping:
      - "Object creation?" → creational/README.md
      - "Performance/Cache?" → performance/README.md
      - "Concurrency?" → concurrency/README.md
      - "Architecture?" → architectural/*.md
      - "Integration?" → messaging/README.md
      - "Security?" → security/README.md

  2_read_patterns:
    action: "Read(~/.claude/docs/<category>/README.md)"
    output: "2-3 applicable patterns"

  3_integrate:
    action: "Add to plan with justification"
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  Pattern Analysis
═══════════════════════════════════════════════════════════════

  Patterns identified:
    ✓ Repository (DDD) - For user data access
    ✓ Factory (Creational) - For token creation
    ✓ Middleware (Enterprise) - For auth chain

  References consulted:
    → ~/.claude/docs/ddd/README.md
    → ~/.claude/docs/creational/README.md
    → ~/.claude/docs/enterprise/README.md

═══════════════════════════════════════════════════════════════
```

---

## Phase 5.0: Synthesize (RLM Pattern)

**Generate the structured plan:**

```yaml
synthesize_workflow:
  plan_audience:
    rule: "Plan must be executable by a skilled developer with ZERO domain knowledge"
    implications:
      - "Chemins de fichiers EXACTS (pas 'the auth module')"
      - "Code samples COMPLETS (pas 'implement the logic')"
      - "Commandes CLI EXACTES avec outputs attendus"

  step_granularity:
    rule: "Each step = 1 TDD cycle (2-5 min)"
    format: |
      ### Step N: <Titre>
      **Files:** `src/file.ts` (create), `tests/file.test.ts` (create)
      **Test first:** Write failing test for {behavior}
      **Implement:** Minimal code to pass
      **Verify:** Run tests, confirm green
      **Commit:** `feat(scope): description`

  1_collect:
    action: "Collect agent results"

  2_consolidate:
    action: "Merge into coherent plan"

  3_generate:
    format: "Structured plan document"

  4_persist_to_disk:
    action: "Write plan to .claude/plans/{slug}.md"
    slug_rule: "Same as /search: lowercase, hyphens, max 40 chars from description"
    collision: "If file exists, append timestamp suffix (-YYYYMMDD-HHMM)"
    purpose: "Survives context compaction; /do can detect from disk"
    note: "This is IN ADDITION to ExitPlanMode (which shows plan to user)"

  5_persist_context:
    action: "Write context file to .claude/contexts/{slug}.md"
    trigger: "Always after plan generation"
    purpose: "Captures discoveries, relevant files, and implementation notes for /do recovery"
    content:
      header: |
        # Context: {description}
        Generated: {ISO8601}
        Plan: .claude/plans/{slug}.md
      sections:
        discoveries: "Key findings from codebase analysis (patterns, conventions, gotchas)"
        relevant_files: "Files examined during planning with brief role description"
        implementation_notes: "Technical decisions, trade-offs, constraints discovered"
        dependencies: "External libs, APIs, or services involved"
    link_in_plan:
      action: "Add 'Context: .claude/contexts/{slug}.md' line in plan header"
      format: |
        # Implementation Plan: {description}
        Context: .claude/contexts/{slug}.md
```

**Plan Output Format:**

```markdown
# Implementation Plan: <description>
Context: .claude/contexts/<slug>.md

## Overview
<2-3 sentences summarizing the approach>

## Design Patterns Applied

| Pattern | Category | Justification | Reference |
|---------|----------|---------------|-----------|
| Repository | DDD | Data access abstraction | ~/.claude/docs/ddd/README.md |
| Factory | Creational | Token creation | ~/.claude/docs/creational/README.md |

## Prerequisites
- [ ] <Required dependency or setup>
- [ ] <Other prerequisite>

## Implementation Steps

### Step 1: <Title>
**Files:** `src/file1.ts`, `src/file2.ts`
**Actions:**
1. <Specific action>
2. <Specific action>

**Code pattern:**
```<lang>
// Example of what will be implemented
```

### Step 2: <Title>
...

## Testing Strategy
- [ ] Unit tests for `component`
- [ ] Integration test for `flow`

## Rollback Plan
How to rollback if issues

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Risk description | Solution |
```

---

## Phase 5.5: Complexity Check

**Triggered automatically after Synthesize. NOT a blocker — just a question.**

```yaml
complexity_check:
  trigger: "files_to_modify + files_to_create > 15"

  action:
    tool: AskUserQuestion
    questions:
      - question: "This plan touches {n} files. Beyond ~15 files in a single session, quality may degrade. How do you want to proceed?"
        header: "Scope"
        options:
          - label: "Execute as-is"
            description: "Proceed with the full plan in one session"
          - label: "Split into phases"
            description: "Claude will propose logical segments to execute separately"

  on_execute_as_is:
    action: "Continue to Phase 6.0 normally"

  on_split:
    action: |
      Rewrite the plan into numbered phases (Phase A, B, C...)
      Each phase: <= 15 files, independently testable
      User approves each phase via /do
```

**If <= 15 files:** Skip this phase silently, proceed to Phase 6.0.

---

## Phase 6.0: Validation Request

**MANDATORY: Wait for user approval**

```
═══════════════════════════════════════════════════════════════
  Plan ready for review
═══════════════════════════════════════════════════════════════

  Summary:
    • 4 implementation steps
    • 6 files to modify
    • 2 new files to create
    • 8 tests to add

  Design Patterns:
    • Repository (DDD)
    • Factory (Creational)

  Estimated complexity: MEDIUM

  Actions:
    → Review the plan above
    → Run /do to execute (auto-detects plan)
    → Or modify the plan manually

═══════════════════════════════════════════════════════════════
```

---

## Integration with other skills

| Before /plan | After /plan |
|-------------|-------------|
| `/search <topic>` | `/do` |
| Generates `.claude/contexts/{slug}.md` | Executes the plan (auto-detected from conversation or `.claude/plans/`) |

**Full workflow:**

```
/search "JWT authentication best practices"
    ↓
.claude/contexts/jwt-auth-best-practices.md generated
    ↓
/plan "Add JWT auth to API" --context
    ↓
Plan created, displayed, AND persisted to .claude/plans/add-jwt-auth-api.md
    ↓
User: "OK, go ahead"
    ↓
/do                          # Detects plan from conversation OR .claude/plans/
    ↓
Implementation executed
```

**Note**: `/do` automatically detects the approved plan from conversation context
or from `.claude/plans/*.md` on disk (conversation takes priority).
Plans persist across context compaction.

---

## DTO Convention (Go)

**If the plan involves DTOs, remind the convention:**

```yaml
dto_reminder:
  trigger: "Plan includes DTO/Request/Response structs"

  convention:
    format: 'dto:"<direction>,<context>,<security>"'
    values:
      direction: [in, out, inout]
      context: [api, cmd, query, event, msg, priv]
      security: [pub, priv, pii, secret]

  purpose: |
    Exempts structs from KTN-STRUCT-ONEFILE
    (grouping multiple DTOs in the same file is allowed)

  include_in_plan: |
    ### DTO Convention
    All DTO structs MUST use `dto:"dir,ctx,sec"` tags:
    ```go
    type CreateUserRequest struct {
        Email string `dto:"in,api,pii" json:"email"`
    }
    ```
    Ref: `~/.claude/docs/conventions/dto-tags.md`
```

---

## Guardrails (ABSOLUTE)

| Action | Status |
|--------|--------|
| Skip Phase 1 (Peek) | **FORBIDDEN** |
| Sequential exploration | **FORBIDDEN** |
| Skip Pattern Consultation | **FORBIDDEN** |
| Implement without approved plan | **FORBIDDEN** |
| Plan without concrete steps | **FORBIDDEN** |
| Plan without rollback strategy | **WARNING** |
