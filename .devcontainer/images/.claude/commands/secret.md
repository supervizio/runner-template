---
name: secret
description: |
  Secure secret management with 1Password CLI (op).
  Share secrets between projects via Vault-like path structure.
  Auto-detects project path from git remote origin.
  Use when: storing, retrieving, or listing project secrets.
allowed-tools:
  - "Bash(op:*)"
  - "Bash(git:*)"
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "Grep(**/*)"
  - "AskUserQuestion(*)"
---

# /secret - Secure Secret Management (1Password + Vault-like Paths)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Fallback to Grep ONLY for exact string matches or regex patterns.

---

## Overview

Secure secret management via **1Password CLI** (`op`) with a path hierarchy inspired by HashiCorp Vault:

- **Peek** - Verify 1Password connectivity + resolve project path
- **Execute** - Call `op` CLI for push/get/list
- **Synthesize** - Display formatted result

**Backend:** 1Password (via `OP_SERVICE_ACCOUNT_TOKEN`)
**CLI:** `op` (installed in the devcontainer)
**No MCP:** 1Password has no official MCP (deliberate policy)

---

## Arguments

| Pattern | Action |
|---------|--------|
| `--push <key>=<value>` | Write a secret to 1Password |
| `--get <key>` | Read a secret from 1Password |
| `--list` | List project secrets |
| `--path <path>` | Override the project path (optional) |
| `--help` | Show help |

### Examples

```bash
# Push a secret (auto path = kodflow/devcontainer-template)
/secret --push DB_PASSWORD=mypass

# Push to a different path (cross-project)
/secret --push SHARED_TOKEN=abc123 --path kodflow/shared-infra

# Get a secret
/secret --get DB_PASSWORD

# Get from another path
/secret --get API_KEY --path kodflow/other-project

# List secrets for the current project
/secret --list

# List secrets from another path
/secret --list --path kodflow/shared-infra
```

---

## --help

```
═══════════════════════════════════════════════════════════════
  /secret - Secure Secret Management (1Password)
═══════════════════════════════════════════════════════════════

Usage: /secret <action> [options]

Actions:
  --push <key>=<value>    Store a secret in 1Password
  --get <key>             Retrieve a secret from 1Password
  --list                  List secrets for current project

Options:
  --path <org/repo>       Override project path (default: auto)
  --help                  Show this help

Path Convention (Vault-like):
  Items are named: <org>/<repo>/<key>
  Default path is auto-detected from git remote origin.
  Example: kodflow/devcontainer-template/DB_PASSWORD

  Without --path: scoped to current project ONLY
  With --path: access any project's secrets

Backend:
  1Password CLI (op) with OP_SERVICE_ACCOUNT_TOKEN
  Items stored as API_CREDENTIAL in configured vault
  Field: "credential" (matches existing MCP token pattern)

Examples:
  /secret --push DB_PASSWORD=s3cret
  /secret --get DB_PASSWORD
  /secret --list
  /secret --push TOKEN=abc --path kodflow/shared
  /secret --get TOKEN --path kodflow/shared

═══════════════════════════════════════════════════════════════
```

---

## Path Convention (Vault-like)

**Tree structure in 1Password:**

```
<vault>/                              # 1Password vault (default: CI)
├── kodflow/
│   ├── devcontainer-template/        # Current project
│   │   ├── DB_PASSWORD               # Item: kodflow/devcontainer-template/DB_PASSWORD
│   │   ├── API_KEY                   # Item: kodflow/devcontainer-template/API_KEY
│   │   └── JWT_SECRET                # Item: kodflow/devcontainer-template/JWT_SECRET
│   ├── shared-infra/                 # Shared secrets
│   │   ├── AWS_CREDENTIALS            # Item: kodflow/shared-infra/AWS_CREDENTIALS
│   │   └── TF_VAR_db_password       # Item: kodflow/shared-infra/TF_VAR_db_password
│   └── other-project/
│       └── STRIPE_KEY                # Item: kodflow/other-project/STRIPE_KEY
└── mcp-github                        # Existing items (legacy pattern)
```

