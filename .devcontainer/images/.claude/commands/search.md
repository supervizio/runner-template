---
name: search
description: |
  Documentation Research with RLM (Recursive Language Model) patterns.
  LOCAL-FIRST: Searches internal docs (~/.claude/docs/) before external sources.
  Cross-validates sources, generates .claude/contexts/{slug}.md, handles conflicts.
  Use when: researching technologies, APIs, or best practices before implementation.
allowed-tools:
  - "WebSearch(*)"
  - "WebFetch(*)"
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "Grep(**/*)"
  - "Write(.claude/contexts/*.md)"
  - "Task(*)"
  - "AskUserQuestion(*)"
  - "mcp__context7__*"
  - "mcp__github__create_issue"
---

# Search - Documentation Research (RLM-Enhanced)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

---

## Description

Research with **LOCAL-FIRST** strategy and RLM patterns.

### Priority: Validated local documentation

```
~/.claude/docs/ (LOCAL)  →  Official sources (EXTERNAL)
     ✓ Validated             ⚠ May be outdated
     ✓ Consistent            ⚠ May contradict local
     ✓ Immediate             ⚠ Requires validation
```

**Applied RLM patterns:**

- **Local-First** - Consult `~/.claude/docs/` first
- **Peek** - Quick preview before full analysis
- **Grep** - Filter by keywords before semantic fetch
- **Partition+Map** - Parallel multi-domain searches
- **Summarize** - Progressive summarization of sources
- **Conflict-Resolution** - Handle local/external contradictions
- **Programmatic** - Structured context generation

**Principle**: Local > External. Reliability > Quantity.

---

## Arguments

| Pattern | Action |
|---------|--------|
| `<query>` | New search on the topic |
| `--append` | Append to existing context (by slug) |
| `--status` | Display current context |
| `--list` | List all available contexts |
| `--clear` | Delete specific context (by slug) |
| `--clear --all` | Delete all context files |
| `--help` | Display help |

---

## --help

```
═══════════════════════════════════════════════
  /search - Documentation Research (RLM)
═══════════════════════════════════════════════

Usage: /search <query> [options]

Options:
  <query>           Search topic
  --append          Append to existing context (by slug)
  --status          Display current context
  --list            List all available contexts
  --clear           Delete specific context (by slug)
  --clear --all     Delete all context files
  --help            Display this help

Output: .claude/contexts/{slug}.md
  Slug generated from query keywords (lowercase, hyphens, max 40 chars)
  Example: "OAuth2 JWT authentication" → oauth2-jwt-auth

RLM Patterns (always applied):
  1. Peek    - Quick preview of results
  2. Grep    - Filter by keywords
  3. Map     - 6 parallel searches
  4. Synth   - Multi-source synthesis (3+ for HIGH)

Examples:
  /search OAuth2 with JWT
  /search Kubernetes ingress --append
  /search --status

Workflow:
  /search <query> → iterate → EnterPlanMode
═══════════════════════════════════════════════
```

---

## Official sources (Whitelist)

**ABSOLUTE RULE**: ONLY the following domains.

### Languages
| Language | Domains |
|----------|---------|
| Node.js | nodejs.org, developer.mozilla.org |
| Python | docs.python.org, python.org |
| Go | go.dev, pkg.go.dev |
| Rust | rust-lang.org, doc.rust-lang.org |
| Java | docs.oracle.com, openjdk.org |
| C/C++ | cppreference.com, isocpp.org |
| C# / .NET | learn.microsoft.com, dotnet.microsoft.com |
| Ruby | ruby-lang.org, ruby-doc.org |
| PHP | php.net |
| Elixir | elixir-lang.org, hexdocs.pm |
| Kotlin | kotlinlang.org |
| Swift | swift.org, developer.apple.com |
| Scala | scala-lang.org, docs.scala-lang.org |
| Dart/Flutter | dart.dev, api.flutter.dev |
| Perl | perldoc.perl.org |
| Lua | lua.org |
| R | r-project.org, cran.r-project.org |
| Fortran | fortran-lang.org |
| Ada | ada-lang.io, learn.adacore.com |
| COBOL | gnucobol.sourceforge.io |
| Pascal | freepascal.org, lazarus-ide.org |

