---
name: do
description: |
  Iterative task execution loop with RLM decomposition.
  Transforms a task into a persistent loop with automatic iteration.
  The agent keeps going, fixing its own mistakes, until success criteria are met.
  Also executes approved plans from /plan (auto-detected).
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Grep(**/*)"
  - "Write(**/*)"
  - "Edit(**/*)"
  - "Bash(*)"
  - "Task(*)"
  - "TaskCreate(*)"
  - "TaskUpdate(*)"
  - "TaskList(*)"
  - "TaskGet(*)"
  - "AskUserQuestion(*)"
  - "mcp__codacy__codacy_cli_analyze(*)"
---

# /do - Iterative Task Loop (RLM Architecture)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Verify library API usage before writing implementation code
- Check framework conventions when working on unfamiliar codebases
- Resolve ambiguous patterns by consulting up-to-date documentation

---

## Overview

Iterative loop using **Recursive Language Model** decomposition:

- **Peek** - Quick scan before execution
- **Decompose** - Split the task into sub-objectives
- **Parallelize** - Parallel validations (test, lint, build)
- **Synthesize** - Consolidated report

**Principle**: Iterate until success rather than aiming for perfection.

---

## --help

```
═══════════════════════════════════════════════════════════════
  /do - Iterative Task Loop (RLM)
═══════════════════════════════════════════════════════════════

  DESCRIPTION
    Transforms a task into a persistent loop of iterations.
    The agent continues until the success criteria are met
    or the iteration limit is reached.

    If an approved plan exists (via /plan), it executes it
    automatically without asking interactive questions.

  USAGE
    /do <task>              Launch the interactive workflow
    /do                     Execute the approved plan (if exists)
    /do --plan <path>       Execute a specific plan file
    /do --help              Display this help

  RLM PATTERNS
    1. Plan    - Approved plan detection (skip questions if yes)
    2. Secret   - 1Password secret discovery
    3. Questions - Interactive configuration (if no plan)
    4. Peek     - Codebase scan + git conflict check
    5. Decompose - Split into measurable sub-objectives
    6. Loop     - Simultaneous validations (test/lint/build)
    7. Synthesize - Consolidated report per iteration

  EXAMPLES
    /do "Migrate Jest tests to Vitest"
    /do "Add tests to cover src/utils at 80%"
    /do                     # Execute the plan from /plan

  GUARDRAILS
    - Max 50 iterations (default: 10)
    - MEASURABLE success criteria only
    - Mandatory diff review before merge
    - Git conflict check before modifications

═══════════════════════════════════════════════════════════════
```

**IF `$ARGUMENTS` contains `--help`**: Display the help above and STOP.

---

## Phase 1.0: Approved Plan Detection

**Announce:** Always start with: "I'm using /do to {task_summary}"

**ALWAYS execute first. Checks if /plan was used.**

```yaml
plan_detection:
  check: "Does an approved plan exist in context or on disk?"

  sources:
    - "Recent conversation (plan validated by user)"
    - "Claude session memory"
    - ".claude/plans/*.md (disk-persisted plans)"

  detection_workflow:
    1_check_explicit_flag:
      condition: "--plan <path> argument provided"
      action: "Read the specified plan file directly"
      priority: "HIGHEST"

    2_check_conversation:
      condition: "Plan visible in conversation context"
      action: "Use plan from conversation"
      priority: "HIGH"
      signals:
        - "User said 'yes', 'ok', 'go', 'approved' after a /plan"
        - "Structured plan with numbered steps visible"
        - "ExitPlanMode was called successfully"

    3_check_disk_plans:
      condition: "No plan found in conversation context"
      action: "Glob .claude/plans/*.md, read most recent"
      priority: "MEDIUM (conversation is fresher than disk)"

  priority_rule: "Explicit flag > Conversation > Disk"

  if_plan_found:
    mode: "PLAN_EXECUTION"
    actions:
      - "Extract: title, steps[], scope, files[]"
      - "Check for 'Context:' header line in plan"
      - "If context path found → Read .claude/contexts/{slug}.md"
      - "Load discoveries, relevant_files, implementation_notes into working memory"
      - "Skip Phase 0 (interactive questions)"
      - "Use plan steps as sub-objectives"
      - "Criteria = plan completed + tests/lint/build pass"

  context_recovery:
    trigger: "Plan file contains 'Context: .claude/contexts/{slug}.md' header"
    workflow:
      1_extract_path: "Parse 'Context:' line from plan header"
      2_read_context: "Read .claude/contexts/{slug}.md if exists"
      3_load_sections:
        discoveries: "Key findings from planning phase"
        relevant_files: "Files to focus on"
        implementation_notes: "Technical decisions and constraints"
      4_graceful_degradation: "If context file missing → warn and proceed without"
    purpose: "Restore full planning context after 'clear context' or compaction"

  if_no_plan:
    mode: "ITERATIVE"
    actions:
      - "Continue to Phase 0 (questions)"
```

