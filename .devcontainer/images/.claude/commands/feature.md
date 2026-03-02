---
name: feature
description: |
  Feature tracking with RTM (Requirements Traceability Matrix).
  CRUD operations, auto-learn from code changes, parallel audit.
allowed-tools:
  - "Read(**/*)"
  - "Write(.claude/**)"
  - "Edit(.claude/**)"
  - "Glob(**/*)"
  - "Grep(**/*)"
  - "Bash(jq:*)"
  - "Bash(mkdir:*)"
  - "Bash(cp:*)"
  - "Bash(mv:*)"
  - "Bash(date:*)"
  - "Bash(wc:*)"
  - "Task(*)"
  - "TaskCreate(*)"
  - "TaskUpdate(*)"
  - "TaskList(*)"
  - "TaskGet(*)"
  - "AskUserQuestion(*)"
  - "mcp__grepai__*"
  - "mcp__taskmaster__*"
---

# /feature - Feature Tracking RTM (Requirements Traceability Matrix)

$ARGUMENTS

---

## Overview

Track project features with full traceability: CRUD, audit, auto-learn.

**Database:** `.claude/features.json` (git-committed, no secrets)

---

## --help

```text
═══════════════════════════════════════════════════════════════
  /feature - Feature Tracking RTM
═══════════════════════════════════════════════════════════════

  DESCRIPTION
    Manage project features with full traceability.
    Hierarchical CRUD, wave-based audit, auto-learn from code.

  USAGE
    /feature --add "title" --desc "..." [--level N] [--workdirs "..."] [--audit-dirs "..."]
    /feature --edit <id> [--title "..."] [--desc "..."] [--status ...] [--level N] [--workdirs "..."] [--audit-dirs "..."]
    /feature --del <id>                           Delete (confirm)
    /feature --list                               Hierarchy tree
    /feature --show <id>                          Detail + journal
    /feature --checkup                            Wave audit ALL
    /feature --checkup <id>                       Audit one feature
    /feature --help                               This help

  STATUSES
    pending | in_progress | completed | blocked | archived

  LEVELS
    Level 0 : Top-level architectural features (e.g., DDD Architecture)
    Level 1 : Major subsystem features (e.g., HTTP Server, Database)
    Level 2+: Specific components (e.g., Auth middleware, Query builder)

    Parent-child: inferred at runtime from level + audit_dirs overlap.
    Direction: corrections flow DOWNWARD only (parent → child).

  DATABASE
    .claude/features.json (git-committed)
    Schema version: 2

  EXAMPLES
    /feature --add "DDD Architecture" --desc "Domain-driven design" --level 0 --workdirs "src/domain/,src/infrastructure/" --audit-dirs "src/"
    /feature --add "HTTP Server" --desc "REST API layer" --level 1 --workdirs "src/api/"
    /feature --edit F001 --status completed
    /feature --list
    /feature --checkup

═══════════════════════════════════════════════════════════════
```

**IF `$ARGUMENTS` contains `--help`**: Display the help above and STOP.

---

## Phase 1: Init + Migration

**Always runs first. Ensure `.claude/features.json` exists and is v2.**

```yaml
init:
  check: "Read .claude/features.json"
  if_missing:
    action: |
      Write .claude/features.json with:
      {
        "version": 2,
        "features": []
      }
    message: "Created .claude/features.json (schema v2)"

  if_exists:
    read_version: "Parse .version from JSON"

    if_version_1:
      action: |
        FOR each feature in .features[]:
          ADD fields: "level": 0, "workdirs": [], "audit_dirs": []
          APPEND to journal:
            { "ts": now, "action": "modified", "detail": "Migrated to schema v2: added level, workdirs, audit_dirs" }
        SET .version = 2
        Write updated .claude/features.json
      message: "Migrated features.json from v1 → v2 ({n} features updated)"

    if_version_2:
      action: "Load into working memory"
```

---

## Phase 2: CRUD Operations

### --add "title" --desc "description" [--level N] [--workdirs "..."] [--audit-dirs "..."]

