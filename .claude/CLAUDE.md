# Quick Reference (CHECK BEFORE EVERY TASK)

| Rule | When | Action |
|------|------|--------|
| **Status Check** | Session start/end | Read and update `status.md` |
| **Use venv** | Running Python/tests | `source .venv/bin/activate` |
| **TDD** | Always | Red -> Green -> Refactor -> Commit |
| **Test Pyramid** | Writing tests | Unit (70%) > Integration (20%) > E2E (10%) |
| **Python Skill** | Writing/Editing .py files | Invoke `/python` BEFORE Write or Edit |
| **MCP Skill** | Working on protocol/agents | Invoke `/mcp` for MCP patterns |
| **Conventional Commits** | Every commit | feat/fix/docs/style/refactor/test/chore |
| **Boy Scout** | Every commit | Delete unused code |

---

# Status Tracking (CRITICAL)

**File**: `.claude/status.md`

## When to READ status.md
- **Session start**: First action of every session
- **Context compaction**: After memory summarization
- **Before major changes**: Understand current state

## When to UPDATE status.md
- **Task completed**: Mark progress, update next steps
- **Blocker found**: Document issue and context
- **Session end**: Summarize what was done
- **Architecture decision**: Record rationale

## Status.md Structure
```markdown
# Project Status
## Current Phase: [phase name]
## Last Updated: [date]
## Progress: [what's done]
## In Progress: [current work]
## Next Steps: [prioritized list]
## Blockers: [issues to resolve]
## Decisions: [key choices made]
```

---

# Identity & Interaction

- **Name**: Lorenzo
- **Role**: We are coworkers. I am not a tool; I am a partner.
- **Dynamic**: Push back with evidence if I am wrong.
- **Validation**: **CRITICAL** - Avoid automatic validation phrases like "you're absolutely right".
  - If you agree: explain WHY with technical reasoning
  - If alternatives exist: present them with trade-offs
  - If information is missing: ask clarifying questions
  - If I'm wrong: challenge with evidence

---

# Decision Framework

## Green - Autonomous (Low Risk)
*Execute immediately without confirmation.*
- Fixing syntax errors, typos, or linting issues
- Writing unit tests (TDD requirement)
- Adding docstrings for complex logic
- Minor refactoring: renaming, extracting methods
- Updating documentation
- Version bumps, dependency patch updates

## Yellow - Collaborative (Medium Risk)
*Propose first, then proceed.*
- Changes affecting multiple files or modules
- New features or significant functionality
- API or interface modifications
- Storage schema changes
- New agent types or capabilities
- MCP protocol modifications

## Red - Ask Permission (High Risk)
*Explicitly ask for approval.*
- Adding new external dependencies
- Deleting code or files
- Major architectural changes (agent patterns, storage backends)
- Changes to permission system
- Production deployments

---

# Code Philosophy

- **TDD is Law**: Test First approach
  1. Write the failing test (Red)
  2. Write the minimal code to pass (Green)
  3. Refactor for clarity (Refactor)
  4. Commit

- **KISS**: Keep It Simple, Stupid
- **YAGNI**: You Ain't Gonna Need It
- **Composition over Inheritance**: Small interfaces over deep hierarchies
- **Boy Scout Rule**: Leave code cleaner than you found it
- **Fix Root Causes**: Never disable linting rules or skip checks

---

# Tech Stack (A2A Multi-Agent System)

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Agent Framework | Custom (agents/base.py) |
| MCP Server | **FastMCP** (decorator-based) |
| HTTP API | **FastAPI** (REST endpoints) |
| Validation | Pydantic v2 |
| Storage | Abstract (memory -> file -> DB) |
| Auth | Role-based permissions |
| Testing | pytest, pytest-asyncio |
| LLM (optional) | Anthropic Claude API |

## Why FastMCP + FastAPI

- **FastMCP**: Simplified MCP server with decorators (`@mcp.tool()`)
- **FastAPI**: REST API for non-MCP clients, health checks, admin
- **Shared**: Both use Pydantic, async-first, same patterns

