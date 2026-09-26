# Release contract — v1

What a release of `supervizio/agent` or `supervizio/libprobe` must prove before it
leaves draft, in a form a machine checks. This directory is the single source of
truth for it; the two private repositories consume it pinned by commit SHA, and
this repository's release-validation lane (`validate-release.yml`, with
`validate-release-doorbell.yml`) implements the public half.

| File | Role |
|---|---|
| `README.md` | the normative text (this file) |
| `release_contract.py` | its only implementation — stdlib Python ≥ 3.9, no dependency; every workflow calls it instead of re-deriving a rule in shell |
| `policy.json` | the required matrix per repository, and the per-repository names below |
| `tests/` | the validator's tests, the manifest test vector any other implementation must reproduce, and `proof-policy.json` (section 9) |

The unit of trust is **a set of bytes, not a commit**. The same commit built twice
can yield different bytes (injected version, dependency drift, floating toolchain),
so everything below is bound to the digest of the published assets, and the commit
is recorded only as provenance.

```
private repository (agent | libprobe)                  runner-template (public)
─────────────────────────────────────                  ────────────────────────
tag push → build, package, sign
  draft release + manifest file + release-receipt.json {verdict: pending}
  bridge push → ghcr.io/supervizio/<repo>-release-candidates@sha256:…  (PRIVATE package)
  repository_dispatch validate-release {manifest, bridge.digest} ─►  validate-release.yml  (no secret)
                                                                     admit: artifact == manifest (no download)
                                                                     leg/<id>: pull by digest, re-hash, scenario
                                                                     verdict: what the legs imply
                          commit status release-validation/<tag>/gN ◄─ validate-release-doorbell.yml
promotion job (on: status)
  evidence = the run's jobs, read from the public API
  release-receipt.json {verdict: success | failure | error}  (+ copy → Garage)
  verify-promotion → gh release edit --draft=false → deploy
```

Nothing binary is ever stored in runner-template: the candidate lives in the
private repository's own package, the receipt on the private release.

## 1. Decisions, and what they rest on

Every claim here was measured (2026-09-23/24) or cites the documentation it comes
from; section 9 lists the measurements.