### Cloud & Infra

| Service | Domains |
|---------|---------|
| AWS | docs.aws.amazon.com |
| GCP | cloud.google.com |
| Azure | learn.microsoft.com |
| Docker | docs.docker.com |
| Kubernetes | kubernetes.io |
| Terraform | developer.hashicorp.com |
| GitLab | docs.gitlab.com |
| GitHub | docs.github.com |

### Frameworks
| Framework | Domains |
|-----------|---------|
| React | react.dev |
| Vue | vuejs.org |
| Next.js | nextjs.org |
| FastAPI | fastapi.tiangolo.com |

### Standards

| Type | Domains |
|------|---------|
| Web | developer.mozilla.org, w3.org |
| Security | owasp.org |
| RFCs | rfc-editor.org, tools.ietf.org |

### Blacklist

- ❌ Blogs, Medium, Dev.to
- ❌ Stack Overflow (except for problem identification)
- ❌ Third-party tutorials, online courses

---

## RLM Workflow (7 phases)

### Phase 1.0: Local documentation (LOCAL-FIRST)

**ALWAYS execute first. Local documentation is VALIDATED and takes priority.**

```yaml
local_first:
  source: "~/.claude/docs/"
  index: "~/.claude/docs/README.md"

  workflow:
    1_search_local:
      action: |
        Grep("~/.claude/docs/", pattern=<keywords>)
        Glob("~/.claude/docs/**/*.md", pattern=<topic>)
      output: [matching_files]

    2_read_matches:
      action: |
        FOR each matching_file:
          Read(matching_file)
          Extract: definition, examples, related patterns
      output: local_knowledge

    3_evaluate_coverage:
      rule: |
        IF local_knowledge covers >= 80% of the query:
          status = "LOCAL_COMPLETE"
          → Skip Phase 1-3, go to Phase 6
        ELSE IF local_knowledge covers >= 40%:
          status = "LOCAL_PARTIAL"
          → Continue Phase 0+ for gaps only
        ELSE:
          status = "LOCAL_NONE"
          → Continue normal workflow

  categories_mapping:
    design_patterns: "creational/, structural/, behavioral/"
    performance: "performance/"
    concurrency: "concurrency/"
    enterprise: "enterprise/"
    messaging: "messaging/"
    ddd: "ddd/"
    functional: "functional/"
    architecture: "architectural/"
    cloud: "cloud/, resilience/"
    security: "security/"
    testing: "testing/"
    devops: "devops/"
    integration: "integration/"
    principles: "principles/"
```

**Output Phase 1.0:**

```
═══════════════════════════════════════════════
  /search - Local Documentation Check
═══════════════════════════════════════════════

  Query    : <query>
  Keywords : <k1>, <k2>, <k3>

  Local Search (~/.claude/docs/):
    ├─ Matches: 3 files
    │   ├─ behavioral/observer.md (95% match)
    │   ├─ behavioral/README.md (70% match)
    │   └─ principles/solid.md (40% match)
    │
    └─ Coverage: 85% → LOCAL_COMPLETE

  Status: ✓ Using local documentation (validated)
  External search: SKIPPED (local sufficient)

═══════════════════════════════════════════════
```

**If LOCAL_PARTIAL:**

```
═══════════════════════════════════════════════
  /search - Local Documentation Check
═══════════════════════════════════════════════

  Query    : "OAuth2 JWT authentication"
  Keywords : OAuth2, JWT, authentication

  Local Search (~/.claude/docs/):
    ├─ Matches: 1 file
    │   └─ security/README.md (50% match)
    │
    └─ Coverage: 50% → LOCAL_PARTIAL

  Status: ⚠ Partial local coverage
  Gaps identified:
    ├─ OAuth2 flow details (not in local)
    └─ JWT implementation specifics (not in local)

  Action: External search for gaps only

═══════════════════════════════════════════════
```