**Path resolution:**

```bash
# Git remote → path
git remote get-url origin
  → https://github.com/kodflow/devcontainer-template.git
  → path: kodflow/devcontainer-template

# SSH format
  → git@github.com:kodflow/devcontainer-template.git
  → path: kodflow/devcontainer-template

# Token-embedded
  → https://ghp_xxx@github.com/kodflow/devcontainer-template.git
  → path: kodflow/devcontainer-template
```

**Strict rule:** Without `--path`, ALL operations are scoped to the current project path. It is impossible to access a different path without specifying it explicitly.

---

## 1Password Item Format

Each secret is stored as a 1Password item:

```yaml
item:
  title: "<org>/<repo>/<key>"           # Ex: kodflow/devcontainer-template/DB_PASSWORD
  category: "API_CREDENTIAL"            # Same category as mcp-github, mcp-codacy
  vault: "${OP_VAULT_ID}"               # Configured vault (default: CI)
  fields:
    - name: "credential"                # Main field (same pattern as MCP tokens)
      value: "<secret_value>"
    - name: "notesPlain"                # Optional metadata
      value: "Managed by /secret skill"
```

---

## Phase 1.0: Peek (MANDATORY)

**Verify prerequisites BEFORE any operation:**

```yaml
peek_workflow:
  1_check_op:
    action: "Verify that op CLI is available"
    command: "command -v op"
    on_failure: |
      ABORT with message:
      "op CLI not found. Install 1Password CLI or run inside DevContainer."

  2_check_token:
    action: "Verify OP_SERVICE_ACCOUNT_TOKEN"
    command: "test -n \"$OP_SERVICE_ACCOUNT_TOKEN\""
    on_failure: |
      ABORT with message:
      "OP_SERVICE_ACCOUNT_TOKEN not set. Configure in .devcontainer/.env"

  3_check_vault:
    action: "Verify vault access"
    command: "op vault list --format=json 2>/dev/null | jq -r '.[0].id'"
    store: "VAULT_ID"
    on_failure: |
      ABORT with message:
      "Cannot access 1Password vault. Check OP_SERVICE_ACCOUNT_TOKEN."

  4_resolve_path:
    action: "Resolve project path from git remote"
    command: |
      REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
      # Remove .git suffix
      REMOTE_URL="${REMOTE_URL%.git}"
      # Extract org/repo (handles HTTPS, SSH, token-embedded)
      if [[ "$REMOTE_URL" =~ [:/]([^/]+)/([^/]+)$ ]]; then
        PROJECT_PATH="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
      else
        ABORT "Cannot resolve project path from git remote: $REMOTE_URL"
      fi
    store: "PROJECT_PATH"
    override: "--path argument if provided"
```

**Phase 1 Output:**

```
═══════════════════════════════════════════════════════════════
  /secret - Connection Check
═══════════════════════════════════════════════════════════════

  1Password CLI : op v2.32.0 ✓
  Service Token : OP_SERVICE_ACCOUNT_TOKEN ✓ (set)
  Vault Access  : CI (ypahjj334ixtiyjkytu5hij2im) ✓
  Project Path  : kodflow/devcontainer-template ✓

═══════════════════════════════════════════════════════════════
```

---

## Action: --push

**Write a secret to 1Password:**

