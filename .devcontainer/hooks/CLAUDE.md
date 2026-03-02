<!-- updated: 2026-02-25T12:30:00Z -->
# DevContainer Hooks

## Purpose

Lifecycle scripts for devcontainer events using a delegation architecture.

## Structure

```text
hooks/
├── lifecycle/          # Delegation stubs (thin wrappers)
│   ├── initialize.sh   # Initial setup (Ollama on host) - NOT delegated
│   ├── onCreate.sh     # Delegates to image-embedded hook
│   ├── postAttach.sh   # Delegates to image-embedded hook
│   ├── postCreate.sh   # Delegates to image-embedded hook
│   ├── postStart.sh    # Delegates to image-embedded hook
│   └── updateContent.sh # Delegates to image-embedded hook
├── shared/             # Shared utilities
│   └── utils.sh        # Common functions (needed by initialize.sh)
└── project/            # Project-specific extensions (optional)
    └── .gitkeep
```

## Delegation Architecture

Workspace hooks are thin stubs that delegate to image-embedded implementations:

1. **DEV** path: `/workspace/.devcontainer/images/hooks/` (template dev only)
2. **IMG** path: `/etc/devcontainer-hooks/` (all downstream containers)
3. **EXT** path: `/workspace/.devcontainer/hooks/project/` (project extensions)

This ensures hooks auto-update when the Docker image is rebuilt.

**Exception:** `initialize.sh` runs on the host machine, cannot be embedded.

## Lifecycle Events

| Event | Script | Description |
|-------|--------|-------------|
| onCreate | onCreate.sh | Initial container creation |
| postCreate | postCreate.sh | After container ready (once, guarded) |
| postAttach | postAttach.sh | After VS Code attaches |
| postStart | postStart.sh | After each start (MCP, grepai, VPN) |

## postStart Services

| Service | Function | Description |
|---------|----------|-------------|
| Shell env repair | `step_shell_env_repair` | v1→v3 upgrade, duplicate cleanup |
| Completion cache | `step_cache_completions` | Pre-generate `~/.zsh_completions/` |
| p10k segments | `step_generate_p10k_segments` | Dynamic `~/.p10k-segments.zsh` |
| grepai watch | `init_semantic_search` | `.health-stamp` + watchdog (60s) |
| VPN | `init_vpn` | 1Password profile detection |

## Conventions

- Stubs must be executable (chmod +x)
- Do NOT add logic to stubs — modify image hooks instead
- `initialize.sh` is the only hook with inline logic (host-side)
- Use `run_step` pattern from `shared/utils.sh` in image hooks
