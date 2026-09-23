# Release contract — v1

What a release of `supervizio/agent` or `supervizio/libprobe` must prove before it
leaves draft, in a form a machine checks. This directory is the single source of
truth for it; the two private repositories consume it pinned by commit SHA, and
this repository's release-validation lane (`validate-release.yml`, still to be
written) implements the public half.

| File | Role |
|---|---|
| `README.md` | the normative text (this file) |
| `release_contract.py` | its only implementation — stdlib Python ≥ 3.9, no dependency; every workflow calls it instead of re-deriving a rule in shell |
| `policy.json` | the required matrix per repository, and the per-repository names below |
| `tests/` | the validator's tests, and the manifest test vector any other implementation must reproduce |

The unit of trust is **a set of bytes, not a commit**. The same commit built twice
can yield different bytes (injected version, dependency drift, floating toolchain),
so everything below is bound to the digest of the published assets, and the commit
is recorded only as provenance.

```
private repository (agent | libprobe)                 runner-template (public)
─────────────────────────────────────                 ────────────────────────
tag push → build, package, sign
  draft release + manifest file + release-receipt.json {verdict: pending}
  copy of the candidate → Garage (private)
  copy of the candidate → staging draft here ──────►  validate-release.yml  (no secret)
  repository_dispatch validate-release ────────────►    admit: staging == manifest
                                                        leg/<id> × required matrix
                                                        report
promotion job ◄────────────── doorbell ────────────   run completed
  evidence = the run's jobs, read from the public API
  release-receipt.json {verdict: success | failure | error}  (+ copy → Garage)
  verify-promotion → gh release edit --draft=false → deploy
```

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

**D3 — The bridge to the public runners is a staging draft release in this
repository.** This departs from brief §4.6, which exposed Garage through a public
vhost and handed presigned URLs to the hosted runners. Garage is now reachable from
the private side only, so something else has to carry the candidate bytes:

| Candidate bridge | Why not |
|---|---|
| The private repository's own draft, read with a read-only token | Measured: a draft is invisible to anything without push access — `contents:read` gets 403, no token 404. The REST docs agree ("Only users with push access will receive listings for draft releases"). A token that can read the private draft can write the private repository's releases, and it would be stored here, in a public repository. |
| Cross-repository Actions artifacts (the `AGENT_REPO_TOKEN` pattern of `e2e.yml`) | The public side must hold a credential on the private repository, and GitHub only scrubs from runner memory the secrets "not referenced in the workflow" ([compromised runners](https://docs.github.com/en/actions/concepts/security/compromised-runners)) — per workflow, not per job — so the legs running candidate code would share memory space with it. It also stores every candidate twice in the private repositories' Actions storage. |
| Signed download URLs of the private draft's assets, in the payload | Measured: the redirect URL carries a JWT valid 300 seconds — shorter than a queue. |
| Public Garage with presigned URLs (brief §4.6) | Garage is private. |

So the private release job, which already holds a token with `contents: write` on
this repository (the one it uses to send `repository_dispatch`), uploads the
candidate files to a **draft release of runner-template** — the *staging release* —
and dispatches. Drafts are invisible to the public. `validate-release.yml`
references **no secret at all**: its only credentials are the per-job
`GITHUB_TOKEN`s GitHub mints with each job's own permissions.

- `admit` — `contents: write` (the only way to read a draft, measured) and nothing
  else. It never executes candidate bytes. It checks the staging release against
  the dispatched manifest (every GitHub digest), downloads the files, re-hashes
  them, and hands them to the legs as a same-run artifact with `retention-days: 1`.
- `leg/<id>` — `permissions: {}` and no secret. Each leg re-hashes every file it
  consumes against the manifest pinned by `asset_manifest_digest` (`manifest
  verify-files`) before executing anything, including packaged install scripts.
- the last job deletes the staging artifact (`actions: write`). A retry is a full
  re-run: `admit` stages again from the staging release, which the private side
  deletes only once the final receipt is written.

The bridge is untrusted by construction: integrity is end to end, from the digest
the private side computed to the hash each leg recomputes. **Residual
exposure:** an artifact of a public repository can be downloaded by any signed-in
GitHub user while it exists, so a candidate is readable for the duration of its
validation run. agent's candidates are headed for public package repositories
anyway; for libprobe's archives this is an owner decision (section 10).

Garage is the durable store of *validated* bytes: written only from the private
side, read by reconcil-release to restore a release (section 7).

**D4 — The verdict comes from the public run, never from a callback.** The
promotion job reads the finished `validate-release.yml` run through the public REST
API — the run, and its jobs with `filter=latest`, paginated. Whatever wakes it up
(section 10) is a doorbell: it may name the run, but a forged doorbell cannot
promote anything, because nothing it says is believed. Consequence:
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
| `support` | object | `{filename: sha256}` of staged-only test inputs (e.g. a test kit built from the private tree); may be `{}`; never published, never overlapping `manifest` |
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
this one has 6, and a 62-asset agent release with all 53 inventoried legs stays
under 16 KiB (tested). The validator enforces both limits on the whole body.

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
    "staging": { "repository": "supervizio/runner-template", "release_id": 987654, "tag_name": "stage/agent/v1.4.2/g1" },
    "required_matrix": ["docker/amd64/debian-glibc", "…"]
  }
}
```

No URL and no credential travel in it. `test_suite_revision` does not either: a
`repository_dispatch` always runs the default branch's copy of the workflow, so the
dispatcher cannot choose it; the receipt records the one that ran.

Rules for `validate-release.yml` (Phase 3):

- `run-name` renders exactly `validate-release <repository> <tag> g<generation>
  <resolved_commit> <asset_manifest_digest>` (`dispatch run-name` prints it; about
  170 characters, and a 268-character run-name was measured to be kept whole). The
  runs API returns it as `display_title`; the dispatch payload itself is not
  retrievable afterwards, so this is what binds a run to one candidate.
- `admit` runs `dispatch check` first (payload shape, limits, and `required_matrix`
  against *this* revision's policy — a stale dispatcher is refused, not trusted).
- one job per leg, named exactly `leg/<leg id>`; its conclusion is the leg's result.
- no job references a secret; permissions per job as in D3.
- the staging release holds files whose sha256 equals their `manifest` or `support`
  entry, plus the manifest file; it may omit published assets no leg consumes.

## 5. The required matrix

`policy.json`, per repository. A leg in state `required` must be in every
receipt's `required_matrix`; `pending-merge` legs exist only on an unmerged pull
request and become `required` when it merges — a leg cannot be required before the
workflow that runs it is on `main`. Rule, per brief §4.7: everything that gates
today keeps gating for a release, and BSD and container legs gate too.

Inventory taken from `main` at `66c96c0` (which includes #101, merged on
2026-09-23) and from the head of #102 at `c29592c`. **#102 is not merged**: its
legs are `pending-merge`.

**supervizio/agent** — 41 required, 12 pending (source: `e2e.yml`, every leg gating in merge CI):

| Legs | Count | Runner |
|---|---|---|
| `docker/{amd64,arm64}/{debian-glibc,alpine-musl,scratch}` | 6 | `ubuntu-24.04`, `ubuntu-24.04-arm` |
| `macos/amd64`, `macos/arm64` | 2 | `macos-15-intel`, `macos-15` |
| `windows/amd64` (Windows Server), `windows/arm64` (Windows 11) | 2 | `windows-2025`, `windows-11-arm` |
| `linux/amd64/{artix-dinit,debian-sysvinit,alpine-openrc,debian-systemd,rocky-systemd,opensuse-zypper,arch-pacman,alpine-runit,alpine-s6}` | 9 | `ubuntu-24.04` |
| `linux/arm64/{alpine-openrc,alpine-runit,alpine-s6,alpine-dinit,debian-systemd,debian-sysvinit,rocky-systemd,opensuse-zypper,arch-pacman}` | 9 | `ubuntu-24.04-arm` |
| `freebsd/{amd64,arm64}` (15.0), `netbsd/{amd64,arm64}` (10.1) | 4 | `ubuntu-24.04` (QEMU) |
| `openbsd/amd64/{7.3,7.4,7.5,7.6,7.7,7.8,7.9}`, `openbsd/arm64/{7.8,7.9}` | 9 | `ubuntu-24.04` (QEMU) |
| *pending #102:* `linux-exotic/{386,armv7,riscv64,ppc64le,s390x}-{glibc,musl}`, `linux-exotic/armv6-musl`, `linux-exotic/loong64` | 12 | `ubuntu-24.04` (QEMU) |

`arm64-packages` gates the merge lane but is not a leg: it *builds* arm64 packages
on a public runner. A release carries its own arm64 packages, built privately, and
the release legs install those — packaging on the public side would need the
return path of brief §4.6, and nothing requires it.

**supervizio/libprobe** — 15 required (source: `external-e2e.yml`): `native/{linux,windows,macos}-{amd64,arm64}`
(gating in merge CI), `bsd/{freebsd,openbsd,netbsd}-{amd64,arm64}` and
`container/{ubuntu,alpine,scratch}` (advisory in merge CI, gating for a release). In
the release lane each runs the ABI/runtime harness of brief §4.1 — a consumer that
links the published `libprobe.a` and `probe.h`, not a rebuild — which does not
exist yet.

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

## 10. Open questions (phases 3 to 5)

- **Doorbell.** What wakes the promotion job. Recommended: a `workflow_run`
  workflow here, on `validate-release.yml` completion, posting a commit status on
  the private repository with a fine-grained token holding *only* commit statuses:
  write — the private side listens with `on: status`. Kept out of
  `validate-release.yml` so that workflow references no secret. Alternative: poll
  from the private side, at the cost of holding a runner for hours.
- **libprobe exposure.** Accept that a libprobe candidate is downloadable by
  signed-in users during its validation run (D3), or move that lane to a private
  package the legs read with `packages: read`.
- **Coverage per asset.** Both repositories publish assets that no leg of the
  matrix executes. Say which must be exercised, or record them in the receipt as
  unexercised.
- **Test kit.** agent's legs read `setup/`, `e2e/` and other files from the private
  tree today; the release lane has no source token, so they travel as `support`
  files built privately and bound by digest.
- **Private side changes** (not made here): generate the manifest file with
  `manifest build --repository …` (byte order), attach `release-receipt.json`,
  upload the staging release, and pin this directory by commit SHA.
