---
name: lint
description: |
  Intelligent linting with ktn-linter using RLM decomposition.
  Sequences 148 rules optimally across 8 phases.
  Fixes ALL issues automatically in intelligent order.
  Detects DTOs on-the-fly and applies dto:"direction,context,security" convention.
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
---

# /lint - Intelligent Linting (RLM Architecture)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Verify linter rule documentation when fixing complex violations
- Check framework-specific lint configurations

---

## AUTOMATIC WORKFLOW

This skill fixes **ALL** ktn-linter issues without exception.
No arguments. No flags. Just complete execution.

---

## IMMEDIATE EXECUTION

### Step 1: Run ktn-linter

```bash
./builds/ktn-linter lint ./... 2>&1
```

If the binary does not exist:

```bash
go build -o ./builds/ktn-linter ./cmd/ktn-linter && ./builds/ktn-linter lint ./...
```

### Step 2: Parse the output

For each error line with format `file:line:column: KTN-XXX-YYY: message`:

1. Extract the file
2. Extract the rule (KTN-XXX-YYY)
3. Extract the message
4. Classify into the appropriate phase

### Step 3: Classify by phase

**PHASE 1 - STRUCTURAL** (fix FIRST - affects other phases)

```text
KTN-STRUCT-ONEFILE   → Split multi-struct files OR add dto:"..."
KTN-TEST-SUFFIX      → Rename _test.go → _external_test.go or _internal_test.go
KTN-TEST-INTPRIV     → Move private tests to _internal_test.go
KTN-TEST-EXTPUB      → Move public tests to _external_test.go
KTN-TEST-PKGNAME     → Fix test package name
KTN-CONST-ORDER      → Move const to top of file
KTN-VAR-ORDER        → Move var after const
```

**PHASE 2 - SIGNATURES** (modify function signatures)

```text
KTN-FUNC-ERRLAST     → Put error as last return value
KTN-FUNC-CTXFIRST    → Put context.Context as first parameter
KTN-FUNC-MAXPARAM    → Group parameters or create struct
KTN-FUNC-NAMERET     → Add names to return values if >3
KTN-FUNC-GROUPARG    → Group params of same type
KTN-RECEIVER-MIXPTR  → Unify receiver (pointer or value)
KTN-RECEIVER-NAME    → Fix receiver name (1-2 chars)
```

**PHASE 3 - LOGIC** (fix logic errors)

```text
KTN-VAR-SHADOW       → Rename shadowing variable
KTN-CONST-SHADOW     → Rename const that shadows builtin
KTN-FUNC-DEADCODE    → Remove unused function
KTN-FUNC-CYCLO       → Refactor overly complex function
KTN-FUNC-MAXSTMT     → Split function >35 statements
KTN-FUNC-MAXLOC      → Split function >50 LOC
KTN-VAR-TYPEASSERT   → Add ok check on type assertion
KTN-ERROR-WRAP       → Use %w in fmt.Errorf
KTN-ERROR-SENTINEL   → Create package-level sentinel error
KTN-GENERIC-*        → Fix generic constraints
KTN-ITER-*           → Fix iterator patterns
KTN-GOVET-*          → Fix all govet issues
```

**PHASE 4 - PERFORMANCE** (memory optimizations)

```text
KTN-VAR-HOTLOOP      → Move allocation out of loop
KTN-VAR-BIGSTRUCT    → Pass by pointer if >64 bytes
KTN-VAR-SLICECAP     → Preallocate slice with capacity
KTN-VAR-MAPCAP       → Preallocate map with capacity
KTN-VAR-MAKEAPPEND   → Use make instead of append
KTN-VAR-GROW         → Use Buffer.Grow
KTN-VAR-STRBUILDER   → Use strings.Builder
KTN-VAR-STRCONV      → Avoid string() in loop
KTN-VAR-SYNCPOOL     → Use sync.Pool
KTN-VAR-ARRAY        → Use array if <=64 bytes
```

**PHASE 5 - MODERN** (Go 1.18-1.26 idioms)

