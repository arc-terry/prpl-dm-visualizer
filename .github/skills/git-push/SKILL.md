---
name: git-push
description: 'Safely push committed changes to a remote branch with checks and user confirmation. Use when user asks to push, publish a branch, or upload commits.'
license: MIT
allowed-tools: Bash
---

# Git Push Safely

## Overview

Push local commits to a remote branch with safety checks and explicit confirmation.

## Workflow

### 1. Verify status and branch

```bash
git status --porcelain

git branch --show-current
```

- If there are unstaged or uncommitted changes, stop and ask the user to commit first.

### 2. Confirm remote and upstream

```bash
git remote -v

git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

- If no upstream is set, prepare to push with `-u origin <branch>`.

### 3. Sync before pushing

```bash
git fetch --prune

git status -sb
```

- If the branch is behind, ask whether to pull (prefer `git pull --rebase` when appropriate).
- If the branch is ahead only, proceed to push.

### 4. Confirm and push

Always show the planned command and ask for confirmation before pushing.

```bash
# With upstream set
git push

# First push for a new branch
git push -u origin <branch>
```

## Safety rules

- NEVER force push unless the user explicitly requests it.
- NEVER push to main/master unless the user explicitly requests it.
- If there are unpushed commits on multiple branches, confirm the target branch with the user.
- Do not alter git config.