**Output Phase 1.0 (plan detected):**

```
═══════════════════════════════════════════════════════════════
  /do - Plan Detection
═══════════════════════════════════════════════════════════════

  ✓ Approved plan detected!

  Source : conversation | .claude/plans/{slug}.md
  Plan   : "Add JWT authentication to API"
  Context: .claude/contexts/{slug}.md (loaded)
  Steps  : 4
  Scope  : src/auth/, src/middleware/
  Files  : 6 to modify, 2 to create

  Mode: PLAN_EXECUTION (skipping interactive questions)

  Proceeding to Phase 4.0 (Peek)...

═══════════════════════════════════════════════════════════════
```

**Output Phase 1.0 (no plan):**

```
═══════════════════════════════════════════════════════════════
  /do - Plan Detection
═══════════════════════════════════════════════════════════════

  No approved plan found.

  Mode: ITERATIVE (interactive questions required)

  Proceeding to Phase 3.0 (Questions)...

═══════════════════════════════════════════════════════════════
```

---

## Phase 2.0: Secret Discovery (1Password)

**Check if secrets are available for this project:**

```yaml
secret_discovery:
  trigger: "ALWAYS (before Phase 0)"
  blocking: false  # Informational only

  1_check_available:
    condition: "command -v op && test -n $OP_SERVICE_ACCOUNT_TOKEN"
    on_failure: "Skip silently (1Password not configured)"

  2_resolve_path:
    action: "Extract org/repo from git remote origin"
    command: |
      REMOTE=$(git config --get remote.origin.url)
      # Extract org/repo from HTTPS, SSH, or token-embedded URLs
      PROJECT_PATH=$(echo "${REMOTE%.git}" | grep -oP '[:/]\K[^/]+/[^/]+$')

  3_list_project_secrets:
    action: "List project secrets"
    command: |
      op item list --vault='$VAULT_ID' --format=json \
        | jq -r '.[] | select(.title | startswith("'$PROJECT_PATH'/")) | .title'
    extract: "Remove prefix to keep key names only"

  4_check_task_needs:
    action: "If the task mentions secret/token/credential/password/API key"
    match_keywords: ["secret", "token", "credential", "password", "api key", "api_key", "auth"]
    if_match_and_secrets_exist:
      output: |
        ═══════════════════════════════════════════════════════════════
          /do - Secrets Available
        ═══════════════════════════════════════════════════════════════

          Project: {PROJECT_PATH}
          Available secrets in 1Password:
            ├─ DB_PASSWORD
            ├─ API_KEY
            └─ JWT_SECRET

          Use /secret --get <key> to retrieve a value
          These may help with the current task.

        ═══════════════════════════════════════════════════════════════
    if_no_secrets:
      output: "(no project secrets in 1Password, continuing...)"
```

---

## Phase 3.0: Interactive Questions (IF NO PLAN)

