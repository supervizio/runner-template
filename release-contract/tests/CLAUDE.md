<!-- updated: 2026-09-29T00:00:00Z -->
# release-contract/tests/

`python3 -m unittest discover -s release-contract/tests`, run by
`release-contract.yml` on Linux, macOS, Windows and Python 3.9.

| File | What |
|------|------|
| `test_release_contract.py` | the validator: manifests, receipts, dispatch bodies, verdicts, the shipped policy's shape and size (agent: 64 legs, all required) |
| `test_live_proof.py` + `live_proof.py` | the documents `release-contract-proof.yml` stages on a live draft, tested offline |
| `proof-policy.json` | integrity-only legs for hand-run lanes on the bridge probe package |
| `e2e-proof-policy.json` | every production agent leg, on the bridge probe package, for a test candidate: kept equal to `policy.json`'s agent legs, the Gentoo and NixOS ones included |
| `vectors/` | the manifest test vector any other implementation must reproduce |

A leg added to `policy.json` changes the counts `ShippedPolicy` and `LegMatrix`
assert: both move in the same change.