```yaml
push_workflow:
  1_parse_args:
    action: "Parse key=value"
    validation:
      - "key contains no special characters (a-zA-Z0-9_)"
      - "value is not empty"
      - "exact format: KEY=VALUE (single =)"

  2_build_title:
    action: "Build the item title"
    format: "<PROJECT_PATH>/<key>"
    example: "kodflow/devcontainer-template/DB_PASSWORD"

  3_check_exists:
    action: "Check if the item already exists"
    command: "op item get '<title>' --vault '$VAULT_ID' 2>/dev/null"
    decision:
      exists: "Update (op item edit)"
      not_exists: "Create (op item create)"

  4a_create:
    condition: "Item does not exist"
    command: |
      op item create \
        --category=API_CREDENTIAL \
        --title='<org>/<repo>/<key>' \
        --vault='$VAULT_ID' \
        'credential=<value>'
    note: "The 'credential' field matches the existing MCP token pattern"

  4b_update:
    condition: "Item already exists"
    command: |
      op item edit '<org>/<repo>/<key>' \
        --vault='$VAULT_ID' \
        'credential=<value>'

  5_confirm:
    action: "Verify that the item is properly stored"
    command: "op item get '<title>' --vault '$VAULT_ID' --format=json | jq -r '.title'"
```

**Output --push (new):**

```
═══════════════════════════════════════════════════════════════
  /secret --push
═══════════════════════════════════════════════════════════════

  Path   : kodflow/devcontainer-template
  Key    : DB_PASSWORD
  Action : Created

  Item: kodflow/devcontainer-template/DB_PASSWORD
  Vault: CI
  Field: credential
  Status: ✓ Stored successfully

═══════════════════════════════════════════════════════════════
```

**Output --push (update):**

```
═══════════════════════════════════════════════════════════════
  /secret --push
═══════════════════════════════════════════════════════════════

  Path   : kodflow/devcontainer-template
  Key    : DB_PASSWORD
  Action : Updated (existing item)

  Item: kodflow/devcontainer-template/DB_PASSWORD
  Vault: CI
  Field: credential
  Status: ✓ Updated successfully

═══════════════════════════════════════════════════════════════
```

---

## Action: --get

**Read a secret from 1Password:**

```yaml
get_workflow:
  1_build_title:
    action: "Build the title"
    format: "<PROJECT_PATH>/<key>"

  2_retrieve:
    action: "Retrieve the value"
    command: |
      op item get '<org>/<repo>/<key>' \
        --vault='$VAULT_ID' \
        --fields='credential' \
        --reveal
    fallback_fields: ["credential", "password", "identifiant", "mot de passe"]
    note: "Same fallback logic as get_1password_field in postStart.sh"

  3_display:
    action: "Display the result"
    security: "The value is revealed ONLY ONCE in the output"
```

**Output --get (success):**

```
═══════════════════════════════════════════════════════════════
  /secret --get
═══════════════════════════════════════════════════════════════

  Path  : kodflow/devcontainer-template
  Key   : DB_PASSWORD
  Value : s3cr3t_p4ssw0rd

═══════════════════════════════════════════════════════════════
```

**Output --get (not found):**

```
═══════════════════════════════════════════════════════════════
  /secret --get
═══════════════════════════════════════════════════════════════

  Path  : kodflow/devcontainer-template
  Key   : DB_PASSWORD
  Status: ✗ Not found

  Hint: Use /secret --list to see available secrets
        Use /secret --push DB_PASSWORD=<value> to create it

═══════════════════════════════════════════════════════════════
```

---

## Action: --list

**List secrets for a path:**

```yaml
list_workflow:
  1_list_items:
    action: "List all items in the vault"
    command: |
      op item list \
        --vault='$VAULT_ID' \
        --format=json
    filter: "Filter by PROJECT_PATH/ prefix"

  2_display:
    action: "Display the filtered list"
    format: "Table with title, category, modification date"
    extract_key: "Remove the path/ prefix to display only the key"
```

**Output --list (with secrets):**

```
═══════════════════════════════════════════════════════════════
  /secret --list
═══════════════════════════════════════════════════════════════

  Path: kodflow/devcontainer-template

  | Key             | Category       | Updated            |
  |-----------------|----------------|--------------------|
  | DB_PASSWORD     | API_CREDENTIAL | 2026-02-09 10:30   |
  | API_KEY         | API_CREDENTIAL | 2026-02-08 14:22   |
  | JWT_SECRET      | API_CREDENTIAL | 2026-02-07 09:15   |

  Total: 3 secrets

═══════════════════════════════════════════════════════════════
```