```text
KTN-VAR-USEANY       → interface{} → any
KTN-VAR-USECLEAR     → delete loop → clear()
KTN-VAR-USEMINMAX    → math.Min/Max → min/max
KTN-VAR-RANGEINT     → for i := 0; i < n → for i := range n
KTN-VAR-LOOPVAR      → Remove loop variable copy (Go 1.22+)
KTN-VAR-SLICEGROW    → Use slices.Grow
KTN-VAR-SLICECLONE   → Use slices.Clone
KTN-VAR-MAPCLONE     → Use maps.Clone
KTN-VAR-CMPOR        → Use cmp.Or
KTN-VAR-WGGO         → Use WaitGroup.Go (Go 1.25+)
KTN-FUNC-MINMAX      → math.Min/Max → min/max
KTN-FUNC-USECLEAR    → clear() builtin
KTN-FUNC-RANGEINT    → range over int
MODERNIZE-*          → All modernize rules
```

**PHASE 6 - STYLE** (naming conventions)

```text
KTN-VAR-CAMEL        → snake_case → camelCase
KTN-CONST-CAMEL      → UPPER_CASE → UpperCase
KTN-VAR-MINLEN       → Rename var too short
KTN-VAR-MAXLEN       → Rename var too long
KTN-CONST-MINLEN     → Rename const too short
KTN-CONST-MAXLEN     → Rename const too long
KTN-FUNC-UNUSEDARG   → Prefix _ if unused
KTN-FUNC-BLANKPARAM  → Remove _ if not interface
KTN-FUNC-NOMAGIC     → Extract magic number into const
KTN-FUNC-EARLYRET    → Remove else after return
KTN-FUNC-NAKEDRET    → Add explicit return
KTN-STRUCT-NOGET     → GetX() → X()
KTN-INTERFACE-ERNAME → Add -er suffix
```

**PHASE 7 - DOCS** (documentation - LAST)

```text
KTN-COMMENT-PKGDOC   → Add package doc
KTN-COMMENT-FUNC     → Add function doc
KTN-COMMENT-STRUCT   → Add struct doc
KTN-COMMENT-CONST    → Add const doc
KTN-COMMENT-VAR      → Add var doc
KTN-COMMENT-BLOCK    → Add block comment
KTN-COMMENT-LINELEN  → Wrap line >100 chars
KTN-GOROUTINE-LIFECYCLE → Document goroutine lifecycle
```

**PHASE 8 - TESTS** (test patterns)

```text
KTN-TEST-TABLE       → Convert to table-driven
KTN-TEST-COVERAGE    → Add missing tests
KTN-TEST-ASSERT      → Add assertions
KTN-TEST-ERRCASES    → Add error cases
KTN-TEST-NOSKIP      → Remove t.Skip()
KTN-TEST-SETENV      → Fix t.Setenv in parallel
KTN-TEST-SUBPARALLEL → Add t.Parallel to subtests
KTN-TEST-CLEANUP     → Use t.Cleanup
```

---

## DTO Convention: dto:"direction,context,security"

**The dto:"..." tag exempts structs from KTN-STRUCT-ONEFILE and KTN-STRUCT-CTOR.**

### Format

```go
dto:"<direction>,<context>,<security>"
```

| Position | Values | Description |
|----------|--------|-------------|
| direction | `in`, `out`, `inout` | Flow direction |
| context | `api`, `cmd`, `query`, `event`, `msg`, `priv` | DTO type |
| security | `pub`, `priv`, `pii`, `secret` | Classification |

### Security Values

| Value | Logging | Marshaling | Usage |
|-------|---------|------------|-------|
| `pub` | Displayed | Included | Public data |
| `priv` | Displayed | Included | IDs, timestamps |
| `pii` | Masked | Conditional | Email, name (GDPR) |
| `secret` | REDACTED | Omitted | Password, token |

### Complete Example