**D1 — The receipt is a release asset, `release-receipt.json`.** Not a commit
status, not a check run. From 2026-10-01, check runs *and* commit statuses expire
with the repository's Actions retention setting instead of after 400+ days
([changelog 2026-08-27](https://github.blog/changelog/2026-08-27-actions-retention-will-cover-checks-workflow-runs-and-statuses/),
[retention docs](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization)),
and this organisation caps that setting at **7 days** (measured). A receipt stored
there would vanish a week after its release, and reconcil-release would read every
release as legacy — safe, it rebuilds nothing, but it loses exactly the proof it
exists to keep. Neither primitive would hold the receipt anyway without abuse: a
status description stops at 140 characters, and a check run can only be written by
a GitHub App, so this public repository could not write one on a private repository
without an App installed there. The release is the one GitHub object whose lifetime is the release's:
its receipt sits next to its assets in the UI, is read through the releases API
reconcil-release already paginates, and is deleted with the release — which is the
"tag present, release absent" case, restored from Garage, where every receipt is
also written.

**D2 — The manifest file a release already publishes *is* the canonical
manifest.** agent publishes `checksums.txt`, libprobe `SHA256SUMS`. Their bytes
must be the canonical serialisation of section 2, so `asset_manifest_digest` is the
sha256 of that file — and GitHub computes and exposes a sha256 `digest` for every
release asset at upload
([changelog 2025-06-03](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/)).
The pre-promotion check therefore needs no download: every asset's GitHub digest is
compared with its manifest entry, and the manifest file's digest with
`asset_manifest_digest`. Anyone can re-check a published release with `sha256sum -c`
and one more `sha256sum`.

**D3 — The bridge to the public runners is a private GHCR package per
repository.** This departs from brief §4.6, which exposed Garage through a public
vhost and handed presigned URLs to the hosted runners. Garage is reachable from the
private side only, so something else has to carry the candidate bytes, and **the
owner's rule is that no binary is stored in this public repository**:

| Candidate bridge | Why not |
|---|---|
| The private repository's own draft, read with a read-only token | Measured: a draft is invisible to anything without push access — `contents:read` gets 403, no token 404. The REST docs agree ("Only users with push access will receive listings for draft releases"). A token that can read the private draft can write the private repository's releases, and it would be stored here, in a public repository. |
| Cross-repository Actions artifacts (the `AGENT_REPO_TOKEN` pattern of `e2e.yml`) | The public side must hold a credential on the private repository, and GitHub only scrubs from runner memory the secrets "not referenced in the workflow" ([compromised runners](https://docs.github.com/en/actions/concepts/security/compromised-runners)) — per workflow, not per job — so the legs running candidate code would share memory space with it. |
| Signed download URLs of the private draft's assets, in the payload | Measured: the redirect URL carries a JWT valid 300 seconds — shorter than a queue. |
| A staging draft release of runner-template (this contract's first design) | Binaries in the public repository, and the same-run artifact that carried them to the legs was downloadable by any signed-in GitHub user while it existed. Abandoned by the owner. |
| Public Garage with presigned URLs (brief §4.6) | Garage is private. |

So the private release job pushes the candidate as an **OCI artifact** to its
repository's own private package, `policy.json` `bridge_package`, with its own
`GITHUB_TOKEN` (`packages: write`), and dispatches its **digest**. The artifact
(`release_contract.py bridge push`):

- one layer per file — every manifest entry, every support file, and the manifest
  file itself — with `mediaType: application/octet-stream`, the file's raw bytes
  as the blob, and its name in `org.opencontainers.image.title`. A layer's digest
  is therefore the file's sha256, and the artifact is checked against the manifest
  **without downloading a byte**;
- `artifactType: application/vnd.supervizio.release-candidate.v1`, the empty OCI
  config, and the annotation `org.supervizio.release.candidate` = the candidate's
  run-name (section 4), so the same bytes pushed for another tag, commit or
  generation are refused;
- a tag `<tag>-g<generation>` for humans. Nothing reads a tag: the dispatch pins
  the manifest digest, and a registry serves a digest's bytes or nothing.

Read access is **granted per package, in the GitHub UI** (package settings →
Manage Actions access → add `supervizio/runner-template`, role Read); it cannot be
automated. The number of packages is therefore fixed — one per repository, every
candidate a new version of it:

| Package | Published by | Grant runner-template Read |
|---|---|---|
| `ghcr.io/supervizio/agent-release-candidates` | `supervizio/agent` (`packages: write`) | once, before the first release |
| `ghcr.io/supervizio/libprobe-release-candidates` | `supervizio/libprobe` (`packages: write`) | once, before the first release |
| `ghcr.io/supervizio/release-contract-bridge-probe` | `supervizio/agent`, measurement and proof only | already granted; `tests/proof-policy.json` only |

A package pushed by a repository's `GITHUB_TOKEN` is created linked to that
repository, which keeps write access; neither repository can write the other's.

`validate-release.yml` references **no secret**: its only credentials are the
per-job `GITHUB_TOKEN`s GitHub mints with each job's own permissions.

- `admit` — `contents: read`, `actions: read`, `packages: read`. Runs `dispatch
  check` (policy of *this* revision), checks its own run-name, fetches the OCI
  manifest by digest and admits it against the manifest (`bridge admit`): right
  artifact type and annotation, one raw layer per expected file, each layer
  digest equal to its manifest sha256, nothing missing, nothing extra. Never
  downloads a blob. Emits the leg matrix.
- `leg/<id>` — `contents: read`, `packages: read`, nothing else. `bridge pull`
  re-admits the artifact (it does not trust `admit`), downloads each blob **by
  digest**, hashes it on the way to disk and gives it its name only once proven;
  then `manifest verify-files` re-hashes everything against the manifest file
  pinned by `asset_manifest_digest`; only then does the scenario run, with no
  token in its environment.
- `e2e` — the legs whose scenario is `e2e` (every agent leg): `e2e.yml` called
  as a reusable workflow with `mode: release`, the dispatch body, and **no
  `secrets:`**, under the same two permissions. Each of its jobs is a leg,
  reported as `e2e / leg/<id>`; instead of checking out the private tree and
  downloading CI artifacts it runs `.github/actions/release-candidate`, which
  pulls only the assets that leg installs plus the support file
  `e2e-kit.tar.gz` (agent's `e2e/`, `setup/`, `go.work`, `.dockerignore` at the
  tagged commit), by digest, re-hashes the assets against the manifest file,
  and lays them out where the merge lane would have. The scenario that follows
  is the merge lane's, byte for byte, on the release's own assets.
- `verdict` — `contents: read`, `actions: read`. What the leg jobs imply
  (`judge`); red unless `success`. It is a signal for humans, never a receipt.

The bridge is untrusted by construction: integrity is end to end, from the digest
the private side computed to the hash each leg recomputes. **Residual exposure:**
a leg holds a token that can read the packages granted to runner-template — the
candidates themselves — while it executes candidate bytes on a hosted runner.

Garage is the durable store of *validated* bytes: written only from the private
side, read by reconcil-release to restore a release (section 7). The candidate
package is transit: the private side may delete a version once its release is
published or abandoned.

**D4 — The verdict comes from the public run, never from a callback.** The
promotion job reads the finished `validate-release.yml` run through the public REST
API — the run, and its jobs with `filter=latest`, paginated — and builds the
receipt itself (`evidence`). What wakes it is a doorbell:
`validate-release-doorbell.yml`, on `workflow_run` completion of a
`repository_dispatch` run on `main`, posts a commit status
`release-validation/<tag>/g<N>` on the validated private commit, `target_url` = the
run, with the status token the merge lanes already hold (`AGENT_REPO_TOKEN`,
`LIBPROBE_REPO_TOKEN`: commit statuses write on their repository). The private side
listens with `on: status`. A forged or stale doorbell can wake it; nothing it says
is believed, so it cannot promote anything. It lives in its own workflow so that no
workflow that runs candidate bytes references a secret. Consequence:
`validate-release.yml` runs must not be deleted by `cleanup-external-e2e.yml`; they
carry no private source, and the 7-day retention removes them.

## 2. The manifest

A manifest is a set of `{filename: sha256}` entries.

- **filename**: ASCII, `^[A-Za-z0-9][A-Za-z0-9._+-]{0,254}$` — no `/`, no
  whitespace, no leading `.` or `-`. Unique, and unique **case-insensitively**:
  two names differing only by case are one file on the macOS and Windows legs.
- **sha256**: 64 lowercase hex characters.
- **entries**: every release asset except the two reserved names — the manifest
  file itself (`checksums.txt` for agent, `SHA256SUMS` for libprobe, see
  `policy.json`) and `release-receipt.json`. At least one entry.

**Canonical serialisation:** one line per entry, `<sha256><SP><SP><filename><LF>`,
sorted by filename in ascending **byte** order; every line LF-terminated, the last
included; no header, no blank line, no CR, no BOM. It is exactly GNU `sha256sum`
text-mode output sorted under `LC_ALL=C`:

```sh
find . -maxdepth 1 -type f ! -name checksums.txt ! -name release-receipt.json -printf '%f\n' \
  | LC_ALL=C sort | while IFS= read -r f; do sha256sum -- "$f"; done > checksums.txt
```

`LC_ALL=C` is not optional. Under `en_US.UTF-8`, `supervizio-arm64.apk` sorts
before `supervizio-arm.apk` and `Z…` after `a…`: same files, different digest.
The validator refuses any manifest file that is not byte-for-byte canonical, even
one `sha256sum -c` would accept.

**`asset_manifest_digest`** = `"sha256:"` + lowercase hex SHA-256 of the canonical
serialisation = the sha256 of the manifest file = its GitHub asset `digest`.

**Test vector** — `tests/vectors/manifest-v1/`: five files whose names exercise
both locale traps. `SHA256SUMS` is their canonical manifest,
`sha256:e0d809e3e6092223b4f62de7a5b44e1b91caa5902391a3004d81780468f4865f` its
digest. CI re-derives both with coreutils alone.

## 3. The receipt

`release-receipt.json` — one JSON object, every key always present (unknown keys
are refused: a new field means a new schema).

| Field | Type | Rule |
|---|---|---|
| `schema` | string | `"supervizio.release-receipt/v1"` |
| `repository` | string | a key of `policy.json` `repositories` |
| `tag` | string | `v<major>.<minor>.<patch>[-<prerelease>]` |
| `resolved_commit` | string | 40 lowercase hex — the commit the tag resolved to, annotated tags peeled |
| `release_id` | integer ≥ 1 | the GitHub release the receipt was written for |
| `candidate_generation` | integer ≥ 1 | increments each time new bytes are attached to a release for this tag |
| `manifest_file` | string | the repository's manifest file name (`policy.json`) |
| `asset_manifest_digest` | string | `sha256:<64 hex>`; must equal the digest of `manifest` |
| `manifest` | object | `{filename: sha256}` of every published asset (section 2) |
| `support` | object | `{filename: sha256}` of candidate-only test inputs (e.g. a test kit built from the private tree), carried by the bridge; may be `{}`; never published, never overlapping `manifest` |
| `support_manifest_digest` | string \| null | digest of `support`, `null` iff `support` is empty |
| `required_matrix` | array of leg ids | non-empty, unique, a superset of the policy's `required` legs for the repository |
| `test_suite_revision` | string \| null | the runner-template commit whose `validate-release.yml` ran (the run's `head_sha`) — observed, not declared |
| `e2e_run_id`, `e2e_attempt` | integer \| null | the run and attempt read as evidence |
| `results` | object | `{leg id: result}`; must cover every required leg |
| `verdict` | string | `pending` \| `success` \| `failure` \| `error` |
| `recorded_at` | string | UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| `restored_from` | object \| null | `{release_id, candidate_generation}` of the receipt a restoration carried over (success only) |

A leg result is a job conclusion (`success`, `failure`, `cancelled`, `timed_out`,
`skipped`, `neutral`, `action_required`, `stale`) or one of `missing` (no job
reported the leg) and `incomplete` (not completed, or reported twice).

**The verdict is derived, never asserted:** `success` iff every required leg is
`success`; `failure` iff a required leg is `failure` (the candidate is bad);
`error` otherwise — cancelled, timed out, skipped, missing, incomplete. `error`
means "no evidence" and is never promotable; unlike `failure` it can be re-validated
without a rebuild. A receipt whose stored verdict differs from the derived one is
invalid.

**Lifecycle.** The private side attaches a `pending` receipt when it dispatches
(no run, no results) — it doubles as the release's "current candidate" marker. The
promotion job replaces it with the final receipt built from the run (`evidence`),
writes a copy to Garage first, then uploads it to the release — **before**
`--draft=false`, so a crash between upload and publication never forces a new
validation.

## 4. The `validate-release` dispatch

`POST /repos/supervizio/runner-template/dispatches`. GitHub accepts at most 10
top-level `client_payload` properties and a payload under 64 KB
([REST reference](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event));
this one has 6, and a 62-asset agent release with all 53 legs stays under 16 KiB
(tested). The validator enforces both limits on the whole body.

```json
{
  "event_type": "validate-release",
  "client_payload": {
    "schema": "supervizio.validate-release/v1",
    "candidate": {
      "repository": "supervizio/agent",
      "tag": "v1.4.2",
      "resolved_commit": "<40 hex>",
      "release_id": 123456,
      "candidate_generation": 1,
      "manifest_file": "checksums.txt",
      "asset_manifest_digest": "sha256:<64 hex>"
    },
    "manifest": { "supervizio-amd64.deb": "<64 hex>", "…": "…" },
    "support": { "e2e-kit.tar.gz": "<64 hex>" },
    "bridge": { "package": "supervizio/agent-release-candidates", "digest": "sha256:<OCI manifest digest>" },
    "required_matrix": ["docker/amd64/debian-glibc", "…"]
  }
}
```

No URL and no credential travel in it; `bridge.package` must be the repository's
`bridge_package`. `test_suite_revision` does not travel either: a
`repository_dispatch` always runs the default branch's copy of the workflow, so the
dispatcher cannot choose it; the receipt records the one that ran.

Private side, in order: build and package; `manifest build --repository …` →
manifest file; write the body with `bridge.digest` empty; `bridge push --dispatch
body.json --dir <files> --tag <tag>-g<N> --output dispatch.json` (re-hashes every
file against the body before a byte leaves, sets the digest); `receipt pending
--dispatch dispatch.json` → attach to the draft; POST `dispatch.json`.

What `validate-release.yml` guarantees:

- `run-name` renders exactly `validate-release <repository> <tag> g<generation>
  <resolved_commit> <asset_manifest_digest>` (`dispatch run-name` prints it; about
  170 characters, and a 268-character run-name was measured to be kept whole);
  `admit` checks it. The runs API returns it as `display_title`; the dispatch
  payload itself is not retrievable afterwards, so this is what binds a run to one
  candidate.
- one job per scheduled leg, named exactly `leg/<leg id>` — or
  `e2e / leg/<leg id>` for a leg `e2e.yml` runs for the `e2e` job — that caller
  only, one level, nothing else counts; its conclusion is the leg's result. A leg of `required_matrix`
  this revision's policy cannot run is not scheduled, so it reads `missing` and the verdict is `error`: naming a leg never
  makes it pass. Advisory legs are scheduled too and land in `results`; the verdict
  ignores them.
- a leg whose release scenario is not wired (`policy.json` `scenario: null`) fails.
  **Today that is no production leg.** Every agent leg is `scenario: "e2e"`:
  `e2e.yml` runs it in release mode (above), and a required agent leg `e2e.yml`
  does not produce a job for reads `missing`. Every libprobe leg runs the `abi`
  scenario (section 5).
- a scenario runs in three steps: `scenario --stage prepare` on the leg's runner
  (checks the pulled files; for a harness, stages it in `work/`), the harness
  where the leg's platform lives (`policy.json` `harness.host`: the runner itself,
  a BSD guest the runner boots, or a container on it), and `scenario --stage
  check` on the runner, which judges what the harness left there. None of the
  three holds a token.
- no job references a secret; permissions per job as in D3.
- triggers are `repository_dispatch` and `workflow_dispatch` only — never
  `pull_request` or `pull_request_target`, so a fork's code never runs with a
  token that can read a candidate package. `workflow_dispatch` may select
  `tests/proof-policy.json` or `tests/e2e-proof-policy.json` (the production
  agent legs, on the measurement package, for a test candidate);
  `repository_dispatch` always uses `policy.json`.

## 5. The required matrix

`policy.json`, per repository. Each leg has an `id`, a `state`, the `runner` label
`validate-release.yml` schedules it on, and a `scenario` (`null` until its release
scenario is wired, which fails the leg; `integrity`, proof only; `abi`, below; `e2e`, run by `e2e.yml` in release mode rather
than by the generic `leg` job, whose `runner` is then documentation). A
leg whose scenario executes something names a `harness`: the `platform` whose
published archive it runs and the `host` it runs on (`native`, `freebsd`,
`openbsd`, `netbsd`, `container-ubuntu`, `container-alpine`, `container-scratch`).
States:

- `required` — must be in every receipt's `required_matrix`; decides the verdict.
- `advisory` — scheduled, recorded in `results`, never waited for by the verdict.
- `pending-merge` — exists only on an unmerged pull request (named in `pr`) and
  becomes `required` when it merges: a leg cannot be required before the workflow
  that runs it is on `main`. None today.

Rule, per brief §4.7: everything that gates today keeps gating for a release, and
BSD and container legs gate too — except libprobe's BSD **arm64** legs, advisory by
the owner's decision: no KVM on the arm64 runners, so QEMU emulates every
instruction and a leg takes one to two hours.

Inventory taken from `main` at `3b0f5b7` (#101, #102 and #110 merged).

**supervizio/agent** — 53 required (source: `e2e.yml`, every leg gating in merge CI):

| Legs | Count | Runner |
|---|---|---|
| `docker/{amd64,arm64}/{debian-glibc,alpine-musl,scratch}` | 6 | `ubuntu-24.04`, `ubuntu-24.04-arm` |
| `macos/amd64`, `macos/arm64` | 2 | `macos-15-intel`, `macos-15` |
| `windows/amd64` (Windows Server), `windows/arm64` (Windows 11) | 2 | `windows-2025`, `windows-11-arm` |
| `linux/amd64/{artix-dinit,debian-sysvinit,alpine-openrc,debian-systemd,rocky-systemd,opensuse-zypper,arch-pacman,alpine-runit,alpine-s6}` | 9 | `ubuntu-24.04` |
| `linux/arm64/{alpine-openrc,alpine-runit,alpine-s6,alpine-dinit,debian-systemd,debian-sysvinit,rocky-systemd,opensuse-zypper,arch-pacman}` | 9 | `ubuntu-24.04-arm` |
| `freebsd/{amd64,arm64}` (15.1), `netbsd/{amd64,arm64}` (10.1) | 4 | `ubuntu-24.04` (QEMU) |
| `openbsd/amd64/{7.3,7.4,7.5,7.6,7.7,7.8,7.9}`, `openbsd/arm64/{7.8,7.9}` | 9 | `ubuntu-24.04` (QEMU) |
| `linux-exotic/{386,armv7,riscv64,ppc64le,s390x}-{glibc,musl}`, `linux-exotic/armv6-musl`, `linux-exotic/loong64` | 12 | `ubuntu-24.04` (QEMU) |

`arm64-packages` gates the merge lane but is not a leg: it *builds* arm64 packages
on a public runner. A release carries its own arm64 packages, built privately, and
the release legs install those — packaging on the public side would need the
return path of brief §4.6, and nothing requires it.

**supervizio/libprobe** — 12 required, 3 advisory (source: `external-e2e.yml`):
`native/{linux,windows,macos}-{amd64,arm64}` and `bsd/{freebsd,openbsd,netbsd}-amd64`
(gating in merge CI since #110), `container/{ubuntu,alpine,scratch}` (advisory in
merge CI, gating for a release), `bsd/{freebsd,openbsd,netbsd}-arm64` (advisory in
both). In the release lane each runs the **`abi` scenario**, the ABI/runtime
harness of brief §4.1 (`harness/libprobe/`), on its own platform's published
archive — never a rebuild:

| Legs | Archive | Where the consumer is built and run |
|---|---|---|
| `native/linux-{amd64,arm64}` | `linux-{amd64,arm64}` | the runner, system `cc` |
| `native/macos-{amd64,arm64}` | `darwin-{amd64,arm64}` | the runner, Apple `cc` |
| `native/windows-amd64` | `windows-amd64` (`x86_64-pc-windows-gnu`) | the runner, MinGW `gcc` |
| `native/windows-arm64` | `windows-arm64` (`aarch64-pc-windows-gnullvm`) | the runner, llvm-mingw (pinned release, digest-checked) |
| `bsd/{freebsd,openbsd,netbsd}-{amd64,arm64}` | same name | a `vmactions` guest (15.1 / 7.9 / 10.1), the base system's `cc` |
| `container/ubuntu` | `linux-amd64` | an `ubuntu:24.04` container, its own `gcc` |
| `container/alpine` | `linux-amd64-musl` | an `alpine:3.21` container, its own `gcc`, static |
| `container/scratch` | `linux-amd64-musl` | built static in Alpine, run in a `FROM scratch` image holding only the binary |

What the scenario checks, in order. **prepare** (host, Python): the platform
tarball `libprobe-<platform>-<tag>.tar.gz` and `probe.h` are manifest entries;
the tarball holds exactly `libprobe.a`, `probe.h`, `metadata.json`, plain regular
files, each once, read as a stream and cut off at 256 MiB, 4 MiB and 64 KiB
respectively (a manifest-valid tarball is still candidate input); its `probe.h` is byte-identical to the published one; `metadata.json`
says `libprobe`, this tag, this platform, and the `abi_sha256` of this
`libprobe.a`. **harness** (`run.sh`, POSIX sh, a C compiler and nothing else):
`consumer.c` includes only `probe.h`, links only `libprobe.a` (plus the system
libraries a Rust staticlib needs), and asks the archive: `probe_get_version()`
equals the tag without its `v` — the check seven releases once failed;
`probe_get_abi_fingerprint()` is not 0; for ten carriers, `sizeof` from this header
on this target equals `probe_get_carrier_size()`, and an unknown name answers the
documented sentinel; then `probe_init`, `probe_collect_cpu` (cores > 0),
`probe_collect_memory` (total > 0), `probe_collect_smoke_json` (the versioned
envelope), `probe_free_string`, `probe_shutdown`, executed for real. It writes a
JSON report and exits non-zero on any failure. **check** (host, Python): the
report exists, names this version twice (asked and answered), carries every
required check, and every check is ok — so a harness that silently ran nothing
fails here too.

A link error is a leg failure, not a harness detail: a consumer would hit it.
Advisory BSD arm64 legs run the same scenario; with nothing to compile but one C
file they took 2 to 3 minutes each in the proof below, against one to two hours
for the source suite that made them advisory.

Legs are required per *environment*, not per asset: a published asset no leg
consumes is still bound by the manifest, but nothing executed it (section 10).

## 6. Pre-promotion verification

`verify-promotion` re-reads the world right before `gh release edit --draft=false`
and refuses unless **all** of these hold (each has a test that breaks it):

1. the receipt checked is the one **stored on the release**, and it is valid:
   schema, types, `asset_manifest_digest` recomputed from `manifest`, the verdict
   re-derived from `results`, `required_matrix` ⊇ policy;
2. `verdict` is `success` and every required leg's result is `success` — a
   cancelled, timed-out, skipped or missing leg refuses;
3. the tag still resolves (annotated tags peeled) to `resolved_commit` — a
   re-pointed or deleted tag refuses;
4. the release is still `release_id`, attached to `tag`, and a draft; the
   receipt's `candidate_generation` is the one the promotion was asked for;
5. the release's assets are exactly `manifest` ∪ {manifest file,
   `release-receipt.json`} — nothing missing, nothing extra — and every GitHub
   digest equals the validated sha256; the manifest file's equals
   `asset_manifest_digest`. A missing digest is unverifiable and refuses, unless
   `observe --hash-assets` hashed the downloaded bytes, which are then checked too.

Promotion protocol: `evidence` → final receipt → Garage copy → upload to the
release → `observe` → `verify-promotion --expect-generation N` → `--draft=false` →
dispatch the deploy (agent).

`verify-promotion --audit` checks a release that may already be published, with
one difference: the receipt is judged against **its own** `required_matrix` and
`manifest_file`, not today's `policy.json`. Tightening the policy never
invalidates a release validated before it — the same rule the brief sets for
`test_suite_revision`. Only a new candidate must meet the current policy.

## 7. Garage layout (`release-artifacts` bucket)

```
releases/<owner>/<repo>/<tag>/<asset_manifest_digest hex>/<filename>          every published asset + the manifest file
releases/<owner>/<repo>/<tag>/<asset_manifest_digest hex>/receipts/g<N>.json  every receipt written for those bytes
```

Addressed by digest, never overwritten: a rebuild with different bytes lands in
another directory. Restoring ("tag present, release absent"): pick the directory
whose latest receipt is `success` for the tag's current commit, verify every object
against its manifest file, recreate the release as a draft, and attach a receipt
carried over with the new `release_id`, the next `candidate_generation` and
`restored_from` naming the one replaced — then promote through section 6. No E2E is
re-run: the bytes are digest-identical to validated ones.

## 8. reconcil-release

The contract gives reconcil-release a decidable state per `(tag, release)`:

| Observed | Contract reading | Action |
|---|---|---|
| published, receipt `success`, `verify-promotion --audit` passes | validated | nothing |
| draft, receipt `success`, `verify-promotion` passes | crashed before publication | resume promotion, no rebuild |
| draft, receipt `pending` | validation in flight or lost | if no run is going, re-dispatch the same bytes, no rebuild |
| draft, receipt `error` | no evidence | re-dispatch only with `force_revalidate` |
| draft, receipt `failure` | candidate is bad | nothing automatic |
| tag, no release | lost release | restore from Garage (section 7), else new candidate |
| release, no tag | orphan | delete per policy, never rebuild |
| published, no receipt | legacy | mark unverified, never rebuild |
| receipt present, `verify-promotion --audit` refuses on tag or assets | receipt invalidated | new candidate, explicitly |

## 9. Measurements

| What | Result | How |
|---|---|---|
| Actions retention | `{"days":7,"maximum_allowed_days":7}` | `GET /repos/supervizio/runner-template/actions/permissions/artifact-and-log-retention` |
| Status `description` | 140 chars → 201; 141 → 422 "Description is too long (maximum is 140 characters)" | `POST /repos/{r}/statuses/{sha}` on a throwaway commit |
| Status `context` | 255 → 201; 256 → 422 | same |
| Status `target_url` | 65535 chars accepted and read back intact | same |
| Combined status | `.statuses` holds 30 of 35 while `total_count` is 35; `per_page=100` or `--paginate` gives 35 | `GET /repos/{r}/commits/{sha}/status` |
| Check run, user OAuth token | 403 "You must authenticate via a GitHub App." | `POST /repos/{r}/check-runs` |
| Check run, `GITHUB_TOKEN` + `checks: write` | text of 65535 chars → 201; 65536 → 422; read back intact via `check_name` | `release-contract-proof.yml` |
| Draft release, `GITHUB_TOKEN` `contents: read` | absent from the list; get, list assets, download → 403 | `release-contract-proof.yml` |
| Draft release, `permissions: {}` / no token | 403 / 404 | `release-contract-proof.yml` |
| Asset digests | GitHub `digest` = local sha256 for every asset (3 MB random included); manifest file digest = `asset_manifest_digest` | `release-contract-proof.yml`, `observe --hash-assets` |
| Validator, live | `verify-promotion` passes on the draft, refuses after an asset is replaced and after the tag is re-pointed | `release-contract-proof.yml` |
| Run title | a 268-character `run-name` comes back whole as `display_title` | `release-contract-proof.yml`, runs API |
| Signed asset URL | JWT `exp` = `nbf` + 300 s | `GET /repos/{r}/releases/assets/{id}` with `Accept: application/octet-stream`, `Location` decoded |
| GHCR bridge, publisher | a private repository's `GITHUB_TOKEN` (`packages: write`) pushes a private org package and reads it back | supervizio/agent, branch `ci/ghcr-bridge-measure`, self-hosted runner |
| GHCR bridge, reader | before the grant: `packages: read`, `permissions: {}` and no token all denied; after granting runner-template Read on that one package: `packages: read` → manifest 200, blob byte-identical | runner-template branch `measure/ghcr-bridge` |
| Fork pull requests | `approval_policy: all_external_contributors` on the repository and the organisation: a fork's workflow does not run before a maintainer approves it | `GET /repos/supervizio/runner-template/actions/permissions/fork-pr-contributor-approval` |
| libprobe `abi` scenario, live (2026-09-26) | the bytes of the published libprobe **v0.7.0** release re-pushed as a candidate: all 15 legs `success` (12 required, 3 advisory BSD arm64), each `probe_get_version()` = `0.7.0`, 18 consumer checks; the same `libprobe.a` repackaged as `v0.7.1` with a `metadata.json` that says so (the v0.2.1..v0.6.0 defect): every prepare check passes, all 15 legs fail on `version: archive says 0.7.0, the release is 0.7.1`, verdict `failure` | `tests/proof-policy.json`, candidates pushed from supervizio/agent to the proof package; runs and package versions deleted, output recorded in the pull request |
| `validate-release.yml`, live (2026-09-26) | conforming candidate: verdict `success` on Linux, macOS and Windows legs; one byte changed in one file: `admit` refuses, verdict `error`; a required leg the policy cannot run: `missing`, verdict `error`; `evidence` refuses to build a receipt from any of these runs (`workflow_dispatch`, not `main`) | `tests/proof-policy.json`, candidate of random bytes pushed from supervizio/agent; runs deleted, output recorded in runner-template#107 |

## 10. Open questions (phases 3 to 5)

- **Release scenarios.** agent: `e2e.yml` in release mode (section 4), fed by
  the support file `e2e-kit.tar.gz` and the published assets. libprobe's legs
  run the `abi` scenario (section 5).
  What it does not cover: 13 of the 26 platform archives of a libprobe release
  (`linux-arm64-musl`, and every 32-bit and exotic Linux archive: arm, armv6, 386,
  riscv64, ppc64le, s390x, loong64, glibc and musl) are bound by the manifest but
  executed by no leg. QEMU user-mode legs like agent's `linux-exotic/*` would
  cover them.
- **Fork tokens.** No release-lane workflow runs on `pull_request`, and a fork's
  workflows need approval (section 9). Not measured: whether an *approved* fork
  pull request's read-only `GITHUB_TOKEN` can read a package granted to this
  repository. `docker-images.yml` (inherited) runs on `pull_request` and asks for
  `packages: write`; reviewers of a fork pull request must treat any workflow it
  adds or changes as able to try.
- **Coverage per asset.** Both repositories publish assets that no leg of the
  matrix executes. Say which must be exercised, or record them in the receipt as
  unexercised. agent, today: the legs install the amd64 and arm64 `.deb`,
  `.rpm`, `.apk`, `.pkg.tar.zst`, the eleven exotic-arch packages, both OpenBSD
  `.tgz`, and run the raw Linux amd64/arm64 (glibc and musl), loong64, macOS,
  Windows `.exe`, FreeBSD and NetBSD binaries. Nothing executes the macOS
  `.pkg`, the Windows `.zip` and `.nupkg`, the FreeBSD `.pkg`, the NetBSD
  `.tgz`, the `.rpm`/`.pkg.tar.zst` of the other arches, or the remaining raw
  Linux binaries (agent's release job does prove the raw OpenBSD binaries are
  the bytes inside the tested `.tgz`).
- **Private side changes** (not made here): `create-release` builds the manifest
  file (`manifest build --repository …`), `bridge push`es the candidate, attaches
  the pending receipt and dispatches; a promotion workflow `on: status` (context
  `release-validation/…`) runs `evidence --run-id`, uploads the receipt (Garage
  copy first), `observe`, `verify-promotion --expect-generation N`, then
  `--draft=false`; `delete-release` and `reconcil-release` read the receipt as in
  section 8 and may delete package versions of abandoned candidates. Both pin this
  directory by commit SHA, and the owner grants runner-template Read on each
  `*-release-candidates` package once it exists.
