<!-- updated: 2026-02-27T13:00:00Z -->
# devcontainer-template

## Purpose

Universal DevContainer shell providing cutting-edge AI agents, skills, and workflows to bootstrap any project. Reliability first: agents reason deeply, cross-reference sources, and self-correct until the output meets quality standards.

## Project Structure

```
/workspace
├── .devcontainer/   # Container config, features, hooks, images
├── .github/         # GitHub Actions workflows
├── .githooks/       # Git hooks (pre-commit: regenerate assets)
├── src/             # All source code (mandatory)
├── tests/           # Unit tests (Go: alongside code in src/)
├── docs/            # Documentation (vision, architecture, workflows)
├── AGENTS.md        # Specialist agents specification
└── CLAUDE.md        # This file
```

## Tech Stack

- **Languages**: Python, C, C++, Java, C#, JavaScript/Node.js, Visual Basic, R, Pascal, Perl, Fortran, PHP, Rust, Go, Ada, MATLAB, Assembly, Kotlin, Swift, COBOL, Ruby, Dart, Lua, Scala, Elixir, SQL
- **Cloud CLIs**: AWS v2, GCP SDK, Azure CLI
- **IaC**: Terraform, Vault, Consul, Nomad, Packer, Ansible
- **Containers**: Docker, kubectl, Helm
- **AI**: Claude Code, MCP servers (GitHub, Codacy, Playwright, context7, grepai, Taskmaster)

## How to Work

1. **New project**: `/init` → conversational discovery → doc generation
2. **New feature**: `/plan "description"` → planning mode → `/do` → `/git --commit`
3. **Bug fix**: `/plan "description"` → planning mode → `/do` → `/git --commit`
4. **Code review**: `/review` → 5 specialist executors in parallel

Branch conventions: `feat/<desc>` or `fix/<desc>`, commit prefix matches.

## Key Principles

**Reliability first**: Verify before generating. Agents consult context7 and official docs before producing non-trivial code.

**MCP-first**: Use MCP tools (`mcp__github__*`, `mcp__codacy__*`) before CLI fallbacks. Auth is pre-configured.

**Self-correction**: When linting or tests fail, agents fix and retry automatically.

**Semantic search**: Use `grepai_search` for meaning-based queries. Fall back to Grep for exact strings.

**Specialist agents**: Language conventions enforced by agents that know current stable versions.

**Deep reasoning**: For complex tasks — Peek, Decompose, Parallelize, Synthesize.

## Safeguards

Ask before:
- Deleting files in `.claude/` or `.devcontainer/`
- Removing features from `.claude/commands/*.md`
- Removing hooks from `.devcontainer/hooks/`

When refactoring: move content to separate files, preserve logic.

## Pre-commit

Auto-detected by language marker (`go.mod`, `Cargo.toml`, `package.json`, etc.). Priority: Makefile targets, then language-specific commands.

## Hooks

| Hook | Purpose |
|------|---------|
| pre-validate | Protect sensitive files |
| post-edit | Format + lint |
| security | Secret detection + auto-correct --force |
| test | Run related tests |
| on-stop | Session summary + terminal bell |
| notification | External monitoring notifications |
| session-init | Cache project metadata as env vars |

## /secret - Secure Secret Management (1Password)

```
/secret --push DB_PASSWORD=mypass     # Store secret
/secret --get DB_PASSWORD             # Retrieve secret
/secret --list                        # List project secrets
/secret --push KEY=val --path org/other  # Cross-project
```

**Path convention:** `<org>/<repo>/<key>` (auto-resolved from git remote)
**Backend:** 1Password CLI (`op`) with `OP_SERVICE_ACCOUNT_TOKEN`
**Integration:** `/init` (check), `/git` (scan), `/do` (discover), `/infra` (TF_VAR_*)

## Documentation Hierarchy

```
CLAUDE.md                    # This overview
├── AGENTS.md                # Specialist agents (79 agents)
├── docs/vision.md           # Objectives, success criteria
├── docs/architecture.md     # System design, components
├── docs/workflows.md        # Detailed workflows
├── .devcontainer/CLAUDE.md  # Container config details
│   ├── features/CLAUDE.md   # Language & tool features
│   ├── hooks/CLAUDE.md      # Lifecycle hooks delegation
│   └── images/CLAUDE.md     # Base image (170 lines)
└── .claude/commands/        # Slash commands (17 skills)
```

Principle: More detail deeper in tree. Target < 200 lines each.

## Commands

| Command | Purpose |
|---------|---------|
| `/init` | Conversational project discovery + doc generation |
| `/plan` | Analyze codebase and design implementation approach |
| `/do` | Execute approved plans iteratively |
| `/review` | Code review with 5 specialist agents |
| `/git` | Conventional commits, branch management |
| `/search` | Documentation research with official sources |
| `/docs` | Deep project documentation generation |
| `/test` | E2E testing with Playwright MCP |
| `/lint` | Intelligent linting with ktn-linter |
| `/infra` | Infrastructure automation (Terraform/Terragrunt) |
| `/secret` | Secure secret management (1Password) |
| `/vpn` | Multi-protocol VPN management |
| `/warmup` | Context pre-loading and CLAUDE.md update |
| `/update` | DevContainer update from template |
| `/improve` | Documentation QA for design patterns |
| `/feature` | Feature tracking RTM (CRUD, audit, auto-learn) |
| `/prompt` | Generate ideal prompt structure for /plan requests |

## Verification

Changes are complete when:
- Tests pass (`make test` or language equivalent)
- Linting passes (auto-run by hooks)
- No secrets in commits (checked by security hook)
- Commit follows conventional format
