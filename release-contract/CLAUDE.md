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
| `policy.json` | the required matrix: agent 66 legs, all `required`, all `scenario: "e2e"` (run by `e2e.yml` in release mode); libprobe 14 required + 3 advisory, `scenario: "abi"` |
| `harness/libprobe/` | the ABI consumer the libprobe legs build against a candidate's published `probe.h` and `libprobe.a`; see `harness/libprobe/CLAUDE.md` |
| `tests/` | see `tests/CLAUDE.md` |

A leg id in `policy.json` must be exactly the `leg/<id>` job name `e2e.yml`
gives it in release mode, or it reads `missing` and no candidate can pass. The
agent legs include `linux/{amd64,arm64}/gentoo-portage` and
`linux/{amd64,arm64}/nixos-nix` (agent's Gentoo overlay and Nix flake,
rendered from the candidate and installed through Portage and NixOS), and
`illumos/amd64` (OmniOS r151054) and `solaris/amd64` (Oracle Solaris 11.4):
the candidate's raw binary and IPS archive, each installed through install.sh
and run under SMF.

## libprobe hosts

A libprobe leg's `harness.host` is one of `HARNESS_HOSTS`: `native` (the
runner), the guests `freebsd`, `openbsd`, `netbsd`, `omnios` (the illumos
archive) and `solaris` (the Solaris 11.4 archive), or the containers
`container-ubuntu`, `container-alpine`, `container-scratch`. A guest host needs
a boot step in `.github/workflows/validate-release.yml`, and a leg's platform a
`case` arm in `harness/libprobe/run.sh`: `tests/test_release_contract.py` fails
on either gap. `solarish/illumos-amd64` and `solarish/solaris-amd64` have no
merge-lane twin here: libprobe's own CI runs its source in those two guests,
because that compiles private code this repository never checks out.

## Changing the contract

README, `release_contract.py` and the tests move together; a new receipt field
is a new schema version; a new required leg is a `policy.json` change (and
`tests/e2e-proof-policy.json`, which mirrors the production agent legs). The
private side computes a candidate's `required_matrix` from the policy at ITS
pinned commit, and `dispatch check` refuses a matrix that omits a leg `main`'s
policy requires: from the merge of a new required leg, agent must bump
`.github/release-contract.sha` and libprobe its pinned contract commit, or
their release admission refuses the new leg. Merge the legs, then bump the
pins, with no release between.