**Ask these 4 questions ONLY if no approved plan is detected:**

### Question 1: Task Type

```yaml
AskUserQuestion:
  questions:
    - question: "What type of task do you want to accomplish?"
      header: "Type"
      multiSelect: false
      options:
        - label: "Refactor/Migration (Recommended)"
          description: "Migrate a framework, refactor existing code"
        - label: "Test Coverage"
          description: "Add tests to reach a coverage threshold"
        - label: "Standardization"
          description: "Apply consistent patterns (errors, style)"
        - label: "Greenfield"
          description: "Create a new project/module from scratch"
```

### Question 2: Max Iterations

```yaml
AskUserQuestion:
  questions:
    - question: "How many maximum iterations to allow?"
      header: "Iterations"
      multiSelect: false
      options:
        - label: "10 (Recommended)"
          description: "Sufficient for most tasks"
        - label: "20"
          description: "For moderately complex tasks"
        - label: "30"
          description: "For major migrations/refactorings"
        - label: "50"
          description: "For complete greenfield projects"
```

### Question 3: Success Criteria

```yaml
AskUserQuestion:
  questions:
    - question: "Which success criteria to use?"
      header: "Criteria"
      multiSelect: true
      options:
        - label: "Tests pass (Recommended)"
          description: "All unit tests must be green"
        - label: "Clean lint"
          description: "No linter errors"
        - label: "Build succeeds"
          description: "Compilation must work"
        - label: "Coverage >= X%"
          description: "Coverage threshold to reach"
```

### Question 4: Scope

```yaml
AskUserQuestion:
  questions:
    - question: "What scope for this task?"
      header: "Scope"
      multiSelect: false
      options:
        - label: "src/ folder (Recommended)"
          description: "All source code"
        - label: "Specific files"
          description: "I will specify the files"
        - label: "Entire project"
          description: "Includes tests, docs, config"
        - label: "Custom"
          description: "I will specify a path"
```

---

## Phase 4.0: Peek (RLM Pattern)

**Quick scan BEFORE any modification:**

```yaml
peek_workflow:
  0_git_check:
    action: "Check git status (conflict detection)"
    tools: [Bash]
    command: "git status --porcelain"
    checks:
      - "No merge/rebase in progress"
      - "Target files not already modified (warning if so)"
    on_conflict:
      action: "Warning + continue (not blocking)"
      message: "⚠ Uncommitted changes detected on target files"

  1_structure:
    action: "Scan the scope structure"
    tools: [Glob]
    patterns:
      - "src/**/*.{ts,js,go,py,rs}"
      - "tests/**/*"
      - "package.json | go.mod | Cargo.toml | pyproject.toml"

  2_patterns:
    action: "Identify existing patterns"
    tools: [Grep]
    searches:
      - "class.*Factory" → Factory pattern
      - "getInstance" → Singleton
      - "describe|test|it" → Existing tests

  3_stack_detect:
    action: "Detect the tech stack"
    checks:
      - "package.json → Node.js/npm"
      - "go.mod → Go"
      - "Cargo.toml → Rust"
      - "pyproject.toml → Python"
    output: "test_command, lint_command, build_command"
```

**Output Phase 4.0:**

```
═══════════════════════════════════════════════════════════════
  /do - Peek Analysis
═══════════════════════════════════════════════════════════════

  Git Status:
    ✓ Working tree clean (or: ⚠ 3 uncommitted changes)

  Scope      : src/
  Files      : 47 source files, 23 test files
  Stack      : Node.js (TypeScript)

  Patterns detected:
    ✓ Factory pattern (3 occurrences)
    ✓ Repository pattern (2 occurrences)
    ✓ Jest test suite (23 files)

  Commands:
    Test  : npm test
    Lint  : npm run lint
    Build : npm run build

═══════════════════════════════════════════════════════════════
```

---

## Phase 5.0: Decompose (RLM Pattern)

**Split the task into measurable sub-objectives:**

