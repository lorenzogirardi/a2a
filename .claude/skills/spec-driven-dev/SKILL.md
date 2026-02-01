---
name: spec-driven-dev
description: >-
  Spec-driven development framework for A2A features. Orchestrates from
  intent to implementation via structured specs and task breakdown.
  Triggers on "/spec.plan", "/spec.refine", "/spec.tasks", "/spec.run",
  "I want to build", "I want to add", "create spec", "new feature".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Task
---

# Spec-Driven Development

Iterative feature development ensuring zero ambiguity before execution.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/spec.plan <intent>` | Create spec from feature description |
| `/spec.refine [section]` | Improve spec with research |
| `/spec.tasks` | Break spec into executable tasks |
| `/spec.run [task#]` | Execute tasks with TDD |

---

## Core Principle

**Iterate until clarity**: No task execution begins until ALL questions are resolved.

---

## Phase 1: `/spec.plan` - Create Specification

**Trigger**: `/spec.plan <description>` or "I want to build/add X"

### Workflow

1. **Check `specs/` folder** - create if missing
2. **Generate spec file**: `specs/{feature-slug}.md`
3. **Fill initial sections** from user intent
4. **Generate clarifying questions**
5. **STOP and present questions**

---

## Phase 2: `/spec.refine` - Research & Improve

**Trigger**: `/spec.refine [section]`

### Workflow

1. Load active DRAFT spec
2. Search codebase for similar patterns
3. Update Technical Strategy
4. Re-evaluate clarity
5. **If questions remain: STOP and present**

---

## Phase 3: `/spec.tasks` - Task Breakdown

**Trigger**: `/spec.tasks`

### Prerequisites

- Active spec must be DRAFT or APPROVED
- "Open Questions" section must be empty
- If questions exist: **STOP → clarify first**

### Task Granularity

Tasks should be **high-level logical units**:
- "Implement FileStorage class"
- "Add agent discovery mechanism"
- "Create tests for router agent"

---

## Phase 4: `/spec.run` - Execute Tasks

**Trigger**: `/spec.run [task#]`

### Execution Rules

- **TDD for each task**: Red → Green → Refactor → Commit
- **Invoke `/python`** for .py files
- **Mark completed** in task file
- **Update status.md** after each task

---

## File Structure

```
specs/
├── file-storage.md           # Spec (APPROVED)
├── file-storage.tasks.md     # Task breakdown
├── agent-discovery.md        # Spec (DRAFT)
└── ...
```

---

## Spec Status Flow

```
DRAFT -> APPROVED -> IN_PROGRESS -> COMPLETED
          |              |
          v              v
      (questions?)   (blocked?)
          |              |
          v              v
        DRAFT      IN_PROGRESS
```

---

## A2A-Specific Scopes

When creating specs, consider these modules:

| Module | Files | Considerations |
|--------|-------|----------------|
| Agents | `agents/*.py` | Base class, think/act pattern |
| Storage | `storage/*.py` | Abstract interface |
| Auth | `auth/*.py` | Permissions, roles |
| Protocol | `protocol/*.py` | MCP integration |

---

## Session Resume

On context compaction:

1. **READ `.claude/status.md`**
2. Check `specs/` for files with status `IN_PROGRESS`
3. Check `.tasks.md` files for unchecked items
4. Report: "Found in-progress spec: X with Y tasks remaining"
5. Ask: "Continue with /spec.run?"
