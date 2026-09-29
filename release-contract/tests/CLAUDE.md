<!-- updated: 2026-09-29T00:00:00Z -->
# release-contract/tests/

`python3 -m unittest discover -s release-contract/tests`, run by
`release-contract.yml` on Linux, macOS, Windows and Python 3.9.

| File | What |
|------|------|
| `test_release_contract.py` | the validator: manifests, receipts, dispatch bodies, verdicts, the shipped policy's shape and size (agent: 66 legs, all required; libprobe: 14 required, 3 advisory) |
| `test_live_proof.py` + `live_proof.py` | the documents `release-contract-proof.yml` stages on a live draft, tested offline |
| `proof-policy.json` | integrity-only agent legs, and the production libprobe legs with their `abi` scenario, for hand-run lanes on the bridge probe package. It omits `solarish/illumos-amd64` and `solarish/solaris-amd64` until a published libprobe release carries those archives |
| `e2e-proof-policy.json` | every production agent leg, on the bridge probe package, for a test candidate: kept equal to `policy.json`'s agent legs, the Gentoo, NixOS, illumos and Solaris ones included |
| `vectors/` | the manifest test vector any other implementation must reproduce |

A leg added to `policy.json` changes the counts `ShippedPolicy` and `LegMatrix`
assert: both move in the same change.

Two guards tie the libprobe harness to the workflow: every libprobe leg's
platform must match a `case` arm of `harness/libprobe/run.sh`, and every guest
host in `HARNESS_HOSTS` must be booted by `.github/workflows/validate-release.yml`
and listed by both steps that stage and run the harness in a guest.
