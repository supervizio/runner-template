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
| `e2e.yml` | `repository_dispatch[run-e2e]`, `workflow_dispatch`, `workflow_call` | **agent's** E2E matrix — Docker, Linux guests, BSD, illumos, Solaris, Windows, macOS. Merge lane: installs the packages the agent run published and reports `e2e/*` commit statuses back to that SHA. Release mode (`workflow_call` from `validate-release.yml`, `mode: release`): the same jobs, named `leg/<id>`, on a release candidate's assets and test kit — see "e2e.yml in release mode" below. |
| `external-e2e.yml` | `repository_dispatch[run-external-e2e]`, `workflow_dispatch` | **libprobe's** lane. Rebuilds from source on the dispatched SHA; posts `e2e-public/<run>-<attempt>`, green iff the 6 native legs AND the 3 BSD **amd64** legs pass. BSD arm64 (no KVM, 1-2 h a leg) and the containers are advisory: shown in the table, never in the verdict. A BSD amd64 leg whose guest never became ready is retried once on a fresh runner; a leg that reached its tests never is. The BSD steps are written once (`&bsd-leg`) and aliased by all nine BSD jobs. |
| `agent-packages.yml` | `repository_dispatch[build-agent-packages]`, `workflow_dispatch` | **agent's packaging**: the one producer of its FreeBSD, NetBSD, OpenBSD (amd64, arm64), macOS (amd64, arm64) and Chocolatey packages, each built and installed on its own system from binaries agent cross-compiled on its self-hosted runner. agent's `public-packages.yml` dispatches it (ci.yml `package-openbsd`, release.yml `build-bsd-packages` / `build-desktop-packages`), finds the run by its run-name and downloads the packages. See "agent's packages" below. |
| `agent-solarish.yml` | `repository_dispatch[build-agent-solarish]`, `workflow_dispatch` | **agent's illumos and Solaris bytes**: the binary built natively with cgo in an OmniOS r151054 and a Solaris 11.4 guest, and its IPS archive, installed and run under SMF there. Builds agent's PRIVATE sources: see "Private sources built here" below. agent's `public-packages.yml` (producer `solarish`) dispatches it, downloads the bytes and deletes the run. |
| `libprobe-solarish.yml` | `repository_dispatch[run-libprobe-solarish]`, `workflow_dispatch` | **libprobe's illumos/Solaris suite** in the same two guests: platform, FFI and container tests, ABI check, metrics report. Builds libprobe's PRIVATE sources; only the verdict (the run's conclusion) leaves. libprobe's `solarish-guest.yml` dispatches it and deletes the run. |
| `cleanup-external-e2e.yml` | `workflow_run` on both of the above | Deletes each dispatched run once it finishes, so no public trace of a private-source run remains. `repository_dispatch` runs only — a `workflow_dispatch` is someone debugging on purpose. |
| `release-contract.yml` | PR and push on `release-contract/**` | Tests the release contract's validator on Linux, macOS, Windows and Python 3.9, and re-derives the manifest test vector with coreutils alone. See "The release contract" below. |
| `validate-release.yml` | `repository_dispatch[validate-release]`, `workflow_dispatch` | The **release** lane: validates a candidate's exact bytes, pulled by digest from the private repository's GHCR package. agent's legs are `e2e.yml` called in release mode. See "The release contract" below. |
| `validate-release-doorbell.yml` | `workflow_run` on `validate-release` | Posts a commit status on the validated private commit so the private side wakes and builds the receipt. Holds the lane's only secret. |
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

The Linux jobs run on `ubuntu-26.04` and `ubuntu-26.04-arm`, and so do the Linux
legs `policy.json` names. Two exceptions, each with its reason where it is set:
`post-commit.yml` stays on `ubuntu-latest` (the fleet stub), and `e2e.yml`'s
`386-glibc` leg on `ubuntu-24.04` until 26.04's Docker lets an i386 glibc
container open a socket (actions/runner-images#14790). actionlint does not know
the 26.04 labels yet; `.github/actionlint.yaml` lists them.

- **Real kernels, real PID 1**, under QEMU+KVM on the hosted runner:
  `vmactions/*-vm` for the Alpine (openrc, runit, s6), Debian-systemd and BSD
  legs; `./.github/actions/qemu-vm` for Rocky, openSUSE and Arch.
  Rocky is on qemu-vm because vmactions strips AVX-512 from `-cpu host` on the
  AMD hosts that have it (EPYC 9V74), and Rocky 10 then never boots: its
  fallback, `qemu64`, lacks the x86-64-v3 that Rocky 10 requires. qemu-vm passes
  `-cpu host` through untouched.
  The Debian-systemd guest (and its arm64 container twin) also installs
  Debian's `pacman-package-manager` before the package: install.sh must still
  take the `.deb`, and agent's `validate-detection.sh` must see apt as the one
  primary and pacman available (`pkg_available` in agent's
  `e2e/expected-matrix.json`, column `debian-vm-amd64` / `debian-container-arm64`).
- **Containers** for `debian-sysvinit` and `artix-dinit`, measured in
  `bench-leg-substrates-proof.yml`. `debian:trixie` ships no init at all, so
  sysvinit is INSTALLED into it rather than converted from systemd, and none of
  the blockers `init-swap-proof.yml` recorded for a cloud image applies (PID 1
  comm=init, runlevel N 2, cron reparented to PID 1, no `--privileged`). The
  official `artixlinux/artixlinux:base-dinit` image carries pacman AND dinit,
  so the package-manager and init dimensions are proven together, seam
  included. `void-xbps` (amd64 and arm64) is a container of Void's own
  `void-glibc-full` image, pinned by index digest, booted with `runit-init` as
  PID 1 -- Void's real stages 1 and 2, runsvdir on
  `/run/runit/runsvdir/current` -- and installs agent's `.xbps` through
  install.sh; no VM image exists for Void (no cloud image, no vmactions
  action). Honest delta: a container covers install, start and supervision,
  not boot ordering or clean shutdown.
- **Channels, not packages: `gentoo-portage` and `nixos-nix`** (amd64 and
  arm64, one matrix job each). agent ships to Gentoo and NixOS through a
  manifest -- an overlay's ebuild, a flake's package and NixOS module -- that
  names the static `supervizio-linux-{amd64,arm64}-musl` by hash. Each leg
  renders that channel with agent's `setup/packaging/render-channels.py`, from
  the agent tree (or the release's kit) and both binaries under test, which is
  what agent's `deploy-repo.yml` publishes for a validated release. The binary
  under test is put where the package manager would fetch it to (Portage's
  DISTDIR; the Nix store, under the flake's own name and hash, the leg
  asserting that path IS the package's source), the containers run with
  `--network none`, and each leg compares the installed file's sha256 with
  the binary under test. Gentoo: `gentoo/stage3` and `gentoo/portage` of one
  day, pinned by digest, `openrc-init` as PID 1, `emerge` from the overlay
  configured as its README says, `rc-update`/`rc-service` as the ebuild's elog
  says, `emerge --unmerge`. NixOS 26.05: `.github/nixos-leg/flake.nix`, built
  on the runner by Nix installed from its sha256-pinned installer (never
  cachix/install-nix-action, which writes the job's token into a
  world-readable nix.conf), booted from an empty image with the host's store
  read-only, unprivileged like every other container leg (the stock services
  that would need `--cap-add SYS_ADMIN` and AppArmor off -- nscd, dbus-broker,
  oomd, the wrappers, the special-filesystem remounts -- are switched off in
  that flake, each with its measured reason); installing is switching to the
  specialisation that enables `services.supervizio`, removing is switching
  back. Both run validate-probe, `validate-detection.sh
  {gentoo,nixos}-container-<arch>` and the scenario battery. Status contexts:
  `e2e/vm/{gentoo-portage,nixos-nix}` (amd64), `e2e/linux-arm64/...` (arm64).
- **BSD legs** run under QEMU through `vmactions/*-vm`, pinned to a release; arm64
  guests are emulated (TCG) and slow.
- **illumos and Solaris: `e2e-illumos-amd64`, `e2e-solaris-amd64`** (release
  legs `illumos/amd64`, `solaris/amd64`). A stock OmniOS r151054 and a stock
  Oracle Solaris 11.4 guest (`vmactions/omnios-vm`, `vmactions/solaris-vm`, no
  compiler), jq from each OS's own repository. The binary and the `.p5p` are
  agent's native build and IPS archive (`agent-solarish.yml` here, brought
  back into agent's run by its `public-packages.yml`; CI
  artifacts `supervizio-{illumos,solaris}-amd64[-pkg]`, release assets
  `supervizio-{illumos,solaris}-amd64[.p5p]`). `.github/solarish-leg/in-guest.sh`
  installs the raw binary through install.sh (which grafts the SMF manifest),
  then the archive through install.sh (pkg(5), whose actuator registers the
  same service): online under SMF after each, nothing left after each
  uninstall. validate-probe, `validate-detection.sh
  {omnios,solaris}-amd64`, an SMF cycle (disable, enable, SIGKILL then
  restarted) and the scenario battery run on the first. The merge lane checks
  out only the four paths the release kit carries (`e2e/`, `setup/`,
  `go.work`, `.dockerignore`), never agent's sources. Status contexts
  `e2e/illumos/omnios-amd64`, `e2e/solaris/amd64`.

  **When they run.** agent builds these two kernels (in `agent-solarish.yml`,
  here) on every release, but for a pull request only when
  it touches the paths agent lists in its `.github/solarish-paths.txt`. So in
  the merge lane `resolve` reads the agent run's artifact list: a kernel with
  neither its binary nor its `-pkg` there gets `illumos=false` /
  `solaris=false`, its leg is skipped by its `if:`, posts no status, and
  `report` records it as `not-built`, which passes (the aggregate description
  names it). Every other skip is still a failure, and a kernel with half its
  pair runs and fails on the missing half. No token to list the run with
  leaves the output empty: the legs run. Release mode never consults any of
  this -- both legs always run, and `validate-release.yml` judges them as
  required legs. `SolarishLegsInReleaseMode` in
  `release-contract/tests/test_release_contract.py` pins all three rules.

## agent's packages (`agent-packages.yml`)

agent's private repository no longer spends a hosted minute on packaging. Its
self-hosted runner cross-compiles every binary; `agent-packages.yml` runs only
the packaging tool that needs its own OS, and installs each package where it
built it before uploading it.

- **Request.** agent's `public-packages.yml` (on `supervizio-runner`)
  dispatches `build-agent-packages` with `request_id` (`<run id>-<attempt>-<label>`),
  `sha`, `run_id`, `version_num` and `only`. The run is named
  `agent-packages <request_id>` (`run-name:`); agent lists this workflow's
  `repository_dispatch` runs, takes the one with that title, waits for it to
  complete and downloads its artifacts. The verdict is the run's conclusion:
  nothing here writes to agent.
- **Artifacts** keep the names agent's release job reads:
  `supervizio-{freebsd,netbsd}-pkg`, `supervizio-openbsd-{amd64,arm64}-pkg`,
  `supervizio-macos-{amd64,arm64}-pkg`, `supervizio-windows-choco`. The
  `windows-arm64` job uploads nothing and is `continue-on-error`.
- **What it reads from agent**: the binaries of the requesting run, and a
  sparse checkout of `setup/`, `examples/config.yaml`, `e2e/test-install.ps1`
  and `.github/scripts/bsd-package-in-guest.sh` at `sha`. Everything but the
  guest wrapper already ships in each release's `e2e-kit.tar.gz`. No Go source
  is checked out. The scripts are read at the packaged commit rather than
  vendored here, so build-pkg.sh and the tree it packages cannot drift apart.
- **Guard-rails.** No `pull_request` or `pull_request_target` trigger. The only
  credential is `PRIVATE_SOURCE_TOKEN` (fine-grained, read-only: Contents and
  Actions on `supervizio/agent`), stored in the **`private-source`
  environment**, never at repository level; that environment's deployment
  branches are `main` only, so a branch run stops at its first private read.
  `admit` validates every payload field before any job holding the token
  starts. Only package directories are uploaded, and no step prints a file of
  the checkout.
- **Nothing stays.** agent's `public-packages.yml` deletes the run
  (`DELETE /actions/runs/<id>`) as soon as it has downloaded the packages,
  whatever the outcome, and fails if the run is still there: a public run of
  agent's packaging left behind is a defect. The three-day artifact retention
  is only a safety net for a deletion that never happened. The run is not in
  `cleanup-external-e2e.yml`, which deletes on completion, before agent could
  download anything.

## Private sources built here (`agent-solarish.yml`, `libprobe-solarish.yml`)

These two workflows compile the PRIVATE sources of agent and libprobe on this
public repository's runners. Their owner decided it: the private repositories'
hosted minutes are billed, their self-hosted pods have no KVM, and illumos and
Solaris need a real guest to build (agent) and to test (libprobe). It is the
one exception to "nothing private goes in it", and it is fenced:

- **Triggers**: `repository_dispatch` and `workflow_dispatch` only. Never
  `pull_request` or `pull_request_target`.
- **Credential**: `PRIVATE_SOURCE_TOKEN` (fine-grained, read-only: Contents
  and Actions on agent and libprobe), in the `private-source` environment,
  deployment branches `main` only; never at repository level. Only the
  checkout (and agent's libprobe fetch, silenced) reads it;
  `persist-credentials: false`; the guest never holds it. A credential-free
  `admit` validates the payload before any job holding it starts.
- **Nothing of the sources leaves**: the guest's whole output goes to a file
  under `/var/tmp` in the guest, outside the synced workspace, so copy-back
  never returns it; the log shows only the scripts' `=== <stage>` markers and
  the verdict. agent's build logs are removed from the workspace before
  copy-back; libprobe's report directory is reduced to its status file.
  Uploads: agent's binary and `.p5p`; for libprobe, nothing.
- **Nothing stays**: the private side deletes the run as soon as it has what it
  needs (cancelling it first if it is still running). Three-day artifact
  retention is only a net.
- `_PrivateSourceWorkflow`, `AgentSolarishGuardRails` and
  `LibprobeSolarishGuardRails` in `release-contract/tests/test_release_contract.py`
  pin every point above that a file can show.

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
  when its file or `release-contract/tests/live_proof.py` changes, or by
  `workflow_dispatch`. The policy and receipt it stages come from `live_proof.py`,
  which `release-contract.yml` exercises offline (`test_live_proof.py`): an inline
  copy in the workflow went stale against the contract unnoticed, and the proof
  was red on `main` from 2026-09-25 to this fix.
- **`validate-release.yml`** is the release lane (README D3 and section 4). The
  candidate is an OCI artifact in the private repository's own GHCR package
  (`policy.json` `bridge_package`), named by digest in the dispatch: nothing
  binary is ever stored here. `admit` checks the artifact against the manifest
  without downloading it; each `leg/<id>` pulls by digest with `packages: read`,
  re-hashes, then runs its scenario with no token in its env; `verdict` says what
  the legs imply. No secret is referenced. Its runs are the evidence a promotion
  reads, so `cleanup-external-e2e.yml` must not delete them. Every agent leg is
  `scenario: "e2e"`: the `e2e` job calls `e2e.yml` in release mode. Every libprobe leg runs the `abi`
  scenario: `scenario --stage prepare`, then the harness
  (`release-contract/harness/libprobe/run.sh`) on the runner, in a `vmactions`
  guest or in a container per `matrix.leg.host`, then `scenario --stage check`
  (README section 5). The guests are FreeBSD, OpenBSD, NetBSD, OmniOS r151054
  (`-build` image, for the illumos archive) and Oracle Solaris 11.4 (`-gcc`
  image); each registers the custom shell `guestvm`, so one step runs the
  harness in whichever booted. A guest host in `HARNESS_HOSTS` that no step
  boots fails `test_release_contract.py`.
- **`validate-release-doorbell.yml`** posts `release-validation/<tag>/g<N>` on the
  private commit when a `repository_dispatch` run on `main` completes, with the
  merge lanes' status tokens. It is the lane's only secret, kept out of the
  workflow that runs candidate bytes. The private side never believes it: it
  rebuilds the receipt from the run.
- To try the lane by hand: `workflow_dispatch` with the whole dispatch body and
  `policy: tests/proof-policy.json` (for agent, three integrity-only legs; for
  libprobe, the production legs with their `abi` scenario; both on the bridge
  probe package), or `tests/e2e-proof-policy.json` (every production agent leg,
  on a test candidate agent's `release.yml` pushed to the bridge probe package
  with `candidate_tag: v0.0.0-test.N`). Such a run can never become a receipt: `evidence` accepts only a
  `repository_dispatch` run on `main`. A workflow that is not on `main` yet can be
  dispatched only once registered: push it once on a branch it triggers on.
- Each `*-release-candidates` package must grant this repository Read, in the
  package's settings (Manage Actions access). That is a UI step, once per package.

When changing the contract: README, `release_contract.py` and the tests move
together; a new or changed receipt field is a new schema version; a new required
leg is a `policy.json` change, and a leg that only exists on an unmerged pull
request is `pending-merge`, never `required`.

## e2e.yml in release mode

`validate-release.yml`'s `e2e` job calls `e2e.yml` with `mode: release`, the
dispatch body, the policy, and **no `secrets:`** — every secret reads empty in
the called workflow, and nothing in release mode needs one:

- `resolve` outputs an empty `sha`, so every status step (gated on
  `sha != ''`) is skipped; `report` does not run. Nor does its artifact
  pre-check, so `illumos`/`solaris` are empty and the illumos and Solaris legs
  run whatever the merge lane would have skipped (their `if:` also says
  `inputs.mode == 'release' ||` first).
- Each leg skips `Checkout agent code` and its `actions/download-artifact`
  step(s), and instead checks this repository out to `.release-lane` and runs
  `.github/actions/release-candidate`: `bridge pull` of the leg's assets, the
  manifest file and `e2e-kit.tar.gz` (by digest; a published asset of the
  release, or a support file for older candidates), `manifest verify-files` on
  the assets (and on the kit when it is an asset), the kit extracted where the agent checkout would have been (`.`
  or `agent/`), each asset copied to the directory the download used (`bin/`,
  `pkg/`, `dl/`). Every step after that is the merge lane's.
- The asset is the RELEASE's, under its release name. The normalise steps
  already resolve by extension, so the same code handles both; `e2e-linux-exotic`
  carries a `release_asset` per entry because agent renames arm7 → `arm`, arm6
  → `armhf`. `arm64-packages` is skipped: the release carries its own arm64
  packages, and `e2e-linux-arm64` installs those.
- Job names are `leg/<policy leg id>` (the merge-lane name otherwise), which
  GitHub reports as `e2e / leg/<id>`: that is what `release_contract.py`
  reads. A leg id here and in `policy.json` must match, or the leg reads
  `missing` and the candidate cannot pass.
- `permissions` gained `packages: read` for the pull. It cannot depend on the
  mode; in the merge lane it is unused.

To prove the merge lane is unchanged after touching this: `workflow_dispatch`
`e2e.yml` on the branch with an agent CI run whose artifacts have not expired
(they live one day), no `sha`, then delete the run.

## Two things that have cost real time here

**`uses:` takes no expression.** `${{ matrix.os }}` in a `uses:` is rejected,
so a matrix over two different actions needs two steps. Put the shared script
in a file rather than duplicating it inline — it is also the only way
shellcheck can read it. `supervizio/agent`'s `.github/scripts/bsd-package-in-guest.sh`
is the worked example; this repo has no such script yet.

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
