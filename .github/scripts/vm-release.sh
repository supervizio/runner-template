#!/usr/bin/env bash
# vm-release.sh - Release a Proxmox VM (remove lock)
#
# Usage: vm-release.sh <NAME_OR_VMID>
#
# The argument is used for logging only. Actual communication uses VM_IP
# from the environment (set by vm-acquire.sh).
#
# Required env vars:
#   SSH_OPTS         - SSH options string
#   VM_IP            - IP address of the VM (set by vm-acquire.sh)
#
# The script removes the /usebyjob lock file so other jobs can acquire
# the VM. The VM stays running — vm-cleanup resets all VMs to "base"
# snapshot at the end of the pipeline.
set -euo pipefail

VM_REF="${1:?Usage: vm-release.sh <NAME_OR_VMID>}"

# Validate required environment variables
if [ -z "${VM_IP:-}" ] || [ -z "${SSH_OPTS:-}" ]; then
  echo "[vm-release] WARNING: Missing VM_IP or SSH_OPTS, skipping release"
  exit 0
fi

echo "[vm-release] Releasing VM ${VM_REF} (removing /usebyjob)..."
ssh ${SSH_OPTS} root@"${VM_IP}" "rm -f /usebyjob" 2>/dev/null || true
echo "[vm-release] VM ${VM_REF} released"