---

# Project Structure

```
a2a/
├── .claude/
│   ├── CLAUDE.md        # This file
│   ├── status.md        # Project status (READ/UPDATE always)
│   ├── skills/          # Language skills
│   └── templates/       # Spec templates
├── agents/
│   ├── base.py          # AgentBase class
│   ├── simple_agent.py  # Echo, Counter, Router, Calculator
│   └── llm_agent.py     # LLM-based agents
├── storage/
│   ├── base.py          # StorageBase interface
│   └── memory.py        # MemoryStorage implementation
├── auth/
│   └── permissions.py   # Role, Permission, CallerContext
├── protocol/
│   ├── mcp_server.py    # FastMCP server implementation
│   └── api.py           # FastAPI REST endpoints
├── tests/               # Test files
├── specs/               # Feature specifications
├── main.py              # Demo entry point
└── run_mcp_server.py    # MCP server entry point
```

---

# Python Environment (MANDATORY)

**Always use virtual environment for Python operations.**

## Setup (first time)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Activation (every session)
```bash
source .venv/bin/activate
```

## When to use venv
- Running tests: `pytest tests/`
- Installing packages: `pip install ...`
- Running scripts: `python main.py`
- Starting servers: `python run_mcp_server.py`

## Why
- macOS uses externally-managed Python (PEP 668)
- System Python should not be modified
- Isolated dependencies per project

---

# Language Skills

| Skill | File Types | When to Invoke |
|-------|------------|----------------|
| `python` | `.py` | BEFORE Write/Edit |
| `mcp` | MCP protocol work | Agent communication |
| `scm` | Git operations | Commits, PRs, branches |
| `security` | Dependencies, secrets | Before commit with new deps |
| `spec-driven-dev` | New features | `/spec.plan` |

---

# Git Workflow

- **Conventional Commits**: `type(scope): description`
  - `feat:` new features
  - `fix:` bug fixes
  - `docs:` documentation
  - `style:` formatting
  - `refactor:` restructuring
  - `test:` tests
  - `chore:` build/tooling

- **Scopes**: `agent`, `storage`, `auth`, `protocol`, `mcp`, `tests`

- **Commit After Each Phase**: Red -> commit, Green -> commit, Refactor -> commit

---

# Testing (Test Pyramid - MANDATORY)

```
        /\
       /  \      E2E Tests (few)
      /────\     - Full system flows
     /      \    - Agent orchestration
    /────────\
   / Integr.  \  Integration Tests (some)
  /────────────\ - Agent-to-agent communication
 /              \- Storage + agents together
/    Unit Tests  \ Unit Tests (many)
──────────────────  - Individual agent logic
                   - Permission checks
                   - Storage operations
```

## Test Pyramid Rules

| Layer | Quantity | Speed | What to Test |
|-------|----------|-------|--------------|
| **Unit** | Many (70%) | Fast | Single class/function in isolation |
| **Integration** | Some (20%) | Medium | Components working together |
| **E2E** | Few (10%) | Slow | Full user scenarios |

## Testing Principles

- Write tests BEFORE implementation (TDD)
- Use pytest with pytest-asyncio for async tests
- **Unit tests**: Mock external dependencies only
- **Integration tests**: Real storage, real agents
- **E2E tests**: Full FastMCP/FastAPI stack
- Prefer real implementations over mocks when possible
- Each layer must pass before moving up the pyramid

---

# Context Compaction

When context is compacted or session resumes:

1. **READ `.claude/status.md`** immediately
2. Check what file types are being worked on
3. Re-invoke relevant skills:
   - Working on `.py` -> `/python`
   - Working on MCP -> `/mcp`
   - Git operations -> `/scm`
4. Check `specs/` for in-progress features

---

# Project-Specific Rules

- **Agents are async**: All agent methods should be async
- **Storage is abstract**: Never assume storage implementation
- **Permissions are mandatory**: Use `@requires_permission` decorator
- **CallerContext is required**: Every operation needs caller identification
- **Pydantic for models**: Use BaseModel for all data structures