---

### Phase 2.0: Decomposition (RLM Pattern: Peek + Grep)

**Analyze the query BEFORE any search:**

1. **Peek** - Identify complexity
   - Simple query (1 concept) → Direct Phase 1
   - Complex query (2+ concepts) → Decompose

2. **Grep** - Extract keywords
   ```
   Query: "OAuth2 with JWT for REST API"
   Keywords: [OAuth2, JWT, API, REST]
   Technologies: [OAuth2 → rfc-editor.org, JWT → tools.ietf.org]
   ```

3. **Systematic parallelization**
   - Always launch up to 6 Task agents in parallel
   - Cover all relevant domains

**Output Phase 0:**
```
═══════════════════════════════════════════════
  /search - RLM Decomposition
═══════════════════════════════════════════════

  Query    : <query>
  Keywords : <k1>, <k2>, <k3>

  Decomposition:
    ├─ Sub-query 1: <concept1> → <domain1>
    ├─ Sub-query 2: <concept2> → <domain2>
    └─ Sub-query 3: <concept3> → <domain3>

  Strategy: PARALLEL (6 Task agents max)

═══════════════════════════════════════════════
```

---

### Phase 3.0: Parallel search (RLM Pattern: Partition + Map)

**For each sub-query, launch a Task agent:**

```
Task({
  subagent_type: "Explore",
  prompt: "Search <concept> on <domain>. Extract: definition, usage, examples.",
  model: "haiku"  // Fast for search
})
```

**IMPORTANT**: Launch ALL agents in A SINGLE message (parallel).

**Multi-agent example:**
```
// Single message with 3 Task calls
Task({ prompt: "OAuth2 on rfc-editor.org", ... })
Task({ prompt: "JWT on tools.ietf.org", ... })
Task({ prompt: "REST API on developer.mozilla.org", ... })
```

---

### Phase 4.0: Peek at results

**Before full analysis, peek at each result:**

1. Read the first 500 characters of each response
2. Check relevance (score 0-10)
3. Filter irrelevant results (< 5)

```
Agent results:
  ✓ OAuth2 (score: 9) - RFC 6749 found
  ✓ JWT (score: 8) - RFC 7519 found
  ✗ REST (score: 3) - Result too generic
    → Relaunch with refined query
```

---

### Phase 5.0: Deep fetch (RLM Pattern: Summarization)

**For relevant results, WebFetch with summarization:**

```
WebFetch({
  url: "<found url>",
  prompt: "Summarize in 5 key points: 1) Definition, 2) Use cases, 3) Implementation, 4) Security, 5) Examples"
})
```

**Progressive summarization:**

- Level 1: Summary per source (5 points)
- Level 2: Merge summaries (synthesis)
- Level 3: Final context (actionable)

---

### Phase 6.0: Cross-referencing and validation

| Situation | Confidence | Action |
|-----------|------------|--------|
| Local + 2+ externals confirm | HIGHEST | Include (local takes priority) |
| Local only | HIGH | Include (validated) |
| 3+ external sources confirm | MEDIUM | Include + compare with local |
| 2 external sources confirm | LOW | Include + warning |
| 1 external source | VERIFY | Verify against local |
| Contradictory sources | CONFLICT | User resolution |
| 0 sources | NONE | Exclude |

**Contradiction detection LOCAL vs EXTERNAL:**

```yaml
conflict_detection:
  trigger: |
    IF external_info != local_info:
      status = "CONFLICT"
      action = "user_resolution"

  comparison:
    - Versions/dates
    - Syntax/API
    - Breaking changes
    - Best practices

  priority_rule: |
    LOCAL is ALWAYS considered VALIDATED.
    EXTERNAL may be outdated or incorrect.
```

---

### Phase 7.0: Conflict resolution (CONFLICT HANDLING)

**MANDATORY if conflict detected between local and external documentation.**

