---
name: git-semver-tag
description: 'Create and manage semantic version tags (vMAJOR.MINOR.PATCH) with safety checks. Use when user asks to tag a release, bump version tags, or follow SemVer.'
allowed-tools: Bash
---

# Git SemVer Tagging

## Overview

Create annotated git tags that follow Semantic Versioning. Use a consistent `vMAJOR.MINOR.PATCH` format and avoid rewriting public tags.

## SemVer rules (summary)

- **MAJOR**: incompatible API changes
- **MINOR**: backward-compatible feature additions
- **PATCH**: backward-compatible bug fixes
- Pre-release identifiers are allowed (e.g., `v1.2.0-rc.1`).

## Workflow

### 1. Inspect existing tags

```bash
git tag --list 'v*' --sort=-v:refname
```

### 2. Choose the next version

Pick the next version explicitly (do not guess):
- Patch bump: `v1.2.3` -> `v1.2.4`
- Minor bump: `v1.2.3` -> `v1.3.0`
- Major bump: `v1.2.3` -> `v2.0.0`

### 3. Create an annotated tag

```bash
git tag -a v1.2.3 -m "Release v1.2.3"
```

### 4. Push the tag

```bash
git push origin v1.2.3
```

## Safety rules

- Never delete or move tags unless the user explicitly asks.
- Prefer annotated tags for releases.
- Confirm the exact version string with the user before tagging.
