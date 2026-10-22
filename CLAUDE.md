<!-- updated: 2026-09-29T00:00:00Z -->
# runner-template

## What this repository is

The **public** end-to-end runner of `supervizio/agent` and `supervizio/libprobe`
(both private), and the home of their **release contract**. It exists because a
public repository's GitHub-hosted minutes are free: the private repositories
dispatch their E2E matrices here and read the verdict back. Every job runs on a
GitHub-hosted runner; none targets the self-hosted fleet.

| Where | What |
|---|---|
| `.github/workflows/` | the E2E lanes, the contract's CI and proofs — `.github/workflows/CLAUDE.md` says what each workflow is for |
| `release-contract/` | the release contract (below) |
| `.github/actions/qemu-vm/` | the QEMU guest action used by `e2e.yml`'s Linux legs and by the proof workflows |
| `.github/solarish-leg/` | what `e2e.yml`'s illumos (OmniOS) and Solaris legs run in their guest: agent's binary and IPS archive, each installed through install.sh and run under SMF |
| `.github/nixos-leg/` | the NixOS system `e2e.yml`'s `nixos-nix` legs boot to install agent's Nix flake |
| everything else (`.devcontainer/`, `AGENTS.md`, the sections after this one) | the devcontainer template this repository was created from; it describes the template, not the E2E work |

## The release contract — `release-contract/`

The single source of truth for what a release of agent or libprobe must prove
before it leaves draft: the canonical asset manifest and its digest, the receipt
every release carries (`release-receipt.json`), the `validate-release` dispatch
payload, the required matrix per repository (`policy.json`), and the checks run
right before a draft is published.

- `release-contract/README.md` is normative; `release_contract.py` (stdlib Python
  ≥ 3.9) is its only implementation. agent's and libprobe's release workflows pin
  the directory by commit SHA and call the script — no rule is re-implemented
  elsewhere, in shell or otherwise.
- `.github/workflows/release-contract.yml` runs the validator's tests on Linux,
  macOS, Windows and Python 3.9, and re-derives the manifest test vector with
  coreutils alone. It proves the validator refuses what it must (altered manifest,
  re-pointed tag, missing, cancelled or timed-out leg, a verdict its results do not
  support) wherever it will run.