**Output --list (empty):**

```
═══════════════════════════════════════════════════════════════
  /secret --list
═══════════════════════════════════════════════════════════════

  Path: kodflow/devcontainer-template

  No secrets found for this project.

  Hint: Use /secret --push KEY=VALUE to store a secret
        Use /secret --list --path / to see all paths

═══════════════════════════════════════════════════════════════
```

**Output --list --path / (all paths):**

```
═══════════════════════════════════════════════════════════════
  /secret --list --path /
═══════════════════════════════════════════════════════════════

  All secrets (grouped by path):

  kodflow/devcontainer-template/ (3 secrets)
    ├─ DB_PASSWORD
    ├─ API_KEY
    └─ JWT_SECRET

  kodflow/shared-infra/ (2 secrets)
    ├─ AWS_CREDENTIALS
    └─ TF_VAR_db_password

  (legacy items without path)
    ├─ mcp-github
    ├─ mcp-codacy
    └─ mcp-coderabbit

  Total: 8 items (5 with paths, 3 legacy)

═══════════════════════════════════════════════════════════════
```

---

## Cross-Project Secret Sharing

**Use `--path` to share secrets between projects:**

```yaml
sharing_patterns:
  # Share a common infra secret
  push_shared:
    command: '/secret --push AWS_CREDENTIALS=xxx... --path kodflow/shared-infra'
    note: "Accessible by all kodflow projects"

  # Retrieve from another project
  get_cross_project:
    command: '/secret --get STRIPE_KEY --path kodflow/payment-service'
    note: "Unblock a situation by retrieving a secret from another project"

  # Unblock a situation
  unblock_workflow:
    1: '/secret --list --path /'
    2: 'Identify the needed secret and its path'
    3: '/secret --get <key> --path <org>/<repo>'
```

---

## Integration with other skills

### From /init

```yaml
init_integration:
  phase: "Phase 3 (Parallelize)"
  agent: "vault-checker"
  check:
    - "op CLI available"
    - "OP_SERVICE_ACCOUNT_TOKEN set"
    - "Vault accessible"
    - "Number of secrets for the current project"
  report_section: "1Password Secrets"
```

### From /git (pre-commit)

```yaml
git_integration:
  phase: "Phase 3 (Parallelize)"
  agent: "secret-scan"
  check:
    - "Scan git diff --cached for secret patterns"
    - "Patterns: ghp_, glpat-, sk-, pk_, postgres://, mysql://, mongodb://"
    - "If found: WARN (do not block)"
    - "Suggest: /secret --push <key>=<detected_value>"
  behavior: "WARNING only, does NOT block the commit"
```

### From /do

```yaml
do_integration:
  phase: "Phase 0 (before Questions)"
  check:
    - "If the task mentions: secret, token, credential, password, API key"
    - "List available secrets for the project"
    - "Suggest using them or creating new ones"
  behavior: "Informational, helps unblock"
```

### From /infra

```yaml
infra_integration:
  phase: "Before --plan and --apply"
  check:
    - "List project secrets with TF_VAR_ prefix"
    - "Check if Terraform variables reference secrets"
    - "Suggest retrieving from 1Password"
  cross_path: "Allow --path kodflow/shared-infra for shared secrets"
```

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Reveal a secret without explicit --get | **FORBIDDEN** | Security |
| Write a secret to logs | **FORBIDDEN** | Security |
| Push without confirmation if item exists | **FORBIDDEN** | Prevent overwrite |
| Access a different path without --path | **FORBIDDEN** | Strict scope |
| Operate without OP_SERVICE_ACCOUNT_TOKEN | **FORBIDDEN** | Auth required |
| Delete a secret (no --delete) | **FORBIDDEN** | Use 1Password UI |
| Skip Phase 1 (Peek) | **FORBIDDEN** | Connection verification |