```yaml
conflict_resolution:
  step_1_notify_user:
    tool: AskUserQuestion
    prompt: |
      ⚠️ CONFLICT detected between local and external documentation

      **Topic:** {topic}

      **Local documentation (~/.claude/docs/):**
      {local_content}

      **External documentation ({source}):**
      {external_content}

      **Difference:**
      {diff_summary}

    questions:
      - question: "How to resolve this conflict?"
        header: "Resolution"
        options:
          - label: "Keep LOCAL"
            description: "Local doc is correct, ignore external"
          - label: "Update LOCAL"
            description: "External is more recent, create issue for update"
          - label: "Both valid"
            description: "Different contexts, document both"

  step_2_create_issue:
    condition: "user_choice == 'Update LOCAL'"
    tool: mcp__github__create_issue
    params:
      owner: "kodflow"
      repo: "devcontainer-template"
      title: "docs: Update {category}/{file} - conflict with official docs"
      body: |
        ## Conflict Report

        **Generated by:** `/search` skill
        **Date:** {ISO8601}

        ### Local Documentation
        **File:** `~/.claude/docs/{path}`
        **Content:**
        ```
        {local_excerpt}
        ```

        ### External Source
        **URL:** {external_url}
        **Content:**
        ```
        {external_excerpt}
        ```

        ### Difference
        {diff_description}

        ### Suggested Action
        - [ ] Review external source validity
        - [ ] Update local documentation if confirmed
        - [ ] Add version/date metadata

        ---
        _Auto-generated by /search conflict detection_
      labels:
        - "documentation"
        - "auto-generated"

  step_3_continue:
    action: |
      IF user_choice == "Keep LOCAL":
        → Use local info, ignore external
      IF user_choice == "Update LOCAL":
        → Issue created, use external with warning
      IF user_choice == "Both valid":
        → Document both contexts
```

**Output Phase 7.0:**

```
═══════════════════════════════════════════════
  /search - Conflict Resolution
═══════════════════════════════════════════════

  ⚠️ CONFLICT DETECTED

  Topic: Observer Pattern implementation

  Local (~/.claude/docs/behavioral/observer.md):
    → Uses EventEmitter interface
    → Recommends typed events

  External (developer.mozilla.org):
    → Uses addEventListener
    → Browser-specific API

  User Decision: "Both valid"
    → Local = Application patterns
    → External = Browser DOM events

  Issue: NOT CREATED (different contexts)

═══════════════════════════════════════════════
```

**Output if issue created:**

```
═══════════════════════════════════════════════
  /search - Conflict Resolution
═══════════════════════════════════════════════

  ⚠️ CONFLICT DETECTED

  Topic: JWT expiration handling

  Local (~/.claude/docs/security/jwt.md):
    → Recommends 15min access token

  External (tools.ietf.org/html/rfc7519):
    → No specific recommendation

  User Decision: "Update LOCAL"

  ✓ Issue created: kodflow/devcontainer-template#142
    Title: "docs: Update security/jwt.md - add RFC reference"

  Action: Using external info with warning

═══════════════════════════════════════════════
```

---

### Phase 8.0: Questions (if needed)

**ONLY if ambiguity detected:**

```
AskUserQuestion({
  questions: [{
    question: "The query mentions X and Y. Which one to prioritize?",
    header: "Priority",
    options: [
      { label: "X first", description: "Focus on X" },
      { label: "Y first", description: "Focus on Y" },
      { label: "Both", description: "Full search" }
    ]
  }]
})
```

**DO NOT ask if:**

- Query is clear and unambiguous
- Single technology
- Sufficient context

---

### Phase 9.0: Generate named context file (RLM Pattern: Programmatic)

**Slug generation from query keywords:**

```yaml
slug_generation:
  input: "OAuth2 JWT authentication for REST API"
  steps:
    1_extract: "oauth2 jwt authentication rest api"
    2_remove_stopwords: "oauth2 jwt authentication rest api"  # remove: for, the, a, an, with, to, of, in, on
    3_truncate: "oauth2-jwt-auth"  # max 40 chars, kebab-case, take first 3-5 significant words
  output: ".claude/contexts/oauth2-jwt-auth.md"
```

