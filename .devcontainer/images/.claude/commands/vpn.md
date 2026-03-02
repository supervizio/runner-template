---
name: vpn
description: |
  Multi-protocol VPN management with 1Password multi-profile support.
  Supports OpenVPN, WireGuard, IPsec/IKEv2, and PPTP.
  List/connect/disconnect VPN profiles from vault "VPN".
  Use when: managing VPN connections, listing available profiles.
allowed-tools:
  - "Bash(op:*)"
  - "Bash(sudo:*)"
  - "Bash(pgrep:*)"
  - "Bash(ip:*)"
  - "Bash(wg:*)"
  - "Bash(ipsec:*)"
  - "Bash(tail:*)"
  - "Bash(wc:*)"
  - "Bash(jq:*)"
  - "Read(**/*)"
  - "Edit(**/.env)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "Grep(**/*)"
  - "AskUserQuestion(*)"
  - "Task(*)"
---

# /vpn - Multi-Protocol VPN Management (1Password)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

---

## Overview

Interactive VPN management via **1Password CLI** (`op`) with multi-profile and multi-protocol support:

- **Peek** - Verify prerequisites (VPN clients, op CLI, vault access, current state)
- **Execute** - List profiles, connect, disconnect, or show status
- **Synthesize** - Display formatted result

**Backend**: 1Password vault "VPN" (configurable via `VPN_VAULT`)
**Protocols**: OpenVPN, WireGuard, IPsec/IKEv2, PPTP
**Convention**: Each profile = items with same title in the vault:
  - `PROFILE` (DOCUMENT) = config file (.ovpn, .conf, etc.)
  - `PROFILE` (LOGIN) = credentials (optional, not needed for WireGuard)
  - Tags on DOCUMENT determine protocol: `openvpn` (default), `wireguard`, `ipsec`, `pptp`

---

## Arguments

| Pattern | Action |
|---------|--------|
| `--list` | List available VPN profiles from 1Password vault (all protocols) |
| `--connect <profile>` | Connect to a named VPN profile |
| `--connect` (no arg) | Connect using default profile from `VPN_CONFIG_REF` in `.env` |
| `--disconnect` | Stop VPN and clean up credentials |
| `--status` | Show connection state, interface IP, and recent logs |
| `--help` | Show usage |

### Examples

```bash
# List available VPN profiles (all protocols)
/vpn --list

# Connect to a specific profile
/vpn --connect HOME

# Connect using default from .env
/vpn --connect

# Check VPN status
/vpn --status

# Disconnect
/vpn --disconnect
```

---

## --help

```
═══════════════════════════════════════════════════════════════════
  /vpn - Multi-Protocol VPN Management (1Password)
═══════════════════════════════════════════════════════════════════

Usage: /vpn <action> [options]

Actions:
  --list                  List VPN profiles in vault (all protocols)
  --connect [profile]     Connect to VPN (default: from .env)
  --disconnect            Stop VPN and clean up
  --status                Show connection state

Options:
  --help                  Show this help

Supported Protocols:
  OpenVPN    (.ovpn)   - tag: "openvpn" (or no tag = default)
  WireGuard  (.conf)   - tag: "wireguard" (no credentials needed)
  IPsec/IKEv2          - tag: "ipsec" (StrongSwan)
  PPTP                 - tag: "pptp"

1Password Convention (vault "VPN"):
  Each profile = items with same title:
    "HOME" (DOCUMENT) -> config file (tagged with protocol)
    "HOME" (LOGIN)    -> username + password (optional)

  Configure default: VPN_CONFIG_REF=op://VPN/HOME
  in .devcontainer/.env

Examples:
  /vpn --list
  /vpn --connect HOME
  /vpn --connect
  /vpn --status
  /vpn --disconnect

═══════════════════════════════════════════════════════════════════
```

---

## Phase 1.0: Peek (MANDATORY)

**Verify prerequisites BEFORE any action:**

```yaml
peek_workflow:
  1_check_vpn_clients:
    action: "Check installed VPN clients"
    commands:
      - "command -v openvpn"
      - "command -v wg"
      - "command -v ipsec"
      - "command -v pptp"
    note: "At least one must be present. List all found."

  2_check_op:
    action: "Verify op CLI is available"
    command: "command -v op"
    on_failure: |
      ABORT with message:
      "op CLI not found. Install 1Password CLI or run inside DevContainer."

  3_check_token:
    action: "Verify OP_SERVICE_ACCOUNT_TOKEN"
    command: "test -n \"$OP_SERVICE_ACCOUNT_TOKEN\""
    on_failure: |
      ABORT with message:
      "OP_SERVICE_ACCOUNT_TOKEN not set. Configure in .devcontainer/.env"

  4_check_vault:
    action: "Verify access to VPN vault"
    command: "op vault get \"${VPN_VAULT:-VPN}\" --format json 2>/dev/null | jq -r '.id'"
    store: "VAULT_NAME"
    on_failure: |
      ABORT with message:
      "Cannot access vault '${VPN_VAULT:-VPN}'. Check 1Password configuration."

  5_check_state:
    action: "Check if any VPN is already connected"
    commands:
      - "pgrep -x openvpn"
      - "ip link show wg0 2>/dev/null"
      - "pgrep -x charon"
      - "pgrep -x pppd"
    store: "VPN_RUNNING (type + boolean)"
    note: "Informational - does not abort"
```

**Output Phase 1:**

```
═══════════════════════════════════════════════════════════════════
  /vpn - Connection Check
═══════════════════════════════════════════════════════════════════

  VPN Clients:
    OpenVPN    : /usr/sbin/openvpn ✓
    WireGuard  : /usr/bin/wg ✓
    StrongSwan : /usr/sbin/ipsec ✓
    PPTP       : /usr/sbin/pptp ✓

  1Password CLI: op ✓
  Service Token: OP_SERVICE_ACCOUNT_TOKEN ✓ (set)
  Vault Access : VPN ✓
  VPN State    : DISCONNECTED

═══════════════════════════════════════════════════════════════════
```

---

## Phase 1.5: OS Agent Dispatch (Parallel)

**After Peek completes, dispatch to the appropriate OS specialist for client validation:**

```yaml
os_dispatch:
  trigger: "After Phase 1.0 Peek completes"

  1_detect_os:
    linux:
      command: "cat /etc/os-release 2>/dev/null | grep -E '^ID=' | cut -d= -f2 | tr -d '\"'"
      routing_table:
        debian: os-specialist-debian
        ubuntu: os-specialist-ubuntu
        fedora: os-specialist-fedora
        rhel|centos|rocky|almalinux: os-specialist-rhel
        arch|manjaro: os-specialist-arch
        alpine: os-specialist-alpine
        opensuse-leap|opensuse-tumbleweed: os-specialist-opensuse
        void: os-specialist-void
        devuan: os-specialist-devuan
        artix: os-specialist-artix
        gentoo: os-specialist-gentoo
        nixos: os-specialist-nixos
        kali: os-specialist-kali
        slackware: os-specialist-slackware
    bsd:
      command: "uname -s"
      routing_table:
        FreeBSD: os-specialist-freebsd
        OpenBSD: os-specialist-openbsd
        NetBSD: os-specialist-netbsd
        DragonFly: os-specialist-dragonflybsd
    darwin: os-specialist-macos
    fallback: "devops-executor-linux (generic)"

  2_dispatch:
    mode: "single Task call"
    prompt: |
      Validate VPN client installation and configuration for {protocol}:
      - Is {vpn_client} installed? If not, provide install command.
      - Check firewall rules for VPN traffic (UDP 1194, UDP 51820, UDP 500/4500).
      - Verify TUN/TAP device availability.
      - Check DNS resolver configuration.
      Return condensed JSON with install commands and config recommendations.

  3_use_result:
    action: "Integrate OS-specific commands into connect/disconnect workflows"
    example: |
      # Agent returns:
      {"commands": [{"description": "Install WireGuard", "command": "apk add wireguard-tools", "sudo": true}]}
      # Skill uses the exact command for the detected OS
```

---

## Action: --list

**List available VPN profiles from 1Password vault (all protocols):**

```yaml
list_workflow:
  1_list_documents:
    action: "List DOCUMENT items in VPN vault with tags"
    command: |
      vault="${VPN_VAULT:-VPN}"
      op item list --vault "$vault" --categories DOCUMENT --format json \
        | jq -r '.[] | {title: .title, tags: (.tags // [])}'
    store: "PROFILES with tags"

  2_detect_protocol:
    action: "Determine protocol from tags"
    logic: |
      for each profile:
        tags = item.tags
        if "wireguard" in tags: protocol = "wireguard"
        elif "ipsec" in tags: protocol = "ipsec"
        elif "pptp" in tags: protocol = "pptp"
        else: protocol = "openvpn"  # default

  3_list_logins:
    action: "Cross-reference LOGIN items"
    command: |
      op item list --vault "$vault" --categories LOGIN --format json \
        | jq -r '.[].title'
    store: "LOGIN_TITLES"

  4_display:
    action: "Display table with protocol, config, and credentials"
```

**Output --list:**

```
═══════════════════════════════════════════════════════════════════
  /vpn --list
═══════════════════════════════════════════════════════════════════

  Vault: VPN

  | Profile    | Protocol  | Config     | Credentials |
  |------------|-----------|------------|-------------|
  | HOME       | openvpn   | ✓ DOCUMENT | ✓ LOGIN     |
  | OFFICE     | wireguard | ✓ DOCUMENT | N/A         |
  | DATACENTER | ipsec     | ✓ DOCUMENT | ✓ LOGIN     |

  Total: 3 profiles

  Default: HOME (from VPN_CONFIG_REF)

═══════════════════════════════════════════════════════════════════
```

---

## Action: --connect

**Connect to a VPN profile (protocol-aware):**

```yaml
connect_workflow:
  1_auto_disconnect:
    action: "Disconnect any active VPN first (only one VPN at a time)"
    rule: "ONLY ONE VPN CONNECTION ALLOWED AT ANY TIME"
    logic: |
      If any VPN is active (openvpn, wg0, charon, pppd):
        1. Inform user: "Disconnecting active VPN (only one allowed)..."
        2. Run disconnect for the detected protocol
        3. Clean up credentials
        4. Proceed with new connection
    commands:
      openvpn_active: "pgrep -x openvpn → sudo killall openvpn"
      wireguard_active: "ip link show wg0 → sudo wg-quick down wg0"
      ipsec_active: "pgrep -x charon → sudo ipsec stop"
      pptp_active: "pgrep -x pppd → sudo killall pppd"
    cleanup: "rm -f /tmp/vpn-auth.txt"
    note: "Auto-disconnect is silent and fast. User sees brief info message."

  2_resolve_profile:
    action: "Determine profile name"
    logic: |
      if argument provided:
        profile = argument
      else:
        ref="${VPN_CONFIG_REF:-${OPENVPN_CONFIG_REF:-}}"
        if [ -z "$ref" ]; then
          ABORT "No profile specified and VPN_CONFIG_REF not set.
                 Use: /vpn --connect <profile>
                 Or set VPN_CONFIG_REF=op://VPN/PROFILE in .devcontainer/.env"
        fi
        ref="${ref#op://}"
        profile=$(echo "$ref" | cut -d'/' -f2)

  3_detect_protocol:
    action: "Determine protocol from 1Password item tags"
    command: |
      vault="${VPN_VAULT:-VPN}"
      doc_item=$(op item list --vault "$vault" --categories DOCUMENT --format json \
        | jq -r --arg t "$profile" '.[] | select(.title==$t)')
      doc_uuid=$(echo "$doc_item" | jq -r '.id')
      # Detect protocol from tags (default: openvpn) - zsh-compatible
      protocol="openvpn"
      echo "$doc_item" | jq -r '.tags // [] | .[]' | while IFS= read -r tag; do
        case "$tag" in
          wireguard|ipsec|pptp) protocol="$tag"; break ;;
        esac
      done

  4_resolve_credentials:
    action: "Get LOGIN item (if applicable)"
    condition: "protocol != wireguard"
    command: |
      login_uuid=$(op item list --vault "$vault" --categories LOGIN --format json \
        | jq -r --arg t "$profile" '.[] | select(.title==$t) | .id')
      if [ -n "$login_uuid" ]; then
        vpn_user=$(op read "op://$vault/$login_uuid/username")
        vpn_pass=$(op read "op://$vault/$login_uuid/password")
        printf '%s\n%s\n' "$vpn_user" "$vpn_pass" > /tmp/vpn-auth.txt
        chmod 600 /tmp/vpn-auth.txt
      fi
    note: "NEVER log passwords"

  5_download_config:
    action: "Download config by UUID"
    command: |
      case "$protocol" in
        openvpn)
          mkdir -p ~/.config/openvpn
          op document get "$doc_uuid" --vault "$vault" > ~/.config/openvpn/client.ovpn
          chmod 600 ~/.config/openvpn/client.ovpn
          ;;
        wireguard)
          mkdir -p ~/.config/wireguard
          op document get "$doc_uuid" --vault "$vault" > ~/.config/wireguard/wg0.conf
          chmod 600 ~/.config/wireguard/wg0.conf
          ;;
        ipsec)
          mkdir -p ~/.config/strongswan
          op document get "$doc_uuid" --vault "$vault" > ~/.config/strongswan/ipsec.conf
          chmod 600 ~/.config/strongswan/ipsec.conf
          ;;
        pptp)
          mkdir -p ~/.config/pptp
          op document get "$doc_uuid" --vault "$vault" > ~/.config/pptp/tunnel.conf
          chmod 600 ~/.config/pptp/tunnel.conf
          ;;
      esac

  6_connect:
    action: "Start VPN (protocol-specific)"
    commands:
      openvpn: |
        sudo openvpn \
          --config ~/.config/openvpn/client.ovpn \
          --daemon ovpn-client \
          --log /tmp/openvpn.log \
          --script-security 2 \
          --up /etc/openvpn/update-dns \
          --down /etc/openvpn/update-dns \
          --keepalive 10 60 \
          --connect-retry 5 \
          --connect-retry-max 0 \
          --persist-tun \
          --persist-key \
          --resolv-retry infinite \
          --auth-user-pass /tmp/vpn-auth.txt
      wireguard: |
        sudo wg-quick up ~/.config/wireguard/wg0.conf
      ipsec: |
        sudo cp ~/.config/strongswan/ipsec.conf /etc/ipsec.d/profile.conf
        [ -f /tmp/vpn-auth.txt ] && sudo cp /tmp/vpn-auth.txt /etc/ipsec.d/profile.secrets
        sudo ipsec restart
        # Extract connection name from config
        conn_name=$(grep -oP '(?<=^conn )\S+' ~/.config/strongswan/ipsec.conf | head -1)
        sudo ipsec up "$conn_name"
      pptp: |
        # Extract server from config and connect
        sudo pppd call tunnel nodetach &
        # Or: sudo pptp <server> file ~/.config/pptp/tunnel.conf

  7_verify:
    action: "Wait for interface (protocol-specific)"
    commands:
      openvpn: "Wait for tun0 (up to 15s)"
      wireguard: "Wait for wg0 (up to 10s)"
      ipsec: "Wait for ipsec status ESTABLISHED (up to 15s)"
      pptp: "Wait for ppp0 (up to 15s)"
    timeout: "15 seconds"
```

**Output --connect (OpenVPN):**

```
═══════════════════════════════════════════════════════════════════
  /vpn --connect HOME
═══════════════════════════════════════════════════════════════════

  Profile  : HOME
  Protocol : OpenVPN
  Vault    : VPN
  Config   : ✓ Downloaded (.ovpn)
  Creds    : ✓ Resolved (username + password)
  Status   : CONNECTED
  Interface: tun0 (10.8.0.2)

═══════════════════════════════════════════════════════════════════
```

**Output --connect (WireGuard):**

```
═══════════════════════════════════════════════════════════════════
  /vpn --connect OFFICE
═══════════════════════════════════════════════════════════════════

  Profile  : OFFICE
  Protocol : WireGuard
  Vault    : VPN
  Config   : ✓ Downloaded (.conf)
  Creds    : N/A (keys in config)
  Status   : CONNECTED
  Interface: wg0 (10.0.0.2)

═══════════════════════════════════════════════════════════════════
```

---

## Action: --disconnect

**Stop VPN and clean up (auto-detects active protocol):**

```yaml
disconnect_workflow:
  1_detect_running:
    action: "Detect which VPN protocol is active"
    checks:
      - "pgrep -x openvpn → OpenVPN"
      - "ip link show wg0 → WireGuard"
      - "pgrep -x charon → IPsec"
      - "pgrep -x pppd → PPTP"
    on_none: |
      INFO "No VPN is running. Nothing to disconnect."
      return

  2_stop:
    action: "Stop detected VPN"
    commands:
      openvpn: "sudo killall openvpn 2>/dev/null || true"
      wireguard: "sudo wg-quick down wg0 2>/dev/null || sudo wg-quick down ~/.config/wireguard/wg0.conf 2>/dev/null || true"
      ipsec: |
        conn_name=$(grep -oP '(?<=^conn )\S+' /etc/ipsec.d/profile.conf 2>/dev/null | head -1)
        [ -n "$conn_name" ] && sudo ipsec down "$conn_name" 2>/dev/null || true
        sudo ipsec stop 2>/dev/null || true
      pptp: "sudo killall pppd 2>/dev/null || true"

  3_cleanup:
    action: "Remove credentials and temp files"
    command: |
      rm -f /tmp/vpn-auth.txt
      sudo rm -f /etc/ipsec.d/profile.conf /etc/ipsec.d/profile.secrets 2>/dev/null || true
    note: "Ephemeral credentials cleaned up"

  4_verify:
    action: "Confirm disconnection"
    command: |
      ! pgrep -x openvpn && ! ip link show wg0 2>/dev/null && \
      ! pgrep -x charon && ! pgrep -x pppd
```

**Output --disconnect:**

```
═══════════════════════════════════════════════════════════════════
  /vpn --disconnect
═══════════════════════════════════════════════════════════════════

  Protocol : OpenVPN (detected)
  Action   : Stopped openvpn daemon
  Cleanup  : /tmp/vpn-auth.txt removed
  Status   : DISCONNECTED

═══════════════════════════════════════════════════════════════════
```

---

## Action: --status

**Check current VPN state (all protocols):**

```yaml
status_workflow:
  1_check_openvpn:
    action: "Check OpenVPN"
    commands:
      - "pgrep -x openvpn → PID"
      - "ip addr show tun0 → IP"
      - "sudo tail -5 /tmp/openvpn.log → logs"

  2_check_wireguard:
    action: "Check WireGuard"
    commands:
      - "ip link show wg0 → interface"
      - "sudo wg show wg0 → stats"

  3_check_ipsec:
    action: "Check IPsec"
    commands:
      - "sudo ipsec status → connections"

  4_check_pptp:
    action: "Check PPTP"
    commands:
      - "pgrep -x pppd → PID"
      - "ip addr show ppp0 → IP"
```

**Output --status (connected, OpenVPN):**

```
═══════════════════════════════════════════════════════════════════
  /vpn --status
═══════════════════════════════════════════════════════════════════

  Protocol : OpenVPN
  Process  : openvpn (PID: 1234) ✓
  Interface: tun0 (10.8.0.2) ✓
  Uptime   : Running

  Recent logs:
    [timestamp] Initialization Sequence Completed
    [timestamp] Data Channel: cipher 'AES-256-GCM'

═══════════════════════════════════════════════════════════════════
```

**Output --status (disconnected):**

```
═══════════════════════════════════════════════════════════════════
  /vpn --status
═══════════════════════════════════════════════════════════════════

  OpenVPN  : not running ✗
  WireGuard: wg0 not found ✗
  IPsec    : no connections ✗
  PPTP     : not running ✗
  Status   : DISCONNECTED

  Hint: Use /vpn --connect to start VPN

═══════════════════════════════════════════════════════════════════
```

---

## SAFEGUARDS (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Multiple VPNs active simultaneously | BLOCKED | Auto-disconnect current before connecting new |
| Log passwords or credentials | FORBIDDEN | Security |
| Commit config files | BLOCKED | Protected by `.gitignore` |
| Store credentials outside `/tmp` | FORBIDDEN | Ephemeral only |
| Skip Phase 1 (Peek) | FORBIDDEN | Must verify prerequisites |
| Connect without confirming profile | FORBIDDEN | Must resolve and display profile name |
| Run without `OP_SERVICE_ACCOUNT_TOKEN` | BLOCKED | Auth required for 1Password |
| Use PPTP without warning | WARNING | PPTP is insecure, recommend alternatives |
