#!/usr/bin/env bash
# vm-acquire.sh - Acquire a Proxmox VM with lock mechanism ("flambeau")
#
# Usage: vm-acquire.sh <NAME_OR_VMID> <JOB_ID>
#
# The first argument can be:
#   - A VM name (e.g., "freebsd", "debian-systemd") — resolved to VMID via Proxmox API
#   - A numeric VMID (e.g., "113") — used directly (backward compatible)
#
# Required env vars:
#   PROXMOX_API_URL  - Proxmox API base URL
#   PVE_AUTH         - PVEAPIToken auth header value
#   NODE             - Proxmox node name
#   SSH_OPTS         - SSH options string
#
# Output (GITHUB_OUTPUT):
#   VM_IP            - IP address of the acquired VM
#   VMID             - Resolved VMID (useful when name was provided)
#
# The script:
#   1. Resolves VM name to VMID via Proxmox API (if not already numeric)
#   2. Checks if VM is running and locked by another job (via /usebyjob on VM)
#   3. Retries every 60s if locked (max 15 retries = 15 min)
#   4. Starts the VM if stopped, waits for SSH
#   5. Creates /usebyjob lock file with job ID
#
# Note: No snapshot rollback here. VM cleanup (vm-cleanup job) handles
# resetting all VMs to "base" snapshot at the end of the pipeline.
set -euo pipefail

INPUT="${1:?Usage: vm-acquire.sh <NAME_OR_VMID> <JOB_ID>}"
JOB_ID="${2:?Usage: vm-acquire.sh <NAME_OR_VMID> <JOB_ID>}"
MAX_RETRIES=15
RETRY_INTERVAL=60
IP_FAIL_THRESHOLD=3  # After N consecutive IP detection failures, reset the VM

# Log to stderr so messages are visible even inside $() command substitutions
log() { echo "[vm-acquire] $*" >&2; }

# Validate required environment variables
for var in PROXMOX_API_URL PVE_AUTH NODE SSH_OPTS; do
  if [ -z "${!var}" ]; then
    log "ERROR: Required env var $var is not set"
    exit 1
  fi
done

# Validate PVE_AUTH is not just "PVEAPIToken==" (empty secrets)
if [ "$PVE_AUTH" = "PVEAPIToken==" ] || [[ "$PVE_AUTH" == *"==" && ! "$PVE_AUTH" == *"!"* ]]; then
  log "ERROR: PVE_AUTH appears to contain empty secrets (got: '$PVE_AUTH')"
  log "Configure CI_RUNNER_API_TOKEN_ID and CI_RUNNER_API_TOKEN_SECRET in GitHub repository secrets"
  exit 1
fi

# Proxmox API helper (curl with auth, timeout, insecure TLS)
pve_api() {
  curl -sf -k --max-time 30 -H "Authorization: ${PVE_AUTH}" "$@"
}

# Resolve VM name to VMID via Proxmox API
# If input is already numeric, return as-is (backward compatible)
resolve_vmid() {
  local input="$1"

  # If numeric, use directly
  if [[ "$input" =~ ^[0-9]+$ ]]; then
    echo "$input"
    return 0
  fi

  # Resolve name → VMID via Proxmox API
  local vmid
  vmid=$(pve_api "${PROXMOX_API_URL}/nodes/${NODE}/qemu" 2>/dev/null \
    | jq -r ".data[] | select(.name == \"${input}\") | .vmid" 2>/dev/null \
    | head -1) || true

  if [ -n "$vmid" ] && [ "$vmid" != "null" ]; then
    log "Resolved '${input}' → VMID ${vmid}"
    echo "$vmid"
    return 0
  fi

  log "ERROR: Cannot resolve VM name '${input}' to VMID"
  log "Available VMs:"
  pve_api "${PROXMOX_API_URL}/nodes/${NODE}/qemu" 2>/dev/null \
    | jq -r '.data[] | "  \(.vmid) \(.name) (\(.status))"' 2>/dev/null || true
  return 1
}