- `.github/workflows/release-contract-proof.yml` measures on live objects what the
  design stands on (who can read a draft release, whether GitHub's asset digests are
  the bytes' sha256, the validator against a real draft), and fails if any of it
  stops being true. It runs on `main` or by `workflow_dispatch`, never on a branch
  push, because its jobs hold `contents: write`.
- `.github/workflows/validate-release.yml` is the release lane: it validates a
  candidate pulled BY DIGEST from the private repository's own GHCR package
  (`ghcr.io/supervizio/{agent,libprobe}-release-candidates`, each granting this
  repository Read in its settings). `validate-release-doorbell.yml` wakes the
  private side afterwards; the private side builds the receipt from the run.
- `release-contract/harness/libprobe/` is the libprobe ABI consumer (`consumer.c`,
  only the published `probe.h` and `libprobe.a`) and its POSIX `run.sh`; the `abi`
  scenario stages and judges it (README section 5).
- Test locally: `python3 -m unittest discover -s release-contract/tests`.

## Rules specific to this repository

- It is **public**. Nothing private goes in it: no private branch names, no internal
  lab addresses or paths, no secrets, no content of the private repositories'
  releases.
  `private-addresses.yml` enforces the address part: no RFC 1918 address in any
  tracked file, documentation included (use placeholders such as `<host-ip>`).
  A job here never connects to a private network; if one ever needs a private
  endpoint it reads it from a repository secret, never from a variable (variables
  print unmasked in public logs).
- No binary is ever stored here, not even transiently as a release or an
  artifact: candidates stay in the private packages.
- `validate-release.yml` references no secret and never runs on `pull_request`;
  the doorbell is the lane's only secret-holder and executes nothing. README D3
  and section 4 say why.

## Product runs: what stays and for how long

A run of this public repository may hold agent's or libprobe's bytes while its
job runs; nothing of them may stay readable afterwards (supervizio/agent#297).
GitHub refuses to delete a run that is still in progress, so removal is always
done from outside the run: by the caller, by a `workflow_run` janitor, and
under both by `cleanup-product-runs.yml`.

| Workflow | Product bytes held during the job | Uploads (all `retention-days: 1`) | How the run goes |
|---|---|---|---|
| `e2e.yml` | merge lane: agent's checkout at the dispatched SHA and the binaries and packages of agent's CI run (App token, `actions: read`); release mode (called by `validate-release.yml`): the candidate's assets and test kit, pulled by digest | `probe-cap-*` (probe output JSON), `supervizio-arm64-packages` (arm64 packages rebuilt for the run's own legs) | `cleanup-external-e2e.yml` on completion (repository_dispatch runs); `cleanup-product-runs.yml` 30 min after completion (any event) |
| `external-e2e.yml` | libprobe's checkout at the dispatched SHA, built and tested on each leg | `report-*`, `metrics-reports` (runner metrics JSON) | same as `e2e.yml` |
| `agent-packages.yml` (stub; logic in kodflow/runner-template) | agent's cross-built binaries from its CI artifacts, a sparse checkout of its packaging files, the packages built from them | the packages, which agent's caller downloads | agent's `public-packages.yml` deletes it after downloading and fails if it is still listed; `sweep.yml` after 2 h; `cleanup-product-runs.yml` after 30 min |
| `libprobe-solarish.yml` (stub; logic in kodflow/runner-template) | libprobe's cross-built bundle | stage logs | libprobe's `solarish-guest.yml` deletes it after downloading the report; `sweep.yml`; `cleanup-product-runs.yml` |
| `validate-release.yml` | a release candidate's assets, pulled by digest from the private package | none | **kept**: its runs are the evidence a promotion reads (README D3); the repository retention setting removes them |

Rules, enforced by `.github/scripts/check_run_retention.py` (run by
`release-contract/tests/test_run_retention.py`, hence by `release-contract.yml`
on any workflow or action change); its docstring is the precise text:

- every `actions/upload-artifact` step has `retention-days: 1`, and per file
  the count of lines naming upload-artifact equals the count of
  `retention-days: 1` lines (the issue's own check: word comments otherwise);
- in a product workflow (the table above, plus `.github/actions/`), nothing
  writes the Actions cache: no `actions/cache`, every `actions/setup-*` says
  `cache: false`, no docker `type=gha`, no vmactions `cache-after-prepare:
  true`. A public repository's default-branch cache can be restored by any
  pull request's workflow, forks included, and it outlives the job;
- anywhere, an `actions/cache` path never names a product location;
- a new workflow that mentions a private repository, the App token, the
  release candidate action or a reusable lane fails the check until it is
  classified in the script.

Logs: a step that handles product files does not `set -x`, and does not print
hashes or `file`/`strings`-style output of product binaries (a mismatch says
"differs", not the two hashes). `::add-mask::` is not relied on.

Open, for the maintainer:

- **The three Alpine legs of `e2e.yml`** (`e2e-linux-alpine-{openrc,runit,s6}`)
  set `cache-after-prepare: true`: vmactions syncs the workspace (the package
  under test, agent's checkout) into the guest BEFORE `prepare`, so the
  prepared image it caches holds them. They need the reboot that option
  brings, for `psi=1` on the kernel command line. They are the check's only
  exception; the fix (a mounted rather than copied workspace, or the
  `qemu-vm` action's `kernel-args`) has to be proven on `main`, and the
  existing `alpine-*-prep-*` cache entries deleted.
- **Retention setting**: Actions artifact and log retention of this repository
  to 1 day (a repository/organisation setting, not a file here). README D1:
  commit statuses and check runs expire with the retention of the repository
  they are on.
- `validate-release.yml` runs are kept on purpose (above); whether their logs
  may outlive the job is a contract decision, not a cleanup one.

---

# Inherited: devcontainer-template

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
- **AI**: Claude Code, MCP servers (GitHub, Playwright, context7, grepai, Taskmaster)

## How to Work

1. **New project**: `/init` → conversational discovery → doc generation
2. **New feature**: `/plan "description"` → planning mode → `/do` → `/git --commit`
3. **Bug fix**: `/plan "description"` → planning mode → `/do` → `/git --commit`
4. **Code review**: `/review` → 5 specialist executors in parallel

Branch conventions: `feat/<desc>` or `fix/<desc>`, commit prefix matches.

## Key Principles

**Reliability first**: Verify before generating. Agents consult context7 and official docs before producing non-trivial code.

**MCP-first**: Use MCP tools (`mcp__github__*`) before CLI fallbacks. Auth is pre-configured.

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
