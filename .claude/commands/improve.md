---
name: improve
description: Documentation QA for Design Patterns. Audits consistency, completeness, freshness.
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "Grep(**/*)"
  - "Write(**/*)"
  - "Edit(**/*)"
  - "Task(*)"
  - "WebSearch(*)"
  - "WebFetch(*)"
---

# /improve - Documentation QA

$ARGUMENTS

## Scope

Target: `/workspace/.devcontainer/images/.claude/docs/`

## Options

| Option | Action |
|--------|--------|
| `--help` | Show help and stop |
| `--check` | Audit without modifications (default) |
| `--fix` | Auto-fix issues |
| `--category <name>` | Audit specific category only |

## Workflow

1. **Inventory**: Glob `**/*.md` in docs root
2. **Structure check**: Verify required sections per template
3. **Consistency check**: Validate table formats, links, naming
4. **Completeness check**: Compare against GoF, PoEAA, EIP catalogs
5. **Freshness check**: WebSearch for current best practices

## Required Sections

Pattern files must have:
- H1 title (`# Pattern Name`)
- Description blockquote (`> ...`)
- Go example (```go block)
- "Quand utiliser" section
- "Patterns liés" section

README files must have:
- Category H1 title
- Pattern table
- Decision table

## Scoring

| Grade | Score |
|-------|-------|
| A+ | 100% |
| A | 90-99% |
| B | 70-89% |
| C | 50-69% |
| F | <50% |

## Output

```
/improve - Documentation Audit
═════════════════════════════
Scanned: {n} files in {n} categories

Structure Issues:   {n}
Consistency Issues: {n}
Missing Patterns:   {n}

Overall Score: {grade}
═════════════════════════════
```

## Guardrails

- Never delete files
- Never modify without justification
- Always use templates for new patterns:
  - `TEMPLATE-PATTERN.md`
  - `TEMPLATE-README.md`

## Parallel Agents

For full audits, use Task tool with:
- `Explore` agent for structure/consistency
- `general-purpose` agent for freshness validation