# Detect VM IP via neighbor table, QEMU guest agent, or DHCP lease
# Returns: IP address on stdout, logs on stderr
# Methods ordered by speed: neighbor scan (~5s) > guest agent (~15s) > DHCP (~20s)
detect_ip() {
  local vmid="$1"
  local vm_ip=""

  # Get MAC address (needed by neighbor scan and DHCP)
  local mac=""
  mac=$(pve_api "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${vmid}/config" 2>/dev/null \
    | jq -r '.data.net0 // empty' 2>/dev/null \
    | grep -oP '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}' 2>/dev/null) || true

  # Method 1: Neighbor table lookup (fastest - ~5s)
  # Runners are on the same L2 network as VMs, so neighbor table has entries
  if [ -n "$mac" ]; then
    local mac_lower
    mac_lower=$(echo "$mac" | tr '[:upper:]' '[:lower:]')

    # Quick check without ping sweep (neighbor table may already have entry)
    if command -v ip >/dev/null 2>&1; then
      vm_ip=$(ip neigh 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep "${mac_lower}" \
        | grep -oP '192\.168\.100\.\d+' | head -1) || true
    fi
    if [ -z "$vm_ip" ] && command -v arp >/dev/null 2>&1; then
      vm_ip=$(arp -an 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep "${mac_lower}" \
        | grep -oP '\(([0-9.]+)\)' | tr -d '()' | head -1) || true
    fi

    if [ -z "$vm_ip" ]; then
      # Ping sweep to populate neighbor table (background, fast)
      log "Neighbor scan: ping sweep..."
      for octet in $(seq 1 254); do
        ping -c 1 -W 1 "192.168.100.${octet}" >/dev/null 2>&1 &
      done
      wait 2>/dev/null
      sleep 1  # Allow neighbor table to settle

      if command -v ip >/dev/null 2>&1; then
        vm_ip=$(ip neigh 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep "${mac_lower}" \
          | grep -oP '192\.168\.100\.\d+' | head -1) || true
      fi
      if [ -z "$vm_ip" ] && command -v arp >/dev/null 2>&1; then
        vm_ip=$(arp -an 2>/dev/null | tr '[:upper:]' '[:lower:]' | grep "${mac_lower}" \
          | grep -oP '\(([0-9.]+)\)' | tr -d '()' | head -1) || true
      fi
    fi

    if [ -n "$vm_ip" ]; then
      log "VM IP (neighbor scan): $vm_ip"
      echo "$vm_ip"
      return 0
    fi
  fi

  # Method 2: QEMU guest agent (3 quick attempts)
  for i in $(seq 1 3); do
    local result=""
    result=$(pve_api \
      "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${vmid}/agent/network-get-interfaces" 2>/dev/null) && {
      vm_ip=$(echo "$result" | jq -r \
        '.data.result[] | select(.name != "lo") | .["ip-addresses"][]? | select(.["ip-address-type"] == "ipv4") | .["ip-address"]' \
        2>/dev/null | head -1) || true
      if [ -n "$vm_ip" ] && [ "$vm_ip" != "null" ]; then
        log "VM IP (guest agent): $vm_ip"
        echo "$vm_ip"
        return 0
      fi
    }
    log "Guest agent attempt $i/3..."
    sleep 2
  done

  if [ -z "$mac" ]; then
    log "Could not detect MAC address from Proxmox API"
    log "ERROR: Could not detect VM IP"
    return 1
  fi

  # Method 3: DHCP lease via SSH to Proxmox host (2 attempts)
  log "Trying DHCP lease detection..."
  for i in $(seq 1 2); do
    vm_ip=$(ssh ${SSH_OPTS} root@192.168.100.1 \
      "grep -i '${mac}' /var/lib/misc/dnsmasq.leases 2>/dev/null | awk '{print \$3}'" 2>/dev/null) || true
    if [ -n "$vm_ip" ]; then
      log "VM IP (DHCP lease): $vm_ip"
      echo "$vm_ip"
      return 0
    fi
    log "DHCP attempt $i/2..."
    sleep 2
  done

  # Method 4: nmap scan as last resort
  if command -v nmap >/dev/null 2>&1; then
    log "Trying nmap scan..."
    local mac_lower_nmap
    mac_lower_nmap=$(echo "$mac" | tr '[:upper:]' '[:lower:]')
    vm_ip=$(nmap -sn 192.168.100.0/24 2>/dev/null \
      | grep -B2 -i "${mac_lower_nmap}" | grep -oP '192\.168\.100\.\d+' | head -1) || true
    if [ -n "$vm_ip" ]; then
      log "VM IP (nmap): $vm_ip"
      echo "$vm_ip"
      return 0
    fi
  fi

  log "ERROR: Could not detect VM IP (tried: neighbor, guest agent, DHCP, nmap)"
  return 1
}

# Wait for SSH to be ready
wait_ssh() {
  local ip="$1"
  log "Waiting for SSH on ${ip}..."
  for i in $(seq 1 30); do
    if ssh ${SSH_OPTS} root@"${ip}" "echo ready" 2>/dev/null; then
      log "SSH ready after $((i * 5)) seconds"
      return 0
    fi
    log "SSH attempt $i/30..."
    sleep 5
  done
  log "ERROR: SSH not ready after 150 seconds"
  return 1
}

# Check VM status via Proxmox API
vm_status() {
  pve_api "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${VMID}/status/current" 2>/dev/null \
    | jq -r '.data.status' 2>/dev/null || echo "unknown"
}

# Resolve input to VMID (supports both name and numeric VMID)
VMID=$(resolve_vmid "$INPUT") || exit 1