```yaml
decompose_workflow:
  1_analyze_task:
    action: "Extract the objectives from the task"
    example:
      task: "Migrate Jest to Vitest"
      objectives:
        - "Replace Jest dependencies with Vitest"
        - "Update the test config"
        - "Adapt imports in test files"
        - "Fix incompatible APIs"
        - "Verify that all tests pass"

  2_prioritize:
    action: "Order by dependency"
    principle: "Smallest change first"

  3_create_todos:
    action: "Initialize TaskCreate with sub-objectives"
```

**Output Phase 5.0:**

```
═══════════════════════════════════════════════════════════════
  /do - Task Decomposition
═══════════════════════════════════════════════════════════════

  Task: "Migrate Jest tests to Vitest"

  Sub-objectives (ordered):
    1. [DEPS] Replace jest → vitest in package.json
    2. [CONFIG] Create vitest.config.ts
    3. [IMPORTS] Adapt imports jest → vitest (23 files)
    4. [COMPAT] Fix incompatible APIs
    5. [VERIFY] All tests pass

  Strategy: Sequential with parallel validation

═══════════════════════════════════════════════════════════════
```

---

## Phase 6.0: Main Loop

```
┌──────────────────────────────────────────────────────────────┐
│  LOOP: while (iteration < max && !success)                   │
│                                                              │
│    1. Peek  → Read current state                             │
│    2. Apply → Minimal modifications                          │
│    3. Parallelize → Simultaneous validations                 │
│    4. Synthesize → Analyze results                           │
│    5. Decision → SUCCESS | CONTINUE | ABORT                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Step 3.1: Iterative Peek

```yaml
peek_iteration:
  action: "Read current state before modification"
  inputs:
    - "Previously modified files"
    - "Errors from last validation"
    - "Progress toward sub-objectives"
```

### Step 3.2: Apply (minimal modifications)

```yaml
apply_iteration:
  principle: "Smallest change that moves toward success"
  actions:
    - "Modify only the necessary files"
    - "Follow the project's existing patterns"
    - "Do not over-engineer"
  tracking:
    - "Add each modified file to the list"
```

### Step 3.3: Parallelize (simultaneous validations)

**Launch validations in PARALLEL via Task agents:**

```yaml
parallel_validation:
  agents:
    - task: "Run tests"
      command: "{test_command}"
      output: "test_result"

    - task: "Run linter"
      command: "{lint_command}"
      output: "lint_result"

    - task: "Run build"
      command: "{build_command}"
      output: "build_result"

  mode: "PARALLEL (single message, multiple Task calls)"
```

**IMPORTANT**: Launch all 3 validations in a SINGLE message.

### Step 3.4: Synthesize (result analysis)

```yaml
synthesize_iteration:
  collect:
    - "test_result.exit_code"
    - "test_result.passed / test_result.total"
    - "lint_result.error_count"
    - "build_result.exit_code"

  evaluate:
    all_success:
      condition: "test_exit == 0 && lint_exit == 0 && build_exit == 0"
      action: "EXIT with success report"

    partial_success:
      condition: "Some criteria met, some not"
      action: "CONTINUE with focused fixes"

    no_progress:
      condition: "Same errors 3 iterations in a row"
      action: "ABORT with blocker analysis"

  verification_gate:
    rule: "Evidence before claims. Previous runs don't count."
    mandatory_steps:
      1_IDENTIFY: "Which command proves the claim?"
      2_RUN: "Execute FRESHLY (no cache)"
      3_READ: "Lire output COMPLET + exit code"
      4_VERIFY: "Output confirme le claim?"
      5_CLAIM: "Seulement alors déclarer succès"
    red_flags:
      - "Hedging: 'should', 'probably', 'seems to'"
      - "Satisfaction before verification"
      - "Trust agent reports without independent verification"

  output: "Iteration summary"
```

**Output per iteration:**

```
═══════════════════════════════════════════════════════════════
  Iteration 3/10
