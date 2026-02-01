# Project Status

## Current Phase: Use Cases
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
- [x] **Research Assistant** (Use Case #1)
  - [x] Parallel search agents (Web, Docs, Code)
  - [x] MergeAgent for result aggregation
  - [x] OrchestratorAgent (fan-out/fan-in pattern)
  - [x] FastAPI + FastMCP integration
  - [x] Unit + Integration tests
- [x] **FileStorage** (Infrastructure)
  - [x] JSON file persistence
  - [x] Conversations + Agent states
  - [x] 13 unit tests
- [x] **LLM Agent con Claude API** (Infrastructure)
  - [x] ToolUsingLLMAgent con tool_use loop
  - [x] Supporto handler sync/async
  - [x] 14 unit tests
- [x] **Agent Discovery** (Infrastructure)
  - [x] AgentRegistry centrale
  - [x] Find by ID o capabilities
  - [x] 22 unit tests
- [x] **Documentation Structure** (docs/)
  - [x] Enterprise Architecture
  - [x] Software Architecture
  - [x] Platform Architecture
- [x] **PostgreSQL Storage** (Infrastructure)
  - [x] Docker Compose setup
  - [x] asyncpg implementation
  - [x] Connection pooling
  - [x] 12 integration tests
- [x] **SSE Transport** (Infrastructure)
  - [x] Real-time streaming events
  - [x] Tool calls via HTTP POST
  - [x] Event broadcasting
  - [x] 8 integration tests
- [x] **Documentation** (docs/)
  - [x] Enterprise Architecture (capabilities, domain, ADRs)
  - [x] Software Architecture (components, patterns, APIs)
  - [x] Platform Architecture (Docker, DB, operations)
- [x] **Chain Pipeline Demo** (Use Case #2)
  - [x] Sequential agent chain: Writer → Editor → Publisher
  - [x] ChainStepAgent base class (extends LLMAgent)
  - [x] Pydantic models: PipelineInput, StepResult, PipelineResult
  - [x] ChainPipeline orchestrator with SSE events
  - [x] API endpoints: /api/chain/run, /api/chain/status, /api/chain/events
  - [x] Live visualization webpage (static/chain/)
  - [x] Unit tests (21), Integration tests (8), E2E tests (8)
  - [x] Documentation: docs/software-architecture/chain-pattern.md
- [x] **LangGraph Integration** (Use Case #4)
  - [x] LangGraph StateGraph with DAG-based execution
  - [x] 4 nodes: analyze, discover, execute, synthesize
  - [x] Conditional edges for synthesis decision
  - [x] GraphRunner with SSE streaming
  - [x] vis.js real-time graph visualization
  - [x] API endpoints: /api/graph/run, /api/graph/stream, /api/graph/structure
  - [x] Live visualization webpage (static/graph/)
  - [x] Unit tests (36), Integration tests (7)
  - [x] Documentation:
    - [x] langgraph-pattern.md (architecture + why not LangChain)
    - [x] langgraph-execution-example.md (detailed walkthrough)
    - [x] Demo video embedded (Cloudinary)
  - [x] README updated with LangGraph section

---

## In Progress
- [ ] None currently

---

## Next Steps

### Priority 1 (Immediate) - COMPLETED
1. ~~Refactor `protocol/mcp_server.py` to use FastMCP decorators~~ ✓
2. ~~Create `protocol/api.py` with FastAPI endpoints~~ ✓
3. ~~Create initial tests for agents~~ ✓
4. ~~Test both MCP and REST interfaces~~ ✓

### Priority 2 (Short-term) - COMPLETED
1. ~~Agent orchestration patterns~~ ✓ (Research Assistant)
2. ~~Multi-agent workflows~~ ✓ (Fan-out/Fan-in pattern)

### Priority 3 (Next) - COMPLETED
1. ~~Add file-based storage (FileStorage)~~ ✓
2. ~~Implement LLM agent with real Claude calls~~ ✓
3. ~~Add agent discovery mechanism~~ ✓

### Priority 4 (Future)
1. ~~Database storage (PostgreSQL)~~ ✓
2. ~~SSE transport for MCP~~ ✓
3. Additional use cases
4. ~~Populate documentation~~ ✓

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
| **Multi-Agent Pattern** | **Fan-out/Fan-in** | Parallel search, then merge results | 2026-02-01 |
| **Chain Pattern** | **Sequential Pipeline** | Writer → Editor → Publisher with SSE | 2026-02-01 |
| **LangGraph** | **DAG Orchestration** | StateGraph with conditional synthesis | 2026-02-01 |
| **LangGraph not LangChain** | **Direct Anthropic SDK** | Simpler, explicit, easier debugging | 2026-02-01 |

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
- **Research Assistant Implementation** (Use Case #1):
  - Created `agents/research/` module:
    - `models.py`: SearchResult, AggregatedResult (Pydantic)
    - `base.py`: SearchAgentBase abstract class
    - `web_search.py`: WebSearchAgent (mock data)
    - `doc_search.py`: DocSearchAgent (mock data)
    - `code_search.py`: CodeSearchAgent (mock data)
    - `merge.py`: MergeAgent (aggregation + deduplication)
    - `orchestrator.py`: OrchestratorAgent (parallel fan-out/fan-in)
  - Added `/api/research?q=...` endpoint (FastAPI)
  - Added `research(query)` tool (FastMCP)
  - Tests: `test_research_agents.py`, `test_research_pipeline.py`
  - Fixed Bandit B104: env vars for host binding
  - Created spec and tasks in `specs/`
- **Chain Pipeline Demo Implementation** (Use Case #2):
  - Created `agents/chain/` module:
    - `models.py`: PipelineInput, StepResult, PipelineResult (Pydantic)
    - `base.py`: ChainStepAgent abstract class (extends LLMAgent)
    - `writer.py`: WriterAgent - generates initial text
    - `editor.py`: EditorAgent - improves and corrects
    - `publisher.py`: PublisherAgent - formats for publication
    - `pipeline.py`: ChainPipeline orchestrator with SSE events
  - Created `protocol/chain_router.py`:
    - POST /api/chain/run - start pipeline
    - GET /api/chain/status/{id} - get status/result
    - GET /api/chain/agents - list chain agents
    - GET /api/chain/events/{id} - SSE events stream
  - Created `static/chain/` frontend:
    - index.html - demo page structure
    - app.js - SSE client and UI logic
    - style.css - dark theme styling
  - Tests:
    - 21 unit tests (test_chain_agents.py)
    - 8 integration tests (test_chain_pipeline.py)
    - 8 E2E tests (test_chain_api.py)
  - Documentation: docs/software-architecture/chain-pattern.md
  - **KPI & Communication Visualization**:
    - TokenUsage model with input/output token tracking
    - TransformResult dataclass for metadata capture
    - transform_with_metadata() for full pipeline stats
    - KPI Dashboard: duration, tokens, model, estimated cost
    - Agent Communication View: colored message bubbles showing flow
    - LiteLLM integration for multi-provider LLM support
  - **Documentation Updated**:
    - docs/software-architecture/chain-pattern.md (full docs)
    - docs/software-architecture/README.md (sequence diagram)
    - docs/README.md (quick links)
    - README.md (project overview with demos)
- [x] **Smart Task Router** (Use Case #3)
  - [x] AnalyzerAgent: LLM-based capability extraction
  - [x] TaskExecutor: Execute subtasks on matched agents
  - [x] SmartRouter: Orchestrate analyze → discover → execute
  - [x] Registry-based agent discovery
  - [x] SSE events for real-time UI updates
  - [x] API endpoints: /api/router/route, /api/router/registry
  - [x] Live visualization webpage (static/router/)
  - [x] Unit tests (37 tests)
  - [x] Documentation: docs/software-architecture/router-pattern.md
  - [x] **Two-Phase Execution** (Context Preservation)
    - [x] SynthesizerAgent: Integrates parallel outputs
    - [x] 5 Specialist Agents: Research, Estimation, Analysis, Translation, Summary
    - [x] Phase 1 (parallel) → Phase 2 (synthesis)
    - [x] Frontend Step 4: Synthesis visualization
- **LangGraph Documentation Completion**:
  - [x] Detailed execution example with real task walkthrough
  - [x] State-based node communication explained
  - [x] Agent selection criteria (Analyzer prompt + capability matching)
  - [x] Registry matching algorithm documented
  - [x] Parallel execution with asyncio.gather explained
  - [x] SSE reduced to UI-only note (not orchestration)
  - [x] "Why LangGraph but not LangChain" architectural decision
  - [x] Demo video embedded (Cloudinary thumbnail)
  - [x] README updated with full LangGraph section
