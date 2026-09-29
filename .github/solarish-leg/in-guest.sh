#!/bin/sh
# Runs INSIDE an OmniOS (illumos) or Oracle Solaris 11.4 guest, from the
# workspace e2e.yml's leg synced in: agent's scripts (e2e/, setup/) at the
# root, bin/supervizio and pkg/supervizio-<os>-amd64.p5p beside them.
#
# The agent goes on the guest twice, through agent's own install.sh each time:
#   1. the raw binary: install.sh finds no package it may download, installs
#      the binary and grafts SMF itself (setup/init/smf/supervizio.xml);
#   2. the IPS archive: pkg(5) installs it, and the manifest's actuator has
#      manifest-import register the same service.
# After each install the service must be online under SMF; after each
# uninstall it must be gone, with its binary and manifest. The probe, the
# detection matrix and an SMF cycle run on the first; the supervision battery
# runs once, the binary being the same.
#
# Environment, named in the step's `envs:` (ssh forwards nothing else):
#   SVZ_KEY  the expected-matrix.json column (omnios-amd64 | solaris-amd64)
#   SVZ_OS   illumos | solaris (names the .p5p)
#
# POSIX sh: the guest's /bin/sh is ksh93.
set -eu

WS="$(pwd)"
: "${SVZ_KEY:?}" "${SVZ_OS:?}"
FMRI=svc:/application/supervizio:default
BIN=/usr/local/bin/supervizio
MANIFEST=/lib/svc/manifest/site/supervizio.xml

echo "=== Platform"
uname -a
head -1 /etc/release
# Solaris keeps the GNU tools the agent's scripts expect under /usr/gnu/bin.
PATH="/usr/gnu/bin:/usr/bin:/usr/sbin:/sbin:$PATH"
export PATH
command -v jq >/dev/null || { echo "::error::jq is missing: the validators need it"; exit 1; }

state() { svcs -H -o state "$FMRI" 2>/dev/null || true; }

# wait_state <state>: up to 60 s for the instance to reach <state>.
wait_state() {
  i=0
  while [ "$i" -lt 60 ]; do
    [ "$(state)" = "$1" ] && return 0
    sleep 1
    i=$((i + 1))
  done
  echo "::error::$FMRI is '$(state)', not '$1', after 60s"
  svcs -xv "$FMRI" 2>&1 || true
  tail -30 /var/svc/log/application-supervizio:default.log 2>/dev/null || true
  return 1
}

# gone: no service, no binary, no manifest.
gone() {
  i=0
  while [ "$i" -lt 30 ] && svcs -H "$FMRI" >/dev/null 2>&1; do
    sleep 1
    i=$((i + 1))
  done
  if svcs -H "$FMRI" >/dev/null 2>&1; then echo "::error::the SMF service survived the uninstall"; return 1; fi
  if [ -e "$BIN" ]; then echo "::error::$BIN survived the uninstall"; return 1; fi
  if [ -e "$MANIFEST" ]; then echo "::error::$MANIFEST survived the uninstall"; return 1; fi
  echo "OK: service, binary and manifest are gone"
}

# The supervizio SMF started: the one whose command line is the manifest's.
# A zombie has no arguments, so an exited supervizio never matches.
main_pid() { pgrep -f "^$BIN --config /etc/supervizio/config.yaml" | head -1; }

# running: online, with a live supervizio that is still the same process 5 s
# later. online alone is svc.startd's view the moment the start method ran: a
# supervisor that exits at startup is online for an instant (svcs -p shows its
# zombie as <defunct>), then restarted until SMF puts it in maintenance.
running() {
  wait_state online || return 1
  pid="$(main_pid)"
  sleep 5
  if [ -z "$pid" ] || [ "$(main_pid)" != "$pid" ] || [ "$(state)" != online ]; then
    echo "::error::no supervizio stayed up in $FMRI (pid '$pid', now '$(main_pid)', state '$(state)')"
    svcs -p "$FMRI" 2>&1 || true
    tail -30 /var/svc/log/application-supervizio:default.log 2>/dev/null || true
    return 1
  fi
  svcs -p "$FMRI"
}