═══════════════════════════════════════════════════════════════

  Modified: 5 files

  Validation (parallel):
    ├─ Tests : 18/23 PASS (5 failing)
    ├─ Lint  : 2 errors
    └─ Build : SUCCESS

  Analysis:
    - 5 tests use jest.mock() incompatible with vitest
    - 2 lint errors on unused imports

  Decision: CONTINUE → Focus on jest.mock migration

═══════════════════════════════════════════════════════════════
```

---

## Phase 7.0: Final Synthesis

### Success Report

```
═══════════════════════════════════════════════════════════════
  /do - Task Completed Successfully
═══════════════════════════════════════════════════════════════

  Task       : {original_task}
  Iterations : {n}/{max}

  ✓ All Criteria Met:
    - Tests: 23/23 PASS
    - Lint: 0 errors
    - Build: SUCCESS

  Files Modified ({count}):
    - package.json (+3, -3)
    - vitest.config.ts (+25, -0)
    - src/**/*.test.ts (23 files)

  Decomposition Results:
    ✓ [DEPS] Replaced dependencies
    ✓ [CONFIG] Created vitest config
    ✓ [IMPORTS] Adapted 23 test files
    ✓ [COMPAT] Fixed mock APIs
    ✓ [VERIFY] All tests pass

═══════════════════════════════════════════════════════════════
  IMPORTANT: Review the diff before merging!
  → git diff HEAD~{n}
═══════════════════════════════════════════════════════════════
```

### Failure Report

```
═══════════════════════════════════════════════════════════════
  /do - Task Stopped (Max Iterations / Blocker)
═══════════════════════════════════════════════════════════════

  Task       : {original_task}
  Iterations : {n}/{max}
  Reason     : {MAX_REACHED | BLOCKER_DETECTED | CIRCULAR_FIX}

  ✗ Criteria NOT Met:
    - Tests: 20/23 PASS (3 failing)
    - Lint: 0 errors

  Blockers Identified:
    1. tests/api.test.ts:45 - Cannot mock external service
    2. tests/db.test.ts:78 - Database connection required

  Decomposition Status:
    ✓ [DEPS] Replaced dependencies
    ✓ [CONFIG] Created vitest config
    ✓ [IMPORTS] Adapted 23 test files
    ✗ [COMPAT] 3 incompatible mocks
    ✗ [VERIFY] Tests failing

  Suggested Next Steps:
    1. Review failing tests manually
    2. Consider mocking strategy for external services
    3. Re-run with narrower scope

═══════════════════════════════════════════════════════════════
```

---

## Anti-patterns (Automatic Detection)

| Pattern | Symptom | Action |
|---------|---------|--------|
| **Circular fix** | Same file modified 3+ times | ABORT + alert |
| **No progress** | 0 improvement over 3 iterations | ABORT + diagnostic |
| **Scope creep** | Files outside scope modified | Rollback + warning |
| **Overbaking** | Inconsistent changes after 15+ iter | ABORT + report |
| **Architecture question** | 3+ failed fix attempts (same error category) | STOP + AskUserQuestion: "Is the architectural approach correct?" |

---

## TaskCreate Integration

```yaml
task_pattern:
  phase_0:
    - TaskCreate: { subject: "Configuration questions", activeForm: "Asking configuration questions" }
      → TaskUpdate: { status: "completed" }

  phase_1:
    - TaskCreate: { subject: "Peek: Analyze codebase", activeForm: "Analyzing codebase" }
      → TaskUpdate: { status: "in_progress" }

  phase_2:
    - TaskCreate: { subject: "{sub_objective_1}", activeForm: "Working on {sub_objective_1}" }
    - TaskCreate: { subject: "{sub_objective_2}", activeForm: "Working on {sub_objective_2}" }

  per_iteration:
    on_start: "TaskUpdate → status: in_progress"
    on_complete: "TaskUpdate → status: completed"
    on_blocked: "TaskCreate new blocker task"
    on_success: "TaskUpdate all → completed"
