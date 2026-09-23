# runner-template

Public E2E test runner for [supervizio/agent](https://github.com/supervizio/agent).

This repository runs Docker and macOS E2E tests on **free** GitHub-hosted runners, keeping the agent repository's CI focused on build, lint, and unit tests.

## Architecture

```
supervizio/agent (CI)                    supervizio/runner-template (E2E)
┌──────────────────────────┐             ┌──────────────────────────────┐
│ lint → test → build      │             │ on: repository_dispatch      │
│ → packages → verify      │  dispatch   │ on: workflow_dispatch        │
│                          │ ──────────→ │                              │
│ dispatch-e2e ────────────│             │ resolve → e2e-docker         │
│                          │             │        → e2e-docker-arm64    │
│ summary ←────────────────│  commit     │        → e2e-macos           │
│   (reads commit status)  │  status     │        → e2e-macos-arm64     │
│                          │ ←────────── │        → report               │
└──────────────────────────┘             └──────────────────────────────┘
```

## How It Works

1. **Agent CI** builds binaries and uploads them as artifacts
2. **Agent CI** dispatches `run-e2e` event to this repo via `repository_dispatch`
3. **This repo** downloads artifacts cross-repo and runs E2E tests
4. **This repo** reports results back via GitHub Commit Status API
5. **Agent CI summary** sees the commit statuses on the PR

## Triggers

### Automatic (repository_dispatch)

Triggered by agent CI after successful build:

```json
{
  "event_type": "run-e2e",
  "client_payload": {
    "ref": "feat/my-branch",
    "run_id": "12345678",
    "sha": "abc123def456"
  }
}
```

### Manual (workflow_dispatch)

Can be triggered from GitHub UI or CLI:

```bash
gh workflow run e2e.yml \
  -R supervizio/runner-template \
  -f ref=main \
  -f run_id=12345678 \
  -f sha=abc123def456
```

## Required Secrets

| Secret | Purpose | Permissions |
|--------|---------|-------------|
| `AGENT_REPO_TOKEN` | Access agent repo for checkout, artifacts, and commit statuses | `Actions: Read`, `Contents: Read`, `Commit statuses: Write` on `supervizio/agent` |

Create a **fine-grained PAT** scoped to `supervizio/agent` with the above permissions, then add it as a repository secret in this repo.

## E2E Test Matrix

| Job | Runner | Artifacts |
|-----|--------|-----------|
| Docker amd64 (debian, alpine, scratch) | `ubuntu-24.04` | `supervizio-linux-amd64`, `supervizio-linux-amd64-musl` |
| Docker arm64 (debian, alpine, scratch) | `ubuntu-24.04-arm` | `supervizio-linux-arm64`, `supervizio-linux-arm64-musl` |
| macOS x86_64 | `macos-15-intel` | `supervizio-darwin-amd64` |
| macOS ARM64 | `macos-15` | `supervizio-darwin-arm64` |
| Linux exotic — 386, armv7, armv6, riscv64, ppc64le, s390x (glibc + musl) and loong64 | `ubuntu-24.04` under `qemu-user`/`binfmt_misc` | `supervizio-{386,arm7,arm6,riscv64,ppc64le,s390x}.{deb,apk}`, `supervizio-linux-loong64` |

The table above is not the whole matrix — the nine Linux init legs per arch, the
Windows legs and the BSD legs are in `e2e.yml` and not listed here.

The exotic Linux legs exist because GitHub sells no riscv64, ppc64le, s390x or
loongarch runner and the bench has no such guest: emulation is the only way to
execute those bytes at all. They install the real `.deb`/`.apk`, then run
`--version`, `--probe`, `validate-probe.sh` and `scenario-battery.sh` — and what a
green leg proves is narrower than that list:

- **Ten of the twelve run under qemu-user**, where every syscall is answered by the
  x86_64 host kernel and a supervised child shows up as `/usr/bin/qemu-<arch>`
  (`ptrace` is `ENOSYS`, `clone(CLONE_NEWPID)` is `EINVAL`). There, green means **the
  package installs, the binary starts and it probes** — not that supervision works
  on that architecture.
- **The two 386 legs run natively**, on the host kernel's 32-bit compat layer; for
  them the scenario battery is real supervision evidence, on a 64-bit kernel.
- **None boots an init**, so the postinstall graft is not proven by any of them.

Each leg checks its own `runtime` from a child's `/proc/<pid>/exe` and fails if it
disagrees with the matrix. The comment block above `e2e-linux-exotic` has the
measurements.

## Commit Statuses

Each E2E job posts individual commit statuses to the agent repo:

- `e2e/docker/{name}` — per-container Docker results
- `e2e/docker-arm64/{name}` — per-container ARM64 Docker results
- `e2e/macos-x86_64` — macOS Intel result
- `e2e/macos-arm64` — macOS Apple Silicon result
- `e2e/linux-exotic/{name}` — per-target emulated Linux results
- `e2e/runner-template` — aggregate final status

## Agent-Side Setup

Add this secret to `supervizio/agent`:

| Secret | Purpose | Permissions |
|--------|---------|-------------|
| `RUNNER_TEMPLATE_DISPATCH_TOKEN` | Dispatch events to this repo | `Contents: Write` on `supervizio/runner-template` |

The agent CI job `dispatch-e2e` uses this token to trigger the `run-e2e` event.
