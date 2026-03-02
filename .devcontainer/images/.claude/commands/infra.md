---
name: infra
description: |
  Infrastructure automation with Terraform/Terragrunt.
  Dispatches to DevOps specialist agents for cloud-specific analysis.
allowed-tools:
  - "Read(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Grep(**/*)"
  - "Write(**/*)"
  - "Edit(**/*)"
  - "Bash(*)"
  - "Task(*)"
  - "AskUserQuestion(*)"
---

# /infra - Infrastructure Automation (Terraform/Terragrunt)

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Fetch Terraform provider documentation for resource configuration
- Verify cloud service API references (AWS, GCP, Azure)
- Check HashiCorp tool documentation (Vault, Consul, Nomad)

---

## Overview

Automates Terraform and Terragrunt workflows with RLM patterns:

- **Peek** - Analyze infrastructure state before changes
- **Validate** - Run tflint, tfsec, and terraform validate
- **Plan** - Generate and review execution plan
- **Apply** - Apply changes with safety checks
- **Docs** - Generate documentation with terraform-docs

---

## Arguments

| Pattern | Action |
|---------|--------|
| `--init` | Initialize Terraform/Terragrunt |
| `--plan` | Generate execution plan |
| `--apply` | Apply changes (requires plan) |
| `--destroy` | Destroy infrastructure (with confirmation) |
| `--validate` | Run all validations (tflint, tfsec, validate) |
| `--docs` | Generate documentation |
| `--help` | Show help |

### Options

| Option | Description |
|--------|-------------|
| `--module <path>` | Target specific module |
| `--all` | Run on all modules (Terragrunt run-all) |
| `--auto-approve` | Skip interactive approval |
| `--dry-run` | Show what would be done |

---

## --help

```
═══════════════════════════════════════════════════════════════
  /infra - Infrastructure Automation (Terraform/Terragrunt)
═══════════════════════════════════════════════════════════════

Usage: /infra <action> [options]

Actions:
  --init          Initialize providers and modules
  --plan          Generate and review execution plan
  --apply         Apply infrastructure changes
  --destroy       Destroy infrastructure (with confirmation)
  --validate      Run validation suite (tflint, tfsec, validate)
  --docs          Generate documentation with terraform-docs

Options:
  --module <path> Target specific module directory
  --all           Apply to all modules (Terragrunt run-all)
  --auto-approve  Skip interactive approval (use with caution)
  --dry-run       Show what would be done without executing

RLM Patterns:
  1. Peek      - Check current state
  2. Validate  - Run all checks
  3. Plan      - Generate plan
  4. Apply     - Execute changes
  5. Docs      - Update documentation

Examples:
  /infra --validate                    # Validate all
  /infra --plan --module terraform/k8s # Plan specific module
  /infra --apply --all                 # Apply all with Terragrunt
  /infra --docs                        # Generate all docs

Safety:
  - Never auto-approve destroy
  - Always validate before apply
  - Review plan output before proceeding

═══════════════════════════════════════════════════════════════
```

---

## Workflow

### Phase 1.0: Detection

Detect infrastructure tool and configuration:

```yaml
detection:
  terraform:
    files: ["*.tf", "terraform.tfvars"]
    tool: "terraform"

  terragrunt:
    files: ["terragrunt.hcl"]
    tool: "terragrunt"

  opentofu:
    files: ["*.tf", ".terraform-version"]
    check: "tofu version"
    tool: "tofu"
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  /infra - Infrastructure Detection
═══════════════════════════════════════════════════════════════

  Directory: /workspace/terraform/k8s_driver

  Detected:
    ├─ Tool: Terragrunt (terragrunt.hcl found)
    ├─ Backend: Consul
    └─ Modules: 5 referenced

  Dependencies:
    ├─ ../infrastructure (required)
    └─ ../vault (required)

═══════════════════════════════════════════════════════════════
```

---

### Phase 1.5: Agent Dispatch (Parallel)

**After detection, dispatch to specialized agents in parallel:**

```yaml
agent_dispatch:
  trigger: "After Phase 1.0 detection completes"

  1_detect_providers:
    action: "Grep for provider blocks in *.tf files"
    pattern: 'provider\s+"(aws|google|azurerm|oci|alicloud)"'
    output: [detected_providers]

  2_parallel_dispatch:
    mode: "single message, N Task calls"
    agents:
      infrastructure:
        always: true
        agent: "devops-specialist-infrastructure"
        focus: "IaC validation, module analysis, state management"

      security:
        always: true
        agent: "devops-specialist-security"
        focus: "tfsec findings, secret exposure, compliance"

      finops:
        condition: "--plan OR --apply"
        agent: "devops-specialist-finops"
        focus: "Cost estimation, waste detection, right-sizing"

      cloud_specialist:
        condition: "provider detected"
        routing:
          aws: "devops-specialist-aws"
          google: "devops-specialist-gcp"
          azurerm: "devops-specialist-azure"
        focus: "Provider-specific best practices, service limits"

      os_specialist:
        condition: "provisioner or user_data detected"
        routing:
          detect: "Parse target OS from AMI, image, or user_data"
          dispatch: "devops-executor-linux → os-specialist-{distro}"
        focus: "OS-level provisioning commands validation"

  3_collect_results:
    action: "Merge agent results into consolidated report"
    format: "condensed JSON per agent → unified summary"
```

