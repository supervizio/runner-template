<!-- updated: 2026-09-29T00:00:00Z -->
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
   `online`.
2. `validate-probe.sh`, then `validate-detection.sh` against agent's
   `e2e/expected-matrix.json` column (`SVZ_KEY`: `omnios-amd64`,
   `solaris-amd64`).
3. An SMF cycle: `svcadm disable -s` stops it, `svcadm enable -s` brings it
   back, and a SIGKILLed supervizio is restarted by SMF under a new pid.
4. The supervision battery (`scenario-battery.sh`).
5. `uninstall.sh`: no service, no binary, no manifest left.
6. The IPS archive through install.sh: pkg(5) must own it, the manifest's
   actuator must have registered the service online, and `uninstall.sh`
   (`pkg uninstall`) must leave nothing behind.

POSIX `sh`: the guests' `/bin/sh` is ksh93, and ksh93 remembers which PATH
directories did not exist when PATH was set -- set PATH after installing
anything into a new directory. `/usr/gnu/bin` comes first for the GNU tools
agent's scripts expect on Solaris. `envs:` names the environment the script
reads (`SVZ_KEY`, `SVZ_OS`): ssh forwards nothing else.
