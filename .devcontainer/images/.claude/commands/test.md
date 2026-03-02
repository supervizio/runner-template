---
name: test
description: |
  E2E and frontend testing with Playwright MCP and RLM decomposition.
  Automates browser interactions, visual testing, and debugging.
  Use when: running E2E tests, debugging frontend, generating test code.
allowed-tools:
  - "mcp__playwright__*"
  - "Bash(npm:*)"
  - "Bash(npx:*)"
  - "Read(**/*)"
  - "Write(**/*)"
  - "Glob(**/*)"
  - "mcp__grepai__*"
  - "mcp__context7__*"
  - "Grep(**/*)"
  - "Task(*)"
---

# /test - E2E & Frontend Testing (RLM Architecture)

$ARGUMENTS

## GREPAI-FIRST (MANDATORY)

Use `grepai_search` for ALL semantic/meaning-based queries BEFORE Grep.
Use `grepai_trace_callers`/`grepai_trace_callees` for impact analysis.
Fallback to Grep ONLY for exact string matches or regex patterns.

## CONTEXT7 (RECOMMENDED)

Use `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` to:
- Verify Playwright API usage and available selectors
- Check test framework APIs (Jest, Vitest, pytest, Go testing)
- Validate assertion library patterns

---

## Overview

E2E tests and frontend debugging with **RLM** patterns:

- **Peek** - Analyze the page before interaction
- **Decompose** - Split the test into steps
- **Parallelize** - Simultaneous assertions and captures
- **Synthesize** - Consolidated test report

**Playwright MCP Capabilities:**

- **Navigation** - Open URLs, navigate, screenshots
- **Interaction** - Click, type, select, hover, drag
- **Assertions** - Verify text, elements, states
- **Tracing** - Record sessions for debugging
- **PDF** - Generate PDFs from pages
- **Codegen** - Generate test code

---

## Arguments

| Pattern | Action |
|---------|--------|
| `<url>` | Open the URL and explore the page |
| `--run` | Run the project's Playwright tests |
| `--debug <url>` | Interactive debug mode |
| `--trace` | Enable tracing for the session |
| `--screenshot <url>` | Screenshot the page |
| `--pdf <url>` | Generate a PDF of the page |
| `--codegen <url>` | Generate test code |
| `--help` | Show help |

---

## --help

```
═══════════════════════════════════════════════════════════════
  /test - E2E & Frontend Testing (RLM)
═══════════════════════════════════════════════════════════════

Usage: /test <url|action> [options]

Actions:
  <url>               Open and explore the page
  --run               Run project tests
  --debug <url>       Interactive debug mode
  --trace             Enable tracing
  --screenshot <url>  Screenshot
  --pdf <url>         Generate a PDF
  --codegen <url>     Generate test code

RLM Patterns:
  1. Peek       - Analyze the page (snapshot)
  2. Decompose  - Split into test steps
  3. Parallelize - Simultaneous assertions
  4. Synthesize - Consolidated report

MCP Tools:
  browser_navigate    Open a URL
  browser_click       Click element
  browser_type        Type text
  browser_snapshot    Capture state
  browser_expect      Assertions

Examples:
  /test https://example.com
  /test --screenshot https://myapp.com/login
  /test --run
  /test --codegen https://myapp.com

═══════════════════════════════════════════════════════════════
```

---

## Phase 1.0: Peek (RLM Pattern)

**Analyze the page BEFORE interaction:**

```yaml
peek_workflow:
  1_navigate:
    tool: mcp__playwright__browser_navigate
    params:
      url: "<url>"

  2_snapshot:
    tool: mcp__playwright__browser_snapshot
    output: "Accessibility tree of the page"

  3_analyze:
    action: "Identify interactive elements"
    extract:
      - forms: "input, select, textarea"
      - buttons: "button, [type=submit]"
      - links: "a[href]"
      - content: "main content areas"
```

**Phase 1 Output:**

```
═══════════════════════════════════════════════════════════════
  /test - Peek Analysis
═══════════════════════════════════════════════════════════════

  URL: https://myapp.com/login

  Page Structure:
    ├─ Header (nav, logo, menu)
    ├─ Main
    │   ├─ Form#login
    │   │   ├─ Input[email]
    │   │   ├─ Input[password]
    │   │   └─ Button[Submit]
    │   └─ Link[Forgot password]
    └─ Footer

  Interactive Elements: 5
  Forms: 1
  Testable: YES

═══════════════════════════════════════════════════════════════
```

---

## Phase 2.0: Decompose (RLM Pattern)

**Split the test into steps:**

```yaml
decompose_workflow:
  example_login_test:
    steps:
      - step: "Navigate to login"
        action: browser_navigate
        url: "/login"

      - step: "Fill email"
        action: browser_type
        element: "Email input"
        value: "user@test.com"

      - step: "Fill password"
        action: browser_type
        element: "Password input"
        value: "******"

      - step: "Submit form"
        action: browser_click
        element: "Submit button"

      - step: "Verify redirect"
        action: browser_expect
        expectation: "URL contains /dashboard"
```