echo "=== 1. The raw binary, through install.sh (SMF grafted by install.sh)"
SUPERVIZIO_LOCAL_BIN="$WS/bin/supervizio"
export SUPERVIZIO_LOCAL_BIN
chmod +x "$SUPERVIZIO_LOCAL_BIN"
sh "$WS/setup/install.sh" || { echo "::error::install.sh (binary) failed"; exit 1; }
[ -x "$BIN" ] || { echo "::error::$BIN not installed"; exit 1; }
"$BIN" --version
[ -f "$MANIFEST" ] || { echo "::error::no SMF manifest at $MANIFEST"; exit 1; }
running || exit 1
echo "OK: SMF runs supervizio"

echo "=== Validate probe"
sh "$WS/e2e/validate-probe.sh" "$BIN" || { echo "::error::validate-probe.sh failed"; exit 1; }

echo "=== Detection vs expected-matrix ($SVZ_KEY)"
"$BIN" --probe > /tmp/probe.json
"$BIN" --inventory all > /tmp/inventory.json \
  || echo "::warning::--inventory all exited non-zero; validating the dump it wrote"
jq -c '.init_system.data' /tmp/inventory.json || true
jq -c '[.package_managers.data.managers[]? | select(.available)]' /tmp/inventory.json || true
sh "$WS/e2e/validate-detection.sh" "$SVZ_KEY" /tmp/probe.json /tmp/inventory.json \
  || { echo "::error::detection drifted from expected-matrix for $SVZ_KEY"; exit 1; }

echo "=== SMF cycle: disable, enable, and a killed supervizio comes back"
svcadm disable -s "$FMRI"
wait_state disabled
if pgrep -f "^$BIN " >/dev/null; then echo "::error::supervizio still runs with the service disabled"; exit 1; fi
svcadm enable -s "$FMRI"
wait_state online
before="$(main_pid)"
[ -n "$before" ] || { echo "::error::no supervizio process under the online service"; exit 1; }
kill -9 "$before"
i=0
after=""
while [ "$i" -lt 60 ]; do
  after="$(main_pid)"
  [ -n "$after" ] && [ "$after" != "$before" ] && [ "$(state)" = online ] && break
  sleep 1
  i=$((i + 1))
done
[ -n "$after" ] && [ "$after" != "$before" ] || { echo "::error::SMF did not restart supervizio after SIGKILL (pid $before)"; exit 1; }
echo "OK: pid $before killed, SMF started pid $after"

echo "=== Supervision scenarios"
sh "$WS/e2e/scenario-battery.sh" "$BIN" || { echo "::error::scenario-battery.sh failed"; exit 1; }

echo "=== Uninstall (binary)"
SUPERVIZIO_NON_INTERACTIVE=true
export SUPERVIZIO_NON_INTERACTIVE
sh "$WS/setup/uninstall.sh"
gone

echo "=== 2. The IPS archive, through install.sh"
unset SUPERVIZIO_LOCAL_BIN
SUPERVIZIO_LOCAL_PKG="$WS/pkg/supervizio-$SVZ_OS-amd64.p5p"
export SUPERVIZIO_LOCAL_PKG
[ -f "$SUPERVIZIO_LOCAL_PKG" ] || { echo "::error::no $SUPERVIZIO_LOCAL_PKG"; exit 1; }
sh "$WS/setup/install.sh" || { echo "::error::install.sh (package) failed"; exit 1; }
pkg list -H application/supervizio || { echo "::error::pkg(5) does not own supervizio: install.sh did not take the IPS path"; exit 1; }
pkg info application/supervizio | sed -n '1,12p'
[ -x "$BIN" ] || { echo "::error::the package installed no $BIN"; exit 1; }
running || exit 1
"$BIN" --version
"$BIN" --probe | jq -e '.os.platform.value' >/dev/null || { echo "::error::--probe from the packaged binary failed"; exit 1; }
echo "OK: the package's service is online"

echo "=== Uninstall (package)"
sh "$WS/setup/uninstall.sh"
if pkg list -H application/supervizio >/dev/null 2>&1; then echo "::error::the package is still installed"; exit 1; fi
gone
if pkg publisher -H 2>/dev/null | grep -q '^supervizio'; then echo "::warning::the supervizio publisher is still configured"; fi
echo "=== done"
