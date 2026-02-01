---
name: scm
description: >-
  Git workflow and source control management for A2A project. Covers
  Conventional Commits, branch strategy, PR workflow, and conflict resolution.
  Triggers on "git", "commit", "branch", "merge", "rebase", "pull request", "PR",
  "conventional commits", "git workflow", "push", "commit message".
  PROACTIVE: MUST invoke when performing Git operations.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Source Control Management (SCM) Skill

## Quick Reference

| Principle | Rule |
|-----------|------|
| Atomic Commits | One logical change per commit |
| Conventional Commits | `type(scope): description` format |
| Branch Naming | `type/description` format |
| Never Force Push | To shared branches (main) |

---

## Branching Strategy (GitHub Flow)

```
main ─────●───────●───────●───────●──────
          │       ↑       │       ↑
          ↓       │       ↓       │
feature ──●──●──●─┘ fix ──●──●────┘
```

**Branches:**
- `main`: Always deployable (protected)
- `feature/*`: New features
- `fix/*`: Bug fixes
- `chore/*`: Maintenance
- `docs/*`: Documentation

---

## Conventional Commits

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(agent): add memory agent` |
| `fix` | Bug fix | `fix(auth): correct permission check` |
| `docs` | Documentation | `docs(readme): update setup guide` |
| `style` | Formatting | `style(storage): fix indentation` |
| `refactor` | Code restructure | `refactor(base): extract validation` |
| `test` | Tests | `test(echo): add response tests` |
| `chore` | Build/tooling | `chore(deps): update pydantic` |

### Scopes (A2A Project)

| Scope | Area |
|-------|------|
| `agent` | Agent classes |
| `storage` | Storage implementations |
| `auth` | Permissions system |
| `protocol` | MCP server |
| `mcp` | MCP integration |
| `tests` | Test files |

---

## Branch Naming

```
<type>/<description>

Examples:
- feature/memory-agent
- fix/permission-decorator
- chore/update-dependencies
```

---

## Commit Workflow

### TDD Commit Pattern

```bash
# Red phase
git add tests/
git commit -m "test(agent): add calculator tests"

# Green phase
git add agents/
git commit -m "feat(agent): implement calculator logic"

# Refactor phase
git add agents/
git commit -m "refactor(agent): extract math operations"
```

### Multi-line Commit (HEREDOC)

```bash
git commit -m "$(cat <<'EOF'
feat(storage): add file-based storage

- Implement FileStorage class
- Support JSON serialization
- Add backup rotation

Closes #12
EOF
)"
```

---

## Before Creating PR

```bash
# 1. Ensure branch is up to date
git fetch origin
git rebase origin/main

# 2. Run tests locally
pytest

# 3. Review changes
git diff origin/main...HEAD
git log origin/main..HEAD --oneline
```

---

## Safety Rules

### Never Do

```bash
# Never force push to main
git push --force origin main  # DANGEROUS

# Never rebase shared branches
git rebase main  # on shared feature branch

# Never reset pushed commits
git reset --hard HEAD~3  # if already pushed
```

### Safe Alternatives

```bash
# Use force-with-lease
git push --force-with-lease

# Merge instead of rebase on shared
git merge origin/main

# Revert instead of reset
git revert <sha>
```

---

## Common Operations

### Undo Operations

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo uncommitted changes
git checkout -- path/to/file

# Revert pushed commit
git revert <sha>
```

### Stashing

```bash
# Stash changes
git stash save "WIP: feature description"

# List stashes
git stash list

# Apply and drop
git stash pop
```

---

## Checklist

Before committing:
- [ ] Changes are atomic (one logical change)
- [ ] Commit message follows Conventional Commits
- [ ] Tests pass locally (`pytest`)
- [ ] No debug code or print statements
- [ ] No secrets or credentials
- [ ] Branch is up to date with main

Before creating PR:
- [ ] Rebased on latest main
- [ ] All commits have meaningful messages
- [ ] Description explains what and why
- [ ] CI checks pass