```

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Skip Phase 1.0 (Plan detect) | **FORBIDDEN** | Must check if plan exists |
| Skip Phase 3.0 without plan | **FORBIDDEN** | Questions required |
| Skip Phase 4.0 (Peek) | **FORBIDDEN** | Context + git check |
| Ignore max_iterations | **FORBIDDEN** | Infinite loop |
| Subjective criteria ("pretty", "clean") | **FORBIDDEN** | Not measurable |
| Modify .claude/ or .devcontainer/ | **FORBIDDEN** | Protected files |
| More than 50 iterations | **FORBIDDEN** | Safety limit |

### Legitimate Parallelization

| Element | Parallel? | Reason |
|---------|-----------|--------|
| Iterative loop (N → N+1) | Sequential | Iteration depends on previous result |
| Checks per iteration (lint+test+build) | Parallel | Independent of each other |
| Corrective actions | Sequential | Logical order required |

---

## Effective Prompt Examples

### Good: Measurable Criteria

```
/do "Migrate all Jest tests to Vitest"
→ Criterion: all tests pass with Vitest

/do "Add tests for src/utils with 80% coverage"
→ Criterion: coverage >= 80%

/do "Replace console.log with a structured logger"
→ Criterion: 0 console.log in src/, clean lint
```

### Bad: Subjective Criteria

```
/do "Make the code cleaner"
→ "Cleaner" is not measurable

/do "Improve performance"
→ No benchmark metric defined
```

---

## Integration with /review (Cyclic Workflow)

**`/review --loop` generates plans that `/do` executes automatically.**

```yaml
review_integration:
  detection:
    trigger: "plan filename contains 'review-fixes-'"
    location: ".claude/plans/review-fixes-*.md"

  mode: "REVIEW_EXECUTION"

  workflow:
    1_load_plan:
      action: "Read .claude/plans/review-fixes-{timestamp}.md"
      extract:
        - findings: [{file, line, fix_patch, language, specialist}]
        - priorities: ["CRITICAL", "HIGH", "MEDIUM"]

    2_group_by_language:
      action: "Group findings by file extension"
      example:
        ".go": ["finding1", "finding2"]
        ".ts": ["finding3"]

    3_dispatch_to_specialists:
      mode: "parallel (by language)"
      for_each_language:
        agent: "developer-specialist-{lang}"
        prompt: |
          You are the {language} specialist.

          ## Findings to Fix
          {findings_json}

          ## Constraints
          - Apply fixes in priority order (CRITICAL → HIGH)
          - Use fix_patch as starting point
          - Verify fix doesn't introduce new issues
          - Follow repo conventions

          ## Output
          For each fix applied:
          - File modified
          - Lines changed
          - Brief explanation

    4_validate:
      action: "Run quick /review (no loop) on modified files"
      check:
        - "Were original issues from the plan fixed?"
        - "Were any new CRITICAL/HIGH issues introduced?"

    5_report:
      action: "Summary of fixes applied"
      format: |
        Files modified: {n}
        Findings fixed: CRIT={a}, HIGH={b}, MED={c}
        New issues: {new_count}

    6_return_to_review:
      condition: "Called from /review --loop"
      action: "Return control to /review for re-validation"