---

## Phase 3.0: Parallelize (RLM Pattern)

**Simultaneous assertions and captures:**

```yaml
parallel_validation:
  mode: "PARALLEL (single message, multiple MCP calls)"

  actions:
    - task: "Visibility check"
      tool: mcp__playwright__browser_expect
      params:
        expectation: "to_be_visible"
        ref: "<dashboard_ref>"

    - task: "Text check"
      tool: mcp__playwright__browser_expect
      params:
        expectation: "to_have_text"
        ref: "<welcome_ref>"
        expected: "Welcome"

    - task: "Screenshot"
      tool: mcp__playwright__browser_screenshot
      params:
        fullPage: true
```

**IMPORTANT**: Launch ALL assertions in a SINGLE message.

---

## Phase 4.0: Synthesize (RLM Pattern)

**Consolidated test report:**

```yaml
synthesize_workflow:
  1_collect:
    action: "Gather all results"
    data:
      - step_results
      - assertions_passed
      - screenshots
      - timing

  2_analyze:
    action: "Identify failures and root causes"

  3_generate_report:
    format: "Structured test report"
```

**Final Output:**

```
═══════════════════════════════════════════════════════════════
  /test - Test Report
═══════════════════════════════════════════════════════════════

  URL: https://myapp.com/login
  Scenario: Login flow

  Steps:
    ✓ Navigate to /login (245ms)
    ✓ Fill email input (32ms)
    ✓ Fill password input (28ms)
    ✓ Click submit button (156ms)
    ✓ Verify dashboard redirect (1.2s)

  Assertions:
    ✓ Dashboard visible
    ✓ Welcome message present
    ✓ User avatar displayed

  Artifacts:
    - Screenshot: /tmp/test-login-success.png
    - Trace: /tmp/trace-login.zip

  Result: PASS (5/5 steps, 3/3 assertions)

═══════════════════════════════════════════════════════════════
```

---

## Workflows

### --run (Execute project tests)

```yaml
run_workflow:
  1_peek:
    action: "Scan test files"
    tools: [Glob]
    patterns: ["**/*.spec.ts", "**/*.test.ts", "**/e2e/**"]

  2_decompose:
    action: "Categorize tests"
    categories:
      - unit: "**/unit/**"
      - integration: "**/integration/**"
      - e2e: "**/e2e/**"

  3_parallelize:
    action: "Run test suites in parallel"
    tools: [Task agents]

  4_synthesize:
    action: "Consolidated test report"
```

### --trace (Debug with tracing)

```yaml
trace_workflow:
  1_start:
    tool: mcp__playwright__browser_start_tracing
    params:
      name: "debug-session"

  2_interact:
    action: "Perform interactions"

  3_stop:
    tool: mcp__playwright__browser_stop_tracing
    output: "trace.zip (viewable in trace.playwright.dev)"
```

### --codegen (Generate test code)

```yaml
codegen_workflow:
  1_peek:
    action: "Analyze page structure"

  2_record:
    action: "Record interactions"

  3_synthesize:
    action: "Generate Playwright test code"
    output: "*.spec.ts file"
```

---

## MCP Tools Reference

### Navigation

| Tool | Description |
|------|-------------|
| `browser_navigate` | Open a URL |
| `browser_go_back` | Previous page |
| `browser_go_forward` | Next page |
| `browser_reload` | Reload |

### Interaction

| Tool | Description |
|------|-------------|
| `browser_click` | Click element |
| `browser_type` | Type text |
| `browser_fill` | Fill a field |
| `browser_select_option` | Select option |
| `browser_hover` | Hover element |
| `browser_press_key` | Press key |

### Capture

| Tool | Description |
|------|-------------|
| `browser_snapshot` | Accessibility tree |
| `browser_screenshot` | Screenshot |
| `browser_pdf_save` | Generate PDF |

### Testing

| Tool | Description |
|------|-------------|
| `browser_expect` | Assertions |
| `browser_generate_locator` | Generate selector |
| `browser_start_tracing` | Start trace |
| `browser_stop_tracing` | Stop trace |

---

## Guardrails (ABSOLUTE)

| Action | Status | Reason |
|--------|--------|--------|
| Skip Phase 1 (Peek/Snapshot) | ❌ **FORBIDDEN** | Analyze page before interaction |
| Navigate to malicious sites | ❌ **FORBIDDEN** | Security |
| Enter real credentials | ⚠ **WARNING** | Use fixtures |
| Modify production data | ❌ **FORBIDDEN** | Test environment only |

### Legitimate parallelization

| Element | Parallel? | Reason |
|---------|-----------|--------|
| E2E steps (navigate->fill->click) | ❌ Sequential | Interaction order required |
| Independent final assertions | ✅ Parallel | No dependency between checks |
| Screenshots + validations | ✅ Parallel | Independent operations |
