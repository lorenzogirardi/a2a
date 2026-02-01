# Project Status

## Current Phase: Foundation
## Last Updated: 2026-02-01

---

## Progress

### Completed
- [x] Project structure created
- [x] Storage layer implemented (MemoryStorage)
- [x] Auth/permissions system (Role, Permission, CallerContext, @requires_permission)
- [x] Base agent class (AgentBase with think/act/receive_message)
- [x] Simple agents (EchoAgent, CounterAgent, RouterAgent, CalculatorAgent)
- [x] LLM agent stub (LLMAgent, ToolUsingLLMAgent)
- [x] MCP server implementation (AgentMCPServer)
- [x] Demo script (main.py)
- [x] .claude configuration complete
  - [x] CLAUDE.md with project conventions
  - [x] status.md for progress tracking
  - [x] Skills: python, mcp, scm, spec-driven-dev
  - [x] Templates: spec.md, tasks.md

---

## In Progress
- [x] Refactor protocol/ to use FastMCP + FastAPI (DONE)

---

## Next Steps

### Priority 1 (Immediate) - COMPLETED
1. ~~Refactor `protocol/mcp_server.py` to use FastMCP decorators~~ ✓
2. ~~Create `protocol/api.py` with FastAPI endpoints~~ ✓
3. ~~Create initial tests for agents~~ ✓
4. ~~Test both MCP and REST interfaces~~ ✓

### Priority 2 (Short-term)
1. Add file-based storage (FileStorage)
2. Implement LLM agent with real Claude calls
3. Add agent discovery mechanism

### Priority 3 (Future)
1. Database storage (SQLite/PostgreSQL)
2. Agent orchestration patterns
3. Multi-agent workflows
4. SSE transport for MCP

---

## Blockers
- None currently

---

## Key Decisions

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Storage pattern | Abstract interface | Easy to swap implementations | 2026-02-01 |
| Auth model | Role-based + decorator | Simple, explicit, auditable | 2026-02-01 |
| Protocol | MCP | Standard Anthropic protocol, good tooling | 2026-02-01 |
| Agent pattern | think/act/respond | Clear separation of concerns | 2026-02-01 |
| **MCP Server** | **FastMCP** | Decorator-based, simpler than raw mcp | 2026-02-01 |
| **HTTP API** | **FastAPI** | REST for non-MCP clients, shared Pydantic | 2026-02-01 |

---

## Architecture Notes

### Agent Communication Flow
```
User -> CallerContext -> Agent.receive_message() -> think() -> act() -> Response
                                    |
                                    v
                            Storage.save_message()
```

### Permission Check Flow
```
@requires_permission(Permission.X)
    -> Extract CallerContext
    -> Check role permissions
    -> Check custom permissions
    -> Allow/Deny
```

---

## Session Log

### 2026-02-01
- Created project structure
- Implemented all core modules
- Completed .claude configuration (adapted from ai-ecom-demo)
  - Added status.md tracking requirement to CLAUDE.md
  - Created skills: python, mcp, scm, spec-driven-dev
  - Created templates for specs and tasks
- Decided to use **FastMCP** + **FastAPI** for protocol layer
  - FastMCP: decorator-based MCP server (@mcp.tool())
  - FastAPI: REST API for non-MCP clients
  - Updated requirements.txt, CLAUDE.md, mcp skill
- Added **Test Pyramid** requirement
  - Unit (70%), Integration (20%), E2E (10%)
  - Updated CLAUDE.md and python skill
- Added **Security GitHub Action** (.github/workflows/security.yml)
  - Trivy, TruffleHog, Bandit, pip-audit, Semgrep
  - Created security skill
- Created **README.md** with project overview
- Pushed to GitHub: https://github.com/lorenzogirardi/a2a
- **Priority 1 COMPLETED**:
  - Refactored mcp_server.py to FastMCP (@mcp.tool decorators)
  - Created api.py with FastAPI REST endpoints
  - Created test pyramid:
    - tests/unit/test_agents.py
    - tests/unit/test_storage.py
    - tests/unit/test_permissions.py
    - tests/integration/test_agent_communication.py
    - tests/e2e/test_fastapi.py
  - Added pyproject.toml with pytest config
  - Fixed security workflow (semgrep container, trufflehog first push)