```yaml
add_feature:
  1_generate_id:
    action: "Auto-increment: find max existing ID number, +1"
    format: "F001, F002, F003, ..."

  2_parse_args:
    level: "from --level (default 0, integer >= 0)"
    workdirs: "from --workdirs (comma-separated, normalize trailing /). Prompted if missing."
    audit_dirs: "from --audit-dirs (comma-separated, default = workdirs)"
    validation: |
      IF --workdirs missing: ask user
      Normalize: ensure each dir ends with /
      IF level > 5: ERROR "Level must be <= 5" → reject input
      IF workdirs empty after prompt: ERROR "workdirs required" → reject input

  3_create_entry:
    fields:
      id: "{generated_id}"
      title: "{from --add argument}"
      description: "{from --desc argument, or ask user}"
      status: "pending"
      tags: "[]  # Ask user for optional tags"
      level: "{parsed level}"
      workdirs: "[parsed workdirs array]"
      audit_dirs: "[parsed audit_dirs array]"
      created: "{ISO 8601 now}"
      updated: "{ISO 8601 now}"
      journal:
        - ts: "{ISO 8601 now}"
          action: "created"
          detail: "Initial feature definition"

  4_write:
    action: "Edit .claude/features.json, append to features array"

  5_infer_parent:
    action: "Run infer_hierarchy, find parent for this feature"
    output: "Parent info (if level > 0 and parent found)"

  6_output:
    format: |
      ═══════════════════════════════════════════════════════════════
        Feature Created
      ═══════════════════════════════════════════════════════════════
        ID       : {id}
        Title    : {title}
        Level    : {level}
        Workdirs : {workdirs}
        Parent   : {parent_id}: {parent_title} (or "none / root")
        Status   : pending
      ═══════════════════════════════════════════════════════════════
```

### --edit \<id\> [--title "..."] [--desc "..."] [--status ...] [--tags ...] [--level N] [--workdirs "..."] [--audit-dirs "..."]

```yaml
edit_feature:
  1_find: "Locate feature by ID in features array"
  2_update: |
    Update only specified fields.
    For --level: integer >= 0. Warn if > 5.
    For --workdirs/--audit-dirs: comma-separated, normalize trailing /.
  3_journal: |
    Append entry:
      { ts: now, action: "modified", detail: "Updated {changed_fields}" }
    If --status changed:
      { ts: now, action: "status_change", detail: "from → to" }
  4_compact: |
    If journal has > 50 entries:
      Summarize oldest entries into single "compacted" entry
  5_write: "Save updated features.json"
```

### --del \<id\>

```yaml
delete_feature:
  1_find: "Locate feature by ID"
  2_check_children:
    action: "Run infer_hierarchy, find children of this feature"
    if_has_children:
      warn: "Feature {id} has {n} inferred children: {child_ids}"
      extra_option: "Cascade archive children"
  3_confirm:
    tool: AskUserQuestion
    question: "Delete feature {id}: {title}? This cannot be undone."
    options:
      - label: "Yes, delete"
        description: "Permanently remove this feature"
      - label: "Archive instead"
        description: "Set status to archived (recoverable)"
      - label: "Cascade archive (with children)"
        description: "Archive this feature and all inferred children"
        condition: "Only shown if has_children"
  4_execute:
    if_delete: "Remove from features array"
    if_archive: "Set status to archived, add journal entry"
    if_cascade: |
      Set this feature + all inferred children to archived.
      Add journal entry to each: { action: "status_change", detail: "Cascade archived via parent {id}" }
  5_write: "Save updated features.json"
```

### --list

```yaml
list_features:
  1_load: "Read features.json"
  2_infer: "Run infer_hierarchy to build parent-child tree"
  3_display:
    action: "Render indented hierarchy tree"
    format: |
      ═══════════════════════════════════════════════════════════════
        /feature --list ({n} features)
      ═══════════════════════════════════════════════════════════════

        F001  [L0] DDD Architecture       | completed   | src/
        ├─ F002  [L1] HTTP Server         | in_progress | src/api/
        │  └─ F004  [L2] Auth middleware  | pending     | src/api/auth/
        └─ F003  [L1] Database layer      | completed   | src/models/
        F005  [L0] CI/CD Pipeline         | in_progress | .github/

        Orphans (no parent found):
          ⚠ F006  [L1] Logging            | pending     | lib/log/

      ═══════════════════════════════════════════════════════════════

    tree_algorithm: |
      1. Group features by level (0, 1, 2, ...)
      2. For each root (level 0): render, then recurse children
      3. Use tree connectors: ├─ (mid), └─ (last), │ (vertical)
      4. Show [LN] tag for level
      5. Show first workdir as path indicator
      6. Orphans (level > 0 with no parent) listed separately with ⚠
```

### --show \<id\>

```yaml
show_feature:
  action: "Display full feature detail + hierarchy + journal"
  steps:
    1_load: "Read feature by ID"
    2_infer: "Run infer_hierarchy for parent/children context"
  format: |
    ═══════════════════════════════════════════════════════════════
      Feature {id}: {title}
    ═══════════════════════════════════════════════════════════════

      Status      : {status}
      Level       : {level}
      Tags        : {tags}
      Workdirs    : {workdirs}
      Audit dirs  : {audit_dirs}
      Created     : {created}
      Updated     : {updated}

      Description:
        {description}

      Hierarchy:
        Parent   : {parent_id}: {parent_title} (or "none / root")
        Children : {child_id}: {child_title}, ... (or "none")

      Journal ({n} entries):
        {ts} | {action} | {detail}
        {ts} | {action} | {detail} | files: {files}
        ...

    ═══════════════════════════════════════════════════════════════
```

