# GitHub Actions Workflows

## Purpose

**This repository is supervizio's public E2E runner, and the home of its release
contract.** `supervizio/agent` and `supervizio/libprobe` are private and pay for
every hosted minute; this repository is public and does not. The workflows below
run their end-to-end matrices on free GitHub runners and report a verdict back.

The devcontainer-template plumbing it was created from is still here
(`docker-images.yml`, `release.yml`, `.devcontainer/`, the root `AGENTS.md`). None
of it is what anyone works on.

## What each workflow is for

| File | Trigger | What it does |
|------|---------|--------------|
| `e2e.yml` | `repository_dispatch[run-e2e]`, `workflow_dispatch` | **agent's** E2E matrix — Docker, Linux guests, BSD, Windows, macOS. Installs the packages the agent run published and reports `e2e/*` commit statuses back to that SHA. |
| `external-e2e.yml` | `repository_dispatch[run-external-e2e]`, `workflow_dispatch` | **libprobe's** lane. Rebuilds from source on the dispatched SHA; posts `e2e-public/<run>-<attempt>`, green iff the 6 native legs AND the 3 BSD **amd64** legs pass. BSD arm64 (no KVM, 1-2 h a leg) and the containers are advisory: shown in the table, never in the verdict. A BSD amd64 leg whose guest never became ready is retried once on a fresh runner; a leg that reached its tests never is. The BSD steps are written once (`&bsd-leg`) and aliased by all nine BSD jobs. |
| `cleanup-external-e2e.yml` | `workflow_run` on both of the above | Deletes each dispatched run once it finishes, so no public trace of a private-source run remains. `repository_dispatch` runs only — a `workflow_dispatch` is someone debugging on purpose. |
| `release-contract.yml` | PR and push on `release-contract/**` | Tests the release contract's validator on Linux, macOS, Windows and Python 3.9, and re-derives the manifest test vector with coreutils alone. See "The release contract" below. |
| `release-contract-proof.yml` | push to `main` on its own path, `workflow_dispatch` | Measures, on real GitHub objects, the behaviours the release contract relies on, and fails if one of them changes. Never runs on a branch push: its jobs hold `contents: write`. |
| `qemu-vm-selftest.yml` | push on its own paths | Exercises `.github/actions/qemu-vm` against the upstream cloud images the Linux legs use, before those legs depend on it. |
| `openbsd-abi-proof.yml` | push on its own path | Runs the OpenBSD link shape across releases and link modes, to answer which OpenBSD binary runs where by executing it. |
| `dinit-container-proof.yml` | push on its own paths | Proves dinit coverage needs no VM: a Chimera rootfs makes a container where dinit is really PID 1, a service in `/etc/dinit.d` starts, and apk-tools 3 still installs nfpm's v2 `.apk`. |
| `init-swap-proof.yml` | push on its own path | Why a systemd-built Debian CLOUD IMAGE cannot be converted to SysVinit. It does **not** mean `debian-sysvinit` needs a VM: see `bench-leg-substrates-proof.yml`. |
| `bench-leg-substrates-proof.yml` | push on its own paths | Proves the artix-dinit and debian-sysvinit legs need no VM: pacman and dinit together in the official Artix dinit image, and real SysVinit as PID 1 in a container. |
| `docker-images.yml`, `release.yml`, `post-commit.yml` | various | Inherited from the template. `post-commit.yml` is the required merge gate and stays on `ubuntu-latest` — see below. |

## Where the work runs

**Every job here runs on a GitHub-hosted runner.** None reaches the labs bench
(Proxmox guests 200-215) or the CI host's self-hosted `supervizio-runner`; check
it with `grep -n 'runs-on' .github/workflows/*.yml`. This repository is public,
so pointing a job at a self-hosted runner would let a fork's pull request run
code there.

- **Real kernels, real PID 1**, under QEMU+KVM on the hosted runner:
  `vmactions/*-vm` for the Alpine (openrc, runit, s6), Debian-systemd and BSD
  legs; `./.github/actions/qemu-vm` for Rocky, openSUSE and Arch.
  Rocky is on qemu-vm because vmactions strips AVX-512 from `-cpu host` on the
  AMD hosts that have it (EPYC 9V74), and Rocky 10 then never boots: its
  fallback, `qemu64`, lacks the x86-64-v3 that Rocky 10 requires. qemu-vm passes
  `-cpu host` through untouched.
- **Containers** for `debian-sysvinit` and `artix-dinit`, measured in
  `bench-leg-substrates-proof.yml`. `debian:trixie` ships no init at all, so
  sysvinit is INSTALLED into it rather than converted from systemd, and none of
  the blockers `init-swap-proof.yml` recorded for a cloud image applies (PID 1
  comm=init, runlevel N 2, cron reparented to PID 1, no `--privileged`). The
  official `artixlinux/artixlinux:base-dinit` image carries pacman AND dinit,
  so the package-manager and init dimensions are proven together, seam
  included. Honest delta: a container covers install, start and supervision,
  not boot ordering or clean shutdown.

