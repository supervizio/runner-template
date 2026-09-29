<!-- updated: 2026-09-29T00:00:00Z -->
# release-contract/

The release contract of supervizio/agent and supervizio/libprobe. `README.md`
is normative; `release_contract.py` (stdlib Python >= 3.9) is its only
implementation, and the two private repositories pin this directory by commit
and call the script rather than re-derive any rule.

| Path | What |
|------|------|
| `README.md` | the contract: manifest, receipt, dispatch, required matrix (section 5 counts the legs per repository), promotion checks |
| `release_contract.py` | the validator and every subcommand the workflows call |
| `policy.json` | the required matrix: agent 64 legs, all `required`, all `scenario: "e2e"` (run by `e2e.yml` in release mode); libprobe 12 required + 3 advisory, `scenario: "abi"` |
| `harness/libprobe/` | the ABI consumer the libprobe legs build against a candidate's published `probe.h` and `libprobe.a` |
| `tests/` | see `tests/CLAUDE.md` |

A leg id in `policy.json` must be exactly the `leg/<id>` job name `e2e.yml`
gives it in release mode, or it reads `missing` and no candidate can pass. The
agent legs include `linux/{amd64,arm64}/gentoo-portage` and
`linux/{amd64,arm64}/nixos-nix`: agent's Gentoo overlay and Nix flake,
rendered from the candidate and installed through Portage and NixOS.

Changing the contract: README, `release_contract.py` and the tests move
together; a new receipt field is a new schema version; a new required leg is a
`policy.json` change (and `tests/e2e-proof-policy.json`, which mirrors the
production agent legs), and agent must then bump `.github/release-contract.sha`
or its release admission refuses the new leg.