---

## Hierarchy Inference (Runtime, No Storage)

**Reusable algorithm referenced by `--list`, `--show`, `--checkup`, `--add`, `--del`.**

```yaml
infer_hierarchy:
  input: "features[] from features.json (status != archived)"
  output: "{ parent_map: {child_id → parent_id}, children_map: {parent_id → [child_ids]} }"

  algorithm: |
    1. Sort features by level ascending
    2. FOR each feature F at level N > 0:
       a. Candidates = features at level N-1 whose audit_dirs overlap F.workdirs
          Overlap test: any audit_dir of candidate is a prefix of any workdir of F
       b. IF multiple candidates: pick longest prefix match
       c. IF no candidate: F is orphan (emit warning)
       d. Record parent_map[F.id] = candidate.id
    3. Invert parent_map → children_map

  examples:
    - F001 (L0, audit_dirs=["src/"]) + F002 (L1, workdirs=["src/api/"])
      → F002 is child of F001 ("src/" is prefix of "src/api/")
    - F001 (L0, audit_dirs=["src/"]) + F003 (L0, audit_dirs=["tests/"])
      → No relationship (same level)
    - F004 (L2, workdirs=["lib/log/"]) with no L1 whose audit_dirs cover "lib/log/"
      → F004 is orphan

  constraints:
    - Level 0 features are always roots (never have parents)
    - Relationships are inferred, NEVER stored in features.json
    - Corrections flow DOWNWARD only (parent → child, never child → parent)
```

---

## Phase 3: --checkup (Wave-Based Audit)

```yaml
checkup_workflow:
  1_load_and_infer:
    action: "Read .claude/features.json, filter status != archived"
    infer: "Run infer_hierarchy → parent_map, children_map"
    output: "active_features[], waves (grouped by level)"

  2_determine_scope:
    if_id_provided: "Audit only the specified feature (single wave)"
    if_no_id: "Audit ALL active features (multi-wave)"

  3_compute_waves:
    action: |
      Group features by level: wave_0 = level 0, wave_1 = level 1, ...
      Execution order: wave 0 first, then wave 1, then wave 2, ...
      Max 8 parallel agents per wave.

  4_execute_waves:
    mode: "Sequential waves, parallel agents within each wave"
    per_wave:
      per_feature:
        subagent_type: "Explore"
        model: "haiku"
        prompt: |
          Audit feature {id}: "{title}" [Level {level}]
          Description: {description}
          Status: {status}
          Workdirs: {workdirs}
          Audit dirs: {audit_dirs}
          Journal (last 5): {last_5_journal_entries}
          Parent audit result: {parent_result_json or "N/A (root)"}

          TASKS:
          1. Search codebase (grepai_search) for files in workdirs related to this feature
          2. Verify implementation matches description
          3. Identify gaps (described but not implemented)
          4. Identify possible improvements
          5. If parent result provided: check alignment with parent's standards
          6. Conformity score: PASS / PARTIAL / FAIL

          Return JSON:
          { "id": "...", "conformity": "...", "gaps": [], "improvements": [], "related_files": [] }

  5_auto_correction:
    trigger: "After each wave N completes"
    action: |
      FOR each child at wave N+1 with conformity PARTIAL or FAIL:
        parent = parent_map[child.id]
        IF parent exists AND parent.conformity == PASS:
          Generate auto-correction plan: .claude/plans/auto-correct-{child_id}.md
          Journal entry on child:
            { action: "auto_corrected", detail: "Parent {parent_id} generated correction plan" }
    constraint: "Direction is DOWNWARD ONLY. Each wave N corrects direct children at N+1; deeper descendants (N+2, N+3...) are corrected when their own wave runs. NEVER upward."

  6_cross_feature_analysis:
    action: "Analyze results across all waves for contradictions"
    checks:
      - "Two features modify same files conflictually"
      - "Feature depends on incomplete feature"
      - "Contradictory descriptions"
      - "Parent PASS but child FAIL (alignment gap)"

  7_generate_report:
    format: |
      ═══════════════════════════════════════════════════════════════
        /feature --checkup - Wave Audit Report
      ═══════════════════════════════════════════════════════════════

        Features audited: {n}
        Waves executed: {wave_count}

        Wave 0 (Level 0):
          ├─ F001: ✓ PASS (DDD Architecture)
          └─ F005: ✓ PASS (CI/CD Pipeline)

        Wave 1 (Level 1):
          ├─ F002: ⚠ PARTIAL (HTTP Server - 2 gaps)
          │  ↳ Auto-correction plan from parent F001
          └─ F003: ✓ PASS (Database layer)

        Wave 2 (Level 2):
          └─ F004: ✗ FAIL (Auth middleware)
             ↳ Auto-correction plan from parent F002

        Cross-feature:
          ├─ Contradiction: F002 vs F003 on data access pattern
          └─ Dependency: F004 blocked by F002

        Actions:
          → F002: /plan generated (.claude/plans/auto-correct-F002.md)
          → F004: /plan generated (.claude/plans/auto-correct-F004.md)

      ═══════════════════════════════════════════════════════════════

  8_update_journal:
    action: |
      For each audited feature:
        Add journal entry:
          { action: "checkup_pass"|"checkup_fail", detail: "Conformity: {score}, wave: {N}" }

  9_auto_plan:
    condition: "PARTIAL or FAIL or contradiction detected (non-auto-corrected)"
    action: |
      For each problem not already auto-corrected:
        Generate .claude/plans/fix-{feature_id}-{slug}.md
        Add journal entry: { action: "plan_generated", detail: "..." }
```