```go
// File: user_dto.go - MULTIPLE DTOs (thanks to dto:"...")

type CreateUserRequest struct {
    Username string `dto:"in,api,pub" json:"username" validate:"required"`
    Email    string `dto:"in,api,pii" json:"email" validate:"email"`
    Password string `dto:"in,api,secret" json:"password" validate:"min=8"`
}

type UserResponse struct {
    ID        string    `dto:"out,api,pub" json:"id"`
    Username  string    `dto:"out,api,pub" json:"username"`
    Email     string    `dto:"out,api,pii" json:"email"`
    CreatedAt time.Time `dto:"out,api,pub" json:"createdAt"`
}

type UpdateUserCommand struct {
    UserID   string `dto:"in,cmd,priv" json:"userId"`
    Email    string `dto:"in,cmd,pii" json:"email,omitempty"`
}
```

### When to Add dto:"..."

| Situation | Action |
|-----------|--------|
| DTO/Request/Response struct | Add `dto:"dir,ctx,sec"` |
| Struct without tags (DTO) | Add `dto:"dir,ctx,sec"` |
| Struct with json/yaml/xml | OK, detected as DTO |
| KTN-STRUCT-ONEFILE DTO | dto tags → OK |

### Recognized Suffixes

```text
DTO, Request, Response, Params, Input, Output,
Payload, Message, Event, Command, Query
```

### Value Selection Guide

```text
DIRECTION:
  - User input → in
  - Output to client → out
  - Update/Patch → inout

CONTEXT:
  - REST/GraphQL API → api
  - CQRS Command → cmd
  - CQRS Query → query
  - Event sourcing → event
  - Message queue → msg
  - Internal → priv

SECURITY:
  - Product name, status → pub
  - IDs, timestamps → priv
  - Email, name, address → pii
  - Password, token, key → secret
```

---

## DTO Application Rules

```text
IF KTN-STRUCT-ONEFILE on a struct:
   1. Read the file
   2. Check if the struct should be a DTO (by NAME)
   3. IF yes → Add dto:"dir,ctx,sec" on each field
   4. Re-run the linter → no more ONEFILE error

IF KTN-STRUCT-CTOR on a struct:
   1. Check if DTO (by tags or name)
   2. IF DTO without tags → Add dto:"dir,ctx,sec"
   3. Re-run → no more CTOR error

IF KTN-DTO-TAG (invalid format):
   → Fix the format: dto:"direction,context,security"

IF KTN-STRUCT-JSONTAG:
   → Add the missing tag (json, xml, or dto depending on context)

IF KTN-STRUCT-PRIVTAG:
   → Remove tags from private fields
```

---

## Execution Mode: Agent Teams (Claude 4.6)

**If `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is enabled**, use Agent Teams to parallelize independent phases.

### Agent Teams Architecture

```text
LEAD (Phase 1-3: SEQUENTIAL - inter-file dependencies)
  Phase 1: STRUCTURAL (7 rules)
    ↓
  Phase 2: SIGNATURES (7 rules)
    ↓
  Phase 3: LOGIC (17 rules)
    ↓
  Re-run ktn-linter → validate Phase 1-3 convergence
    ↓
  === SPAWN 4 TEAMMATES ===
    ├── "perf"   → Phase 4 PERFORMANCE (11 rules)
    ├── "modern" → Phase 5 MODERN (20 rules)
    ├── "polish" → Phase 6 STYLE + Phase 7 DOCS (25 rules)
    └── "tester" → Phase 8 TESTS (8 rules)
    ↓
  LEAD: wait for all teammates to complete
    ↓
  Final re-run ktn-linter → validate global convergence