## Upstream images: pinned hash or signature

A VM leg boots an upstream cloud image and gives it a root shell, so the image
is always verified. Alpine, Debian, Fedora and Arch publish each build under its
own name and keep it: those are pinned by sha256/sha512. openSUSE rebuilds in
place and keeps only the newest build, and Rocky moves each build out of `pub/`
at the next point release, so any pin goes stale (openSUSE's did on 2026-09-24:
`e2e/vm/opensuse-zypper` went red on every agent PR, the agent not involved).
Those two legs resolve the current build with
`.github/actions/qemu-vm/resolve-image.sh`, and qemu-vm takes its sha256 from
the checksum file the distribution signs, after `gpgv` proves the signer is the
key in `.github/keys/` whose fingerprint the workflow pins. See
`.github/keys/CLAUDE.md`.

## The release contract

`release-contract/` is the single source of truth for what a release of agent or
libprobe must prove before it leaves draft: the canonical asset manifest and its
digest, the receipt a release carries (`release-receipt.json`), the
`validate-release` dispatch payload, the required matrix (`policy.json`), and the
checks run right before `--draft=false`. `release-contract/README.md` is the
normative text; `release_contract.py` (stdlib Python) is its only implementation.
agent's and libprobe's release workflows pin that directory by commit SHA and call
the script; they do not re-implement a rule.

- **`release-contract.yml`** proves the validator refuses what it must — an altered
  manifest, a re-pointed tag, a missing, cancelled or timed-out leg, a receipt whose
  verdict does not follow from its results — on every OS family that will run it,
  and that the manifest format is reproducible without it.
- **`release-contract-proof.yml`** proves, on a live draft it creates and deletes,
  what the contract's design stands on, and fails if it stops being true: a draft
  release is readable only with push access (the `contents: read`, no-permission
  and anonymous probes assert a denial; the same probe with push access must see
  the draft, or the denials prove nothing); GitHub's asset `digest` is the sha256
  of the uploaded bytes; the validator passes a consistent draft and refuses it
  after an asset is replaced or the tag is re-pointed; a check run holds 65535
  characters of text; a 268-character run-name is kept whole. It runs on `main`
  when its file changes, or by `workflow_dispatch`.
- **`validate-release.yml` does not exist yet.** The contract fixes what it must be
  (README section 4): no secret referenced anywhere; an `admit` job with
  `contents: write` and nothing else, never executing candidate bytes; one
  `leg/<id>` job per required leg, with `permissions: {}`; a `run-name` binding the
  run to one candidate. Its runs are the evidence a promotion reads, so
  `cleanup-external-e2e.yml` must not delete them.

When changing the contract: README, `release_contract.py` and the tests move
together; a new or changed receipt field is a new schema version; a new required
leg is a `policy.json` change, and a leg that only exists on an unmerged pull
request is `pending-merge`, never `required`.

## Two things that have cost real time here

**`uses:` takes no expression.** `${{ matrix.os }}` in a `uses:` is rejected,
so a matrix over two different actions needs two steps. Put the shared script
in a file rather than duplicating it inline — it is also the only way
shellcheck can read it. `supervizio/agent`'s `.github/scripts/bsd-package-in-guest.sh`
is the worked example; this repo has no such script yet, only the VM helpers.

**ssh forwards no environment.** A `run:` block passed to `vmactions/*-vm` or
`./.github/actions/qemu-vm` executes in the GUEST. Anything it reads must be
named in `envs:`, or it is empty there.

## Conventions

- Pin every action by SHA, with the version in a trailing comment.
- Run `actionlint` on anything edited here. `yq` proves the YAML parses; it does
  not prove GitHub will run it — an empty `${{ }}`, even inside a comment,
  starts a run with zero jobs and `yq` is perfectly happy with it.
- Know which shell a step runs: it decides what an expected failure does. With no
  `shell:`, Linux and macOS run `bash -e {0}` and Windows runs `pwsh`; `shell: bash`
  runs `bash --noprofile --norc -eo pipefail {0}` on every OS
  ([workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).
  In bash, a step that expects a command to fail must `set +e` or capture it
  (`cmd || rc=$?`), or the first expected failure ends the step. In `pwsh`,
  `$ErrorActionPreference = 'stop'` is prepended and the step exits with the last
  `$LASTEXITCODE`: check `$LASTEXITCODE` right after the command, and end with
  `exit 0` once the failure is the expected one. `release-contract.yml` sets
  `shell: bash` on its Windows job, so one syntax covers all three OS families.
- A `GITHUB_TOKEN` cannot move a ref across commits whose workflow files differ —
  it never holds the `workflows` permission.
- This repository is public. Nothing private goes in it: no private branch names,
  no internal lab addresses or paths, no secrets.
