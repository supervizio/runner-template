<!-- updated: 2026-09-30T00:00:00Z -->
# .github/solarish-leg/

`in-guest.sh` is what `e2e.yml`'s `e2e-illumos-amd64` (OmniOS r151054) and
`e2e-solaris-amd64` (Oracle Solaris 11.4) legs run inside their `vmactions`
guest, from the synced workspace: agent's `e2e/` and `setup/` at the root,
`bin/supervizio` and `pkg/supervizio-<os>-amd64.p5p` beside them. One file for
both kernels because `uses:` takes no expression (one step per guest action)
and shellcheck reads a file, not YAML.

What it asserts, in order:

1. The raw binary through agent's `setup/install.sh`: no package it may
   download, so install.sh installs `/usr/local/bin/supervizio` and grafts
   `/lib/svc/manifest/site/supervizio.xml` itself. The service must reach
   `online` AND hold a live supervizio that is still the same process five
   seconds later (`running`): a supervisor that exits at startup is `online`
   for an instant, its zombie listed as `<defunct>` by `svcs -p` — which is
   how a startup refusal once passed this step.
2. `validate-probe.sh`, then `validate-detection.sh` against agent's
   `e2e/expected-matrix.json` column (`SVZ_KEY`: `omnios-amd64`,
   `solaris-amd64`).
3. An SMF cycle: `svcadm disable -s` stops it, `svcadm enable -s` brings it
   back, and a SIGKILLed supervizio is restarted by SMF under a new pid with
   the service `online` again — a new pid alone does not pass.
4. The supervision battery (`scenario-battery.sh`).
5. `uninstall.sh`: no service, no binary, no manifest left.
6. The IPS archive through install.sh: pkg(5) must own it, the manifest's
   actuator must have registered the service and it must be `running`, and
   `uninstall.sh`
   (`pkg uninstall`) must leave nothing behind.

In the merge lane both legs run only when the agent run built their kernel:
agent builds illumos/Solaris for a pull request that touches their paths, and
for every release. With neither artifact the leg is skipped and `report` reads
`not-built` (`../workflows/CLAUDE.md`, "When they run"). In release mode they
always run.

POSIX `sh`: the guests' `/bin/sh` is ksh93, and ksh93 remembers which PATH
directories did not exist when PATH was set -- set PATH after installing
anything into a new directory. `/usr/gnu/bin` comes first for the GNU tools
agent's scripts expect on Solaris. `envs:` names the environment the script
reads (`SVZ_KEY`, `SVZ_OS`): ssh forwards nothing else.

## libprobe-tests.sh

What `libprobe-solarish.yml` runs in its OmniOS and Solaris guests: the bundle
libprobe cross-built on its own runner (`bin/` and `plan.txt`, no source),
stage by stage. Plan lines are `run <stage> <binary> [args]`, `report <stage>
<binary> [args]` (stdout kept as `<stage>.json`) and `abi <stage> <checker>
<binary> [args]` (the binary's output fed to the checker). Every stage's
output goes to `<report>/<stage>.log`, which the workflow uploads for one day;
the console gets `=== ` lines only. Every command reads `/dev/null`, never the
plan being read; the plan's words are split, never globbed. POSIX `sh`, exits
0, verdict in `<report>/status`.
