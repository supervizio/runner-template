# GitHub Actions Workflows

## Purpose

**This repository is supervizio's public E2E runner.** Its reason to exist is
that `supervizio/agent` and `supervizio/libprobe` are private and pay for every
hosted minute, while this repo is public and does not. The workflows below run
their end-to-end matrices on free GitHub runners and report a verdict back.

The devcontainer-template plumbing it was forked from is still here
(`docker-images.yml`, `release.yml`, and the root `CLAUDE.md`/`AGENTS.md`).
That inheritance is not what anyone works on; this file used to describe only
that half, which is how the workflows that matter went undocumented.

## What each workflow is for

| File | Trigger | What it does |
|------|---------|--------------|
| `e2e.yml` | `repository_dispatch[run-e2e]`, `workflow_dispatch` | **agent's** E2E matrix — Docker, Linux guests, BSD, Windows, macOS. Installs the packages the agent run published and reports `e2e/*` commit statuses back to that SHA. |
| `external-e2e.yml` | `repository_dispatch[run-external-e2e]` | **libprobe's** lane. Rebuilds from source on the dispatched SHA; posts `e2e-public/<run>-<attempt>`. |
| `cleanup-external-e2e.yml` | `workflow_run` on both of the above | Deletes each dispatched run once it finishes, so no public trace of a private-source run remains. `repository_dispatch` runs only — a `workflow_dispatch` is someone debugging on purpose. |
| `qemu-vm-selftest.yml` | push on its own paths | Exercises `.github/actions/qemu-vm` against the upstream cloud images the Linux legs use, before those legs depend on it. |
| `init-swap-proof.yml` | push on its own path | A recorded experiment: why `debian-sysvinit` cannot move to a hosted guest. Kept so the conclusion is not re-derived. |
| `docker-images.yml`, `release.yml`, `post-commit.yml` | various | Inherited from the template. `post-commit.yml` is the merge gate and stays on `ubuntu-latest` **on purpose** — this repo is public, and pointing its pull requests at the fleet's self-hosted runner would let a fork run code there. |

## Where the work runs, and why it matters

Almost everything is on GitHub-hosted runners. Two jobs are not:

- `e2e-vm` (2 legs: `artix-dinit`, `debian-sysvinit`) and `vm-cleanup` run on
  `supervizio-runner`, the ARC pod, and acquire Proxmox guests 208 and 205.
  They stay because no cloud image exists for either: Artix publishes none,
  Chimera ships only live ISOs, Devuan only ISOs (checked 2026-09-19), and
  converting a Debian cloud image to SysVinit failed four documented times —
  see `init-swap-proof.yml`.

Everything else — the seven Linux legs, five BSD legs, both Windows, both
macOS, six Docker legs — is hosted and free.

## Two things that have cost real time here

**`uses:` takes no expression.** `${{ matrix.os }}` in a `uses:` is rejected,
so a matrix over two different actions needs two steps. Put the shared script
in a file rather than duplicating it inline — it is also the only way
shellcheck can read it. `supervizio/agent`'s `.github/scripts/bsd-package-in-guest.sh`
is the worked example; this repo has no such script yet, only the VM helpers.

**ssh forwards no environment.** A `run:` block passed to `vmactions/*-vm` or
`./.github/actions/qemu-vm` executes in the GUEST. Anything it reads must be
named in `envs:`. This has caused three separate outages in this repo: eight
qemu-vm self-test legs at once, then `OPENBSD_PKG`, then a `$RUNNER_TEMP` in a
diagnostic that took down the leg it was diagnosing.

## Conventions

- Pin every action by SHA, with the version in a trailing comment.
- Run `actionlint` on anything edited here. `yq` proves the YAML parses; it does
  not prove GitHub will run it — an empty `${{ }}`, even inside a comment,
  starts a run with zero jobs and `yq` is perfectly happy with it.
