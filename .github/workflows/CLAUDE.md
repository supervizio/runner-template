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
| `external-e2e.yml` | `repository_dispatch[run-external-e2e]`, `workflow_dispatch` | **libprobe's** lane. Rebuilds from source on the dispatched SHA; posts `e2e-public/<run>-<attempt>`, green iff the 6 native legs AND the 3 BSD **amd64** legs pass. BSD arm64 (no KVM, 1-2 h a leg) and the containers are advisory: shown in the table, never in the verdict. A BSD amd64 leg whose guest never became ready is retried once on a fresh runner; a leg that reached its tests never is. The BSD steps are written once (`&bsd-leg`) and aliased by all nine BSD jobs. |
| `cleanup-external-e2e.yml` | `workflow_run` on both of the above | Deletes each dispatched run once it finishes, so no public trace of a private-source run remains. `repository_dispatch` runs only — a `workflow_dispatch` is someone debugging on purpose. |
| `qemu-vm-selftest.yml` | push on its own paths | Exercises `.github/actions/qemu-vm` against the upstream cloud images the Linux legs use, before those legs depend on it. |
| `dinit-container-proof.yml` | push on its own paths | Proves dinit coverage needs no VM: a Chimera rootfs makes a container where dinit is really PID 1, a service in `/etc/dinit.d` starts, and apk-tools 3 still installs nfpm's v2 `.apk`. Kept so the result is not re-derived. |
| `init-swap-proof.yml` | push on its own path | A recorded experiment: why a systemd-built Debian CLOUD IMAGE cannot be converted to SysVinit. Its conclusion stands and is still worth keeping — but it does **not** mean `debian-sysvinit` needs a VM. See `bench-leg-substrates-proof.yml`. |
| `bench-leg-substrates-proof.yml` | push on its own paths | Proves neither remaining bench leg needs a VM: pacman and dinit together in the official Artix dinit image, and real SysVinit as PID 1 in a container. Kept so the result is not re-derived. |
| `docker-images.yml`, `release.yml`, `post-commit.yml` | various | Inherited from the template. `post-commit.yml` is the merge gate and stays on `ubuntu-latest` **on purpose** — this repo is public, and pointing its pull requests at the fleet's self-hosted runner would let a fork run code there. |

## Where the work runs, and why it matters

Almost everything is on GitHub-hosted runners. Two jobs are not:

- `e2e-vm` (2 legs: `artix-dinit`, `debian-sysvinit`) and `vm-cleanup` run on
  `supervizio-runner`, the ARC pod, and acquire Proxmox guests 208 and 205.

  **Neither leg still needs a VM.** Both were measured green on hosted runners in
  `bench-leg-substrates-proof.yml`; what remains is wiring, not research.

  `debian-sysvinit` was called irreplaceable in this file, and that was wrong.
  The reasoning was sound about `init-swap-proof.yml` — four runs failed to
  convert a systemd-built Debian CLOUD IMAGE, and its conclusion that the bench
  guest was INSTALLED with sysvinit rather than converted is exactly right. What
  nobody noticed is that a Docker base image is *also* a system sysvinit gets
  INSTALLED into. `debian:trixie` ships no init at all — no systemd-sysv, no
  /sbin/init, no /etc/inittab — so there is nothing to remove and none of the
  four blockers applies. Measured: PID 1 comm=init, runlevel N 2, inittab 2348
  bytes, cron reparented to PID 1, no --privileged.

  Devuan still publishes no disk image (`virtual/`, `qemu/`, `cloud/` all 404,
  checked 2026-09-19) — that part of the old note is accurate. It simply stopped
  being the question.

  `artix-dinit` is replaced by the official Artix Docker image
  `artixlinux/artixlinux:base-dinit`, which carries pacman AND dinit — so the
  leg's two dimensions stay together. The earlier Chimera finding
  (`dinit-container-proof.yml`) remains true and is kept, but it is no longer
  the better answer: splitting across Chimera (dinit, apk) and Arch (pacman,
  systemd) would prove "pacman installs" and "dinit starts" without ever proving
  the seam between them, which is where packaging regressions live. Measured: a
  .pkg.tar.zst installs, `pacman -Qo` reports it owns the service file, and
  dinit as PID 1 takes it to STARTED.

  Honest delta for both: containers cover install, start and supervision. They
  do not cover boot ordering or clean shutdown — `dinit --container` disables
  system management by design, and a sysvinit container never reaches runlevel
  0. Whether that delta is worth two Proxmox guests is a judgement.

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