**Generate the file in a structured way:**

```markdown
# Context: <topic>

Generated: <ISO8601>
Query: <query>
Iterations: <n>
RLM-Depth: <parallel_agents_count>

## Summary

<2-3 sentences summarizing the findings>

## Key Information

### <Concept 1>

<Validated information>

**Sources:**
- [<Title>](<url>) - "<excerpt>"
- [<Title2>](<url>) - "<confirmation>"

**Confidence:** HIGH

### <Concept 2>

<Information>

**Sources:**
- [<Title>](<url>)

**Confidence:** MEDIUM

## Clarifications

| Question | Answer |
|----------|--------|
| <Q1> | <A1> |

## Recommendations

1. <Actionable recommendation>
2. <Actionable recommendation>

## Warnings

- ⚠ <Point of attention>

## Sources Summary

| Source | Domain | Confidence | Used In |
|--------|--------|------------|---------|
| RFC 6749 | rfc-editor.org | HIGH | §1 |
| RFC 7519 | tools.ietf.org | HIGH | §2 |

---
_Generated by /search (RLM-enhanced). Do not commit._
```

**Write to:** `.claude/contexts/{slug}.md`

---

## --append

Enrich existing context:

1. Generate slug from query keywords (same rules)
2. Read existing `.claude/contexts/{slug}.md`
3. Identify gaps (missing sections)
4. Search only for gaps
5. Merge without duplicates

---

## --list

List all available contexts:

```yaml
list_workflow:
  action: "Glob .claude/contexts/*.md"
  output: |
    ═══════════════════════════════════════════════
      /search - Available Contexts
    ═══════════════════════════════════════════════

      Contexts in .claude/contexts/:
        ├─ oauth2-jwt-auth.md (2024-01-15)
        ├─ kubernetes-ingress.md (2024-01-14)
        └─ react-server-components.md (2024-01-13)

      Total: 3 context files

    ═══════════════════════════════════════════════
```

---

## --status

Display the most recent context file content (or specific by slug).

---

## --clear

Delete context files:

```yaml
clear_workflow:
  "--clear <slug>": "Delete .claude/contexts/{slug}.md"
  "--clear": "Delete context matching current query slug"
  "--clear --all": "Delete all files in .claude/contexts/"
```

---

## Guardrails

| Action | Status |
|--------|--------|
| Skip Phase 1.0 (local documentation) | ❌ **FORBIDDEN** |
| Ignore local/external conflict | ❌ **FORBIDDEN** |
| Prefer external over local without validation | ❌ **FORBIDDEN** |
| Non-official source | ❌ FORBIDDEN |
| Skip Phase 2.0 (decomposition) | ❌ FORBIDDEN |
| Sequential agents when parallelizable | ❌ FORBIDDEN |
| Info without source | ❌ FORBIDDEN |

**ABSOLUTE LOCAL-FIRST RULE:**

```yaml
local_first_rule:
  priority: "LOCAL > EXTERNAL"
  reason: "Local documentation is validated and consistent"

  workflow:
    1: "ALWAYS search in ~/.claude/docs/ first"
    2: "IF local sufficient → use local only"
    3: "IF conflict → ask the user"
    4: "IF update needed → create GitHub issue"
```

---

## Execution examples

### Simple query

```
/search "Go context package"

→ 1 concept, 1 domain (go.dev)
→ Direct WebSearch + WebFetch
→ Validation 3+ sources
```

### Complex query

```
/search "OAuth2 JWT authentication for REST API"

→ 4 concepts, 3 domains
→ 6 parallel Task agents
→ Cross-reference fetch
→ RLM synthesis (3+ sources for HIGH)
```

### Multi-domain query

```
/search "Kubernetes ingress controller comparison"

→ 6 parallel Task agents
→ Coverage: kubernetes.io, docs.docker.com, cloud.google.com
→ Strict validation 3+ sources
```