---

## Journal Actions Reference

| Action | Trigger | Fields |
|--------|---------|--------|
| `created` | --add | detail |
| `modified` | --edit | detail, files? |
| `status_change` | --edit --status | detail (from → to) |
| `checkup_pass` | --checkup | detail |
| `checkup_fail` | --checkup | detail |
| `auto_corrected` | --checkup wave correction | detail (parent ID) |
| `plan_generated` | --checkup auto-plan | detail |
| `compacted` | Journal > 50 entries | detail (N events) |

---

## Journal Compaction

```yaml
compaction:
  trigger: "journal.length > 50 for any feature"
  action: |
    Keep last 50 entries.
    Summarize removed entries into:
      { ts: oldest_ts, action: "compacted", detail: "{N} events compacted" }
    Insert compacted entry at index 0.
  result: "Journal always has <= 51 entries (1 compacted + 50 recent)"
```

---

## Schema Reference (v2)

```json
{
  "version": 2,
  "features": [
    {
      "id": "F001",
      "title": "Short title (< 80 chars)",
      "description": "Detailed description of the feature",
      "status": "pending|in_progress|completed|blocked|archived",
      "tags": ["tag1", "tag2"],
      "level": 0,
      "workdirs": ["src/domain/", "src/infrastructure/"],
      "audit_dirs": ["src/"],
      "created": "ISO 8601",
      "updated": "ISO 8601",
      "journal": [
        {
          "ts": "ISO 8601",
          "action": "created|modified|status_change|checkup_pass|checkup_fail|auto_corrected|plan_generated|compacted",
          "detail": "Description of what happened",
          "files": ["optional/array/of/paths.ext"]
        }
      ]
    }
  ]
}
```

**v2 fields:**
- `level` (int, default 0): Hierarchy depth. 0 = root, 1 = subsystem, 2+ = component.
- `workdirs` (string[]): Directories this feature owns. Trailing `/` required.
- `audit_dirs` (string[]): Directories this feature can audit. Used for parent inference.

---

## Guardrails

| Action | Status | Reason |
|--------|--------|--------|
| Delete without confirmation | **FORBIDDEN** | Must use AskUserQuestion |
| Journal > 50 entries | **AUTO-COMPACT** | Keeps DB manageable |
| features.json > 500 features | **WARNING** | Consider archiving |
| Modify features.json schema | **FORBIDDEN** | Version migration needed |
| Store secrets in features.json | **FORBIDDEN** | Git-committed file |
| Auto-correct upward (child → parent) | **FORBIDDEN** | Corrections flow downward only |
| Delete parent with children | **WARN** | Offer cascade archive option |
| Level > 5 | **FORBIDDEN** | Reject input (must be <= 5) |
| Workdirs empty | **FORBIDDEN** | Reject input (required for hierarchy inference) |

---

## features.json vs Taskmaster

| Aspect | features.json (RTM) | Taskmaster |
|--------|---------------------|------------|
| **Scope** | Product-level features | Session-level tasks |
| **Persistence** | Git-committed, shared | Local `.taskmaster/`, gitignored |
| **Lifecycle** | Long-lived (days/weeks) | Ephemeral (hours/session) |
| **Purpose** | Track WHAT exists and WHY | Track HOW to implement NOW |
| **Audit** | `--checkup` verifies conformity | `next_task` guides workflow |
| **Example** | "JWT authentication" | "Write login endpoint test" |

**Rule:** Features describe capabilities. Tasks decompose work.
A feature spawns many tasks; a task belongs to at most one feature.

---

## Integration

| Skill | Integration |
|-------|-------------|
| `/init` | Propose --add for discovered features |
| `/warmup` | Load features.json into context |
| `/plan` | Reference features in plan context |