```

### Teammate Roles

**Lead**: Orchestrates the workflow. Executes Phase 1-3 (structural + signatures + logic) which have inter-file dependencies. After Phase 3 convergence, spawns the 4 teammates. Collects results and launches the final verification.

**Teammate "perf"** (Phase 4): Memory optimization specialist. Fixes: KTN-VAR-HOTLOOP, KTN-VAR-BIGSTRUCT, KTN-VAR-SLICECAP, KTN-VAR-MAPCAP, KTN-VAR-MAKEAPPEND, KTN-VAR-GROW, KTN-VAR-STRBUILDER, KTN-VAR-STRCONV, KTN-VAR-SYNCPOOL, KTN-VAR-ARRAY.

**Teammate "modern"** (Phase 5): Idiomatic Go specialist. Fixes: KTN-VAR-USEANY, KTN-VAR-USECLEAR, KTN-VAR-USEMINMAX, KTN-VAR-RANGEINT, KTN-VAR-LOOPVAR, KTN-VAR-SLICEGROW, KTN-VAR-SLICECLONE, KTN-VAR-MAPCLONE, KTN-VAR-CMPOR, KTN-VAR-WGGO, MODERNIZE-*.

**Teammate "polish"** (Phase 6+7): Style and documentation. Fixes: KTN-VAR-CAMEL, KTN-CONST-CAMEL, KTN-VAR-MINLEN/MAXLEN, KTN-FUNC-UNUSEDARG, KTN-FUNC-NOMAGIC, KTN-FUNC-EARLYRET, KTN-STRUCT-NOGET, KTN-INTERFACE-ERNAME + all KTN-COMMENT-*.

**Teammate "tester"** (Phase 8): Test quality. Fixes: KTN-TEST-TABLE, KTN-TEST-COVERAGE, KTN-TEST-ASSERT, KTN-TEST-ERRCASES, KTN-TEST-NOSKIP, KTN-TEST-SETENV, KTN-TEST-SUBPARALLEL, KTN-TEST-CLEANUP.

### User Interaction (VS Code)

- `Shift+Up/Down` to navigate between teammates
- Write directly to a teammate to guide its decisions
- Each teammate uses TaskCreate/TaskUpdate to report its progress

### Fallback: Sequential Mode

**If Agent Teams not available**, execute the classic mode:

```text
FOR each phase from 1 to 8:
    FOR each issue in this phase:
        1. Read the affected file
        2. IF struct DTO → apply dto:"dir,ctx,sec" convention
        3. Apply the fix
        4. TaskUpdate → completed
    END FOR
END FOR

Re-run ktn-linter to verify convergence
IF still issues: restart
ELSE: finish with report
```

---

## Final Report

```text
═══════════════════════════════════════════════════════════════
  /lint - COMPLETE
═══════════════════════════════════════════════════════════════

  Mode             : Agent Teams (4 teammates) | Sequential
  Issues fixed     : 47
  Iterations       : 3
  DTOs detected    : 4 (excluded from ONEFILE/CTOR)

  By phase:
    STRUCTURAL  : 5 fixed (including 2 via dto tags)  [Lead]
    SIGNATURES  : 8 fixed                              [Lead]
    LOGIC       : 12 fixed                             [Lead]
    PERFORMANCE : 4 fixed                              [perf]
    MODERN      : 10 fixed                             [modern]
    STYLE       : 5 fixed                              [polish]
    DOCS        : 3 fixed                              [polish]
    TESTS       : 0 fixed                              [tester]

  DTOs processed:
    - user_dto.go: CreateUserRequest, UserResponse (dto:"...,api,...")
    - order_dto.go: OrderCommand, OrderQuery (dto:"...,cmd/query,...")

  Final verification: 0 issues

═══════════════════════════════════════════════════════════════
```

---

## ABSOLUTE RULES

1. **Fix EVERYTHING** - No exceptions, no skips
2. **Phase ordering** - Phase 1→3 sequential, Phase 4→8 parallel (Agent Teams) or sequential (fallback)
3. **DTOs on-the-fly** - Detect and apply dto:"dir,ctx,sec"
4. **Iteration** - Re-run until 0 issues
5. **No questions** - Everything is automatic
6. **Strict dto format** - Always 3 values separated by comma
7. **TaskCreate** - Each phase = 1 task with progress

---

## START NOW

1. Run `./builds/ktn-linter lint ./...`
2. Parse the output
3. Classify by phase
4. Detect Agent Teams availability (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`)
5. IF Agent Teams: Lead Phase 1-3, spawn teammates Phase 4-8
6. ELSE: fix sequentially 1→8 (DTOs with dto:"dir,ctx,sec" convention)
7. Re-run until convergence
8. Display final report