```

**Language-Specialist Routing:**

| Extension | Specialist Agent |
|-----------|------------------|
| `.go` | `developer-specialist-go` |
| `.py` | `developer-specialist-python` |
| `.java` | `developer-specialist-java` |
| `.ts`, `.js` | `developer-specialist-nodejs` |
| `.rs` | `developer-specialist-rust` |
| `.rb` | `developer-specialist-ruby` |
| `.ex`, `.exs` | `developer-specialist-elixir` |
| `.php` | `developer-specialist-php` |
| `.c`, `.h` | `developer-specialist-c` |
| `.cpp`, `.cc`, `.hpp` | `developer-specialist-cpp` |
| `.cs` | `developer-specialist-csharp` |
| `.kt`, `.kts` | `developer-specialist-kotlin` |
| `.swift` | `developer-specialist-swift` |
| `.r`, `.R` | `developer-specialist-r` |
| `.pl`, `.pm` | `developer-specialist-perl` |
| `.lua` | `developer-specialist-lua` |
| `.f90`, `.f95`, `.f03` | `developer-specialist-fortran` |
| `.adb`, `.ads` | `developer-specialist-ada` |
| `.cob`, `.cbl` | `developer-specialist-cobol` |
| `.pas`, `.dpr`, `.pp` | `developer-specialist-pascal` |
| `.vb` | `developer-specialist-vbnet` |
| `.m` (Octave) | `developer-specialist-matlab` |
| `.asm`, `.s` | `developer-specialist-assembly` |
| `.scala` | `developer-specialist-scala` |
| `.dart` | `developer-specialist-dart` |

**Infrastructure/SysAdmin Task Routing:**

When the task involves infrastructure, system administration, or OS-level operations,
dispatch to the appropriate DevOps agents:

| Task Pattern | Agent | Dispatch |
|-------------|-------|----------|
| Terraform, IaC, cloud resources | `devops-orchestrator` | Coordinates infra specialists |
| Docker, containers, images | `devops-specialist-docker` | Container optimization |
| Kubernetes, Helm, K8s | `devops-specialist-kubernetes` | K8s orchestration |
| Security scanning, CVEs | `devops-specialist-security` | Vulnerability detection |
| Cost optimization, FinOps | `devops-specialist-finops` | Cloud cost analysis |
| AWS services | `devops-specialist-aws` | AWS best practices |
| GCP services | `devops-specialist-gcp` | GCP best practices |
| Azure services | `devops-specialist-azure` | Azure best practices |
| HashiCorp (Vault, Consul) | `devops-specialist-hashicorp` | HashiCorp stack |
| Linux sysadmin | `devops-executor-linux` | Routes to OS specialist |
| BSD sysadmin | `devops-executor-bsd` | Routes to BSD specialist |
| macOS sysadmin | `devops-executor-osx` | Routes to macOS specialist |
| Windows sysadmin | `devops-executor-windows` | Routes to Windows specialist |
| QEMU/KVM VMs | `devops-executor-qemu` | VM management |
| VMware vSphere | `devops-executor-vmware` | VMware operations |

**OS Executor Routing Chain:**

```
Task detected as OS-level
  → devops-executor-{linux|bsd|osx|windows}  (router)
    → os-specialist-{distro}                   (specialist)
      → Returns condensed JSON
    ← Merged into task result
```

---

## Integration with Other Skills

| Before /do | After /do |
|-----------|-----------|
| `/plan` (optional but recommended) | `/git --commit` |
| `/review` (generates plan) | `/review` (re-validate if --loop) |
| `/search` (if research needed) | N/A |

**Recommended workflow (standard plan):**

```
/search "vitest migration from jest"  # If research needed
    ↓
/plan "Migrate Jest tests"            # Plan the approach
    ↓
(user approves plan)                   # Human validation
    ↓
/do                                    # Detects the plan → executes
    ↓
(review diff)                          # Verify changes
    ↓
/git --commit                          # Commit + PR
```

**Cyclic workflow (with /review --loop):**

```
/review --loop 5                       # Analyze + generate fix plan
    ↓
/do (auto-triggered)                   # Execute via language-specialists
    ↓
/review (auto-triggered)               # Re-validate corrections
    ↓
(loop until no CRITICAL/HIGH OR limit)
    ↓
/git --commit                          # Commit corrections
```

**Quick workflow (without plan):**

```
/do "Fix all lint bugs"               # Simple + measurable task
    ↓
(iterations until success)
    ↓
/git --commit
```

**Note**: `/do` replaces `/apply`. The `/apply` skill is deprecated.
