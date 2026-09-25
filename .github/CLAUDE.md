<!-- updated: 2026-02-27T13:00:00Z -->
# GitHub Configuration

## Purpose

GitHub-specific configurations: workflows, templates, and instructions.

## Structure

```
.github/
├── workflows/          # GitHub Actions — see workflows/CLAUDE.md for what each one is for
├── actions/
│   ├── qemu-vm/        # Throwaway QEMU+KVM guest on a hosted runner
│   │   ├── action.yml        # image verified by pinned sha256/sha512 OR by a signed checksum
│   │   └── resolve-image.sh  # finds the build an upstream publishes now (openSUSE, Rocky)
│   └── release-candidate/  # e2e.yml release mode: pull a candidate's files by digest, place them
├── keys/               # PUBLIC OpenPGP keys qemu-vm verifies upstream images with (keys/CLAUDE.md)
├── instructions/       # AI instructions (gitignored)
├── dependabot.yml      # Dependency updates
└── CLAUDE.md           # This file
```

## Workflows

This repository is supervizio's public E2E runner; the devcontainer-template
workflows it was forked from (`docker-images.yml`, `release.yml`) are
inheritance, not the work. `workflows/CLAUDE.md` lists every workflow, where
it runs (GitHub-hosted only) and why.

## Dependency Management

| File | Description |
|------|-------------|
| dependabot.yml | Automated dependency update configuration |

## Instructions (gitignored)

| File | Description |
|------|-------------|
| codacy.instructions.md | Codacy code quality AI instructions |

## Conventions

- Workflows use reusable actions where possible
- Secrets stored in GitHub repository settings
- Branch protection on main