**Example dispatch (AWS + security + cost):**

```
# Single message with 3 parallel Task calls:
Task(subagent_type="devops-specialist-infrastructure", prompt="Validate Terraform modules in /workspace/terraform/")
Task(subagent_type="devops-specialist-aws", prompt="Review AWS provider config and resource best practices")
Task(subagent_type="devops-specialist-security", prompt="Run security analysis on Terraform code")
```

---

### Phase 2.0: Secret Discovery (1Password)

**Check 1Password for infrastructure secrets before any operation:**

```yaml
infra_secret_discovery:
  trigger: "Before --plan, --apply, --validate"
  blocking: false  # Informatif seulement

  1_check_1password:
    condition: "command -v op && test -n $OP_SERVICE_ACCOUNT_TOKEN"
    on_failure: "Skip (1Password not configured)"

  2_resolve_project_path:
    action: "Extract org/repo from git remote"

  3_scan_tfvars:
    action: "Detect variables referenced in *.tf and *.tfvars"
    command: 'grep -rh "variable\s" *.tf | sed "s/variable\s*\"/TF_VAR_/;s/\".*//"'
    output: "required_vars[]"

  4_check_vault_for_secrets:
    action: "List 1Password items matching project path + TF_VAR_ prefix"
    command: |
      op item list --vault='$VAULT_ID' --format=json \
        | jq -r '.[] | select(.title | startswith("'$PROJECT_PATH'/")) | .title'
    filter: "Items matching TF_VAR_*, AWS_*, AZURE_*, GCP_*"

  5_cross_path_check:
    action: "Also check shared-infra path for common secrets"
    paths:
      - "${ORG}/shared-infra"
      - "${ORG}/infrastructure"
    match: "AWS_*, AZURE_*, GCP_*, TF_VAR_*"

  6_output:
    if_secrets_found: |
      ═══════════════════════════════════════════════════════════════
        /infra - 1Password Secrets Available
      ═══════════════════════════════════════════════════════════════

        Project secrets ({PROJECT_PATH}):
          ├─ TF_VAR_db_password
          └─ TF_VAR_api_key

        Shared secrets ({ORG}/shared-infra):
          ├─ AWS_CREDENTIALS
          └─ TF_VAR_region

        Use /secret --get <key> to retrieve
        Or /secret --get <key> --path <org>/shared-infra

      ═══════════════════════════════════════════════════════════════
    if_no_secrets: "(no infra secrets found in 1Password)"
```

---

### Phase 3.0: Validation (--validate)

Run comprehensive validation suite:

```yaml
validation_suite:
  1_format:
    command: "terraform fmt -check -recursive"
    fix: "terraform fmt -recursive"

  2_validate:
    command: "terraform validate"

  3_tflint:
    command: "tflint --config .tflint.hcl"
    config: |
      plugin "terraform" {
        enabled = true
        preset  = "recommended"
      }

  4_tfsec:
    command: "tfsec --soft-fail"

  5_checkov:
    command: "checkov -d . --framework terraform"
    optional: true
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  /infra --validate
═══════════════════════════════════════════════════════════════

  Format Check:
    └─ ✓ All files properly formatted

  Terraform Validate:
    └─ ✓ Configuration is valid

  TFLint:
    ├─ Warnings: 2
    │   ├─ Line 45: Consider using for_each instead of count
    │   └─ Line 89: Variable 'unused_var' is declared but not used
    └─ Errors: 0

  TFSec:
    ├─ Critical: 0
    ├─ High: 0
    ├─ Medium: 1
    │   └─ aws-ec2-no-public-ip: EC2 instance has public IP
    └─ Low: 3

  Overall: ✓ Validation passed (warnings present)

═══════════════════════════════════════════════════════════════
```

---

### Phase 4.0: Plan (--plan)

Generate and analyze execution plan:

