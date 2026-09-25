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