# Main acquisition loop
ip_fail_count=0
for attempt in $(seq 1 "$MAX_RETRIES"); do
  vm_st=$(vm_status)
  log "Attempt $attempt/$MAX_RETRIES: VM ${VMID} status=$vm_st"

  # Track IP resolved during lock check to avoid double detection
  resolved_ip=""

  if [ "$vm_st" = "running" ]; then
    # VM is running - check if locked
    resolved_ip=$(detect_ip "$VMID") || true
    if [ -n "$resolved_ip" ]; then
      ip_fail_count=0  # Reset counter on successful IP detection
      lock_owner=$(ssh ${SSH_OPTS} root@"$resolved_ip" "cat /usebyjob 2>/dev/null" || true)
      if [ -n "$lock_owner" ] && [ "$lock_owner" != "$JOB_ID" ]; then
        log "VM ${VMID} locked by '$lock_owner'"

        # Extract run ID from lock format: {run_id}_{job_name}
        lock_run_id=$(echo "$lock_owner" | cut -d_ -f1)

        # Check if locking run is still active via GitHub API
        if [ -n "$lock_run_id" ] && [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
          run_status=$(curl -sf --max-time 10 \
            -H "Authorization: Bearer ${GITHUB_TOKEN}" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runs/${lock_run_id}" \
            2>/dev/null | jq -r '.status // "unknown"') || run_status="api_error"

          if [ "$run_status" != "in_progress" ] && [ "$run_status" != "queued" ] \
             && [ "$run_status" != "api_error" ] && [ "$run_status" != "unknown" ]; then
            log "STALE LOCK: run $lock_run_id status='$run_status', breaking lock"
            ssh ${SSH_OPTS} root@"$resolved_ip" "rm -f /usebyjob" || true
            sleep 2
            continue
          fi

          if [ "$run_status" = "api_error" ] || [ "$run_status" = "unknown" ]; then
            log "Cannot verify lock (API error), falling back to wait"
          else
            log "Run $lock_run_id still active ($run_status)"
          fi
        fi

        log "Waiting ${RETRY_INTERVAL}s for lock release..."
        sleep "$RETRY_INTERVAL"
        continue
      fi
      log "VM running and unlocked, acquiring..."
    else
      ip_fail_count=$((ip_fail_count + 1))
      log "VM running but cannot detect IP (fail $ip_fail_count/$IP_FAIL_THRESHOLD)"
      if [ "$ip_fail_count" -ge "$IP_FAIL_THRESHOLD" ]; then
        log "VM appears stuck (running but unreachable). Resetting..."
        pve_api -X POST "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${VMID}/status/stop" > /dev/null 2>&1 || true
        sleep 5
        pve_api -X POST "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${VMID}/snapshot/base/rollback" > /dev/null 2>&1 || true
        sleep 2
        log "VM reset to base snapshot, will restart on next attempt"
        ip_fail_count=0
      fi
    fi
  fi

  # Start VM if not running
  if [ "$vm_st" != "running" ]; then
    log "Starting VM ${VMID}..."
    pve_api -X POST "${PROXMOX_API_URL}/nodes/${NODE}/qemu/${VMID}/status/start" > /dev/null 2>&1 || true
    log "Waiting 15s for VM boot..."
    sleep 15
  fi

  # Resolve IP: reuse from lock check if available, otherwise detect fresh
  if [ -n "$resolved_ip" ]; then
    VM_IP="$resolved_ip"
    log "Reusing resolved IP: $VM_IP"
  else
    VM_IP=$(detect_ip "$VMID") || {
      log "Failed to detect IP on attempt $attempt/$MAX_RETRIES"
      if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        log "Retrying in ${RETRY_INTERVAL}s..."
        sleep "$RETRY_INTERVAL"
      fi
      continue
    }
  fi

  # Wait for SSH
  if ! wait_ssh "$VM_IP"; then
    log "SSH not available on attempt $attempt/$MAX_RETRIES"
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
      log "Retrying in ${RETRY_INTERVAL}s..."
      sleep "$RETRY_INTERVAL"
    fi
    continue
  fi

  # Create lock file (flambeau)
  ssh ${SSH_OPTS} root@"$VM_IP" "echo '${JOB_ID}' > /usebyjob"
  log "VM ${VMID} acquired by '${JOB_ID}' at ${VM_IP}"

  # Export outputs
  echo "VM_IP=${VM_IP}" >> "$GITHUB_OUTPUT"
  echo "VM_IP=${VM_IP}" >> "$GITHUB_ENV"
  echo "VMID=${VMID}" >> "$GITHUB_OUTPUT"
  echo "VMID=${VMID}" >> "$GITHUB_ENV"
  exit 0
done

log "ERROR: Failed to acquire VM ${VMID} after ${MAX_RETRIES} retries (${MAX_RETRIES} minutes)"
exit 1