```yaml
plan_workflow:
  1_init:
    condition: ".terraform not exists OR --force-init"
    command: "terraform init -upgrade"

  2_plan:
    command: "terraform plan -out=tfplan"
    output: "tfplan"

  3_analyze:
    action: "Parse plan for changes"
    categories:
      - create
      - update
      - replace
      - destroy

  4_security_review:
    action: "Check for sensitive changes"
    warn_on:
      - "aws_iam_*"
      - "vault_*_secret*"
      - "*_password*"
      - "*_token*"
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  /infra --plan
═══════════════════════════════════════════════════════════════

  Module: terraform/k8s_driver

  Changes Summary:
    ├─ Create: 3
    │   ├─ kubernetes_deployment.app
    │   ├─ kubernetes_service.app
    │   └─ kubernetes_config_map.config
    ├─ Update: 1
    │   └─ helm_release.cilium (values changed)
    ├─ Replace: 0
    └─ Destroy: 0

  Resource Details:
    + kubernetes_deployment.app
      + metadata.name = "my-app"
      + spec.replicas = 3

    ~ helm_release.cilium
      ~ values = (sensitive)

  Security Review:
    └─ ✓ No sensitive resources modified

  Plan saved to: tfplan

  Next: Run `/infra --apply` to apply these changes

═══════════════════════════════════════════════════════════════
```

---

### Phase 5.0: Apply (--apply)

Apply changes with safety checks:

```yaml
apply_workflow:
  1_verify_plan:
    condition: "tfplan file exists"
    action: "Verify plan is current"

  2_confirmation:
    condition: "NOT --auto-approve"
    tool: AskUserQuestion
    question: "Apply these changes?"

  3_apply:
    command: "terraform apply tfplan"

  4_verify:
    command: "terraform show"
    action: "Verify resources created"

  5_cleanup:
    action: "Remove tfplan file"
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  /infra --apply
═══════════════════════════════════════════════════════════════

  Module: terraform/k8s_driver
  Plan: tfplan (generated 5m ago)

  Applying changes...

  Progress:
    [====================] 100%

  Applied:
    ✓ kubernetes_deployment.app (created)
    ✓ kubernetes_service.app (created)
    ✓ kubernetes_config_map.config (created)
    ✓ helm_release.cilium (updated)

  Summary:
    ├─ Created: 3
    ├─ Updated: 1
    ├─ Destroyed: 0
    └─ Duration: 45s

  State: terraform.tfstate updated

═══════════════════════════════════════════════════════════════
```

---

### Phase 6.0: Documentation (--docs)

Generate documentation with terraform-docs:

```yaml
docs_workflow:
  1_find_modules:
    command: "find . -name '.terraform-docs.yml'"

  2_generate:
    for_each: module
    command: "terraform-docs --config .terraform-docs.yml ."

  3_verify:
    command: "terraform-docs --output-check"
```

**Output:**

```
═══════════════════════════════════════════════════════════════
  /infra --docs
═══════════════════════════════════════════════════════════════

  Generating documentation...

  Modules processed:
    ├─ terraform/_modules/networking  ✓ README.md updated
    ├─ terraform/_modules/kubernetes  ✓ README.md updated
    ├─ terraform/_modules/vault       ✓ README.md updated
    └─ terraform/_modules/openstack   ✓ README.md updated

  Summary: 4 modules documented

═══════════════════════════════════════════════════════════════
```

---

## Terragrunt Support

### run-all Commands

```yaml
terragrunt_commands:
  plan_all:
    command: "terragrunt run-all plan"

  apply_all:
    command: "terragrunt run-all apply"
    options:
      - "--terragrunt-parallelism 3"

  destroy_all:
    command: "terragrunt run-all destroy"
    confirmation: MANDATORY
```

### Dependency Graph

```yaml
dependency_analysis:
  command: "terragrunt graph-dependencies"
  output: "Show dependency tree"
```

---

## Safety Guards

| Action | Guard |
|--------|-------|
| Destroy | ALWAYS requires confirmation |
| Apply without plan | BLOCKED |
| Apply to production | Requires `--environment production` flag |
| Sensitive resource changes | Warning + review |
| State manipulation | BLOCKED (manual only) |

### Blocked Commands

```yaml
blocked_commands:
  - "terraform state rm"
  - "terraform state mv"
  - "terraform import"
  - "terraform force-unlock"
  - "terragrunt destroy --terragrunt-non-interactive"
```

---

## Configuration

### .infra.yml (optional)

```yaml
# Project-specific infrastructure configuration

default_tool: terragrunt
modules_path: terraform/_modules

validation:
  tflint: true
  tfsec: true
  checkov: false

environments:
  production:
    require_approval: true
    backend: consul
  staging:
    require_approval: false
    backend: local
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `/plan` | Use before `/infra --plan` for complex changes |
| `/review` | Review infrastructure code changes |
| `/git` | Commit infrastructure changes |
| `/search` | Research Terraform patterns |

---

## Examples

### Initialize and Plan

```
/infra --init --module terraform/k8s_driver
/infra --plan --module terraform/k8s_driver
```

### Validate All Modules

```
/infra --validate --all
```

### Apply with Terragrunt

```
/infra --apply --all
```

### Generate Documentation

```
/infra --docs
```
