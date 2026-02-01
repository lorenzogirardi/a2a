# Smart Task Router - Implementation Plan

## Overview

Un dispatcher intelligente che analizza la richiesta utente, identifica le capability richieste, trova gli agenti giusti nel Registry, e esegue il task.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                              │
│            "calcola 15 * 3 e scrivi un haiku"                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AnalyzerAgent (LLM)                         │
│  System: "Analizza il task e restituisci le capability         │
│           richieste come JSON array"                            │
│  Output: ["calculation", "creative_writing"]                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AgentRegistry                               │
│  find_by_capability("calculation") → [CalculatorAgent]          │
│  find_by_capability("creative_writing") → [WriterAgent]         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TaskExecutor                                │
│  1. CalculatorAgent.execute("15 * 3") → "45"                    │
│  2. WriterAgent.execute("scrivi haiku su 45") → "..."           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AGGREGATED RESULT                           │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
a2a/
├── agents/router/
│   ├── __init__.py
│   ├── models.py           # TaskInput, TaskResult, CapabilityMatch
│   ├── analyzer.py         # AnalyzerAgent (LLM-based)
│   ├── executor.py         # TaskExecutor
│   └── router.py           # SmartRouter (orchestrator)
├── protocol/
│   └── router_api.py       # FastAPI endpoints
├── static/router/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── tests/
    ├── unit/test_router_agents.py
    ├── integration/test_router_flow.py
    └── e2e/test_router_api.py
```

## Components

### 1. AnalyzerAgent

LLM-based agent che analizza il task e identifica le capability:

```python
class AnalyzerAgent(LLMAgent):
    """Analyzes user task and extracts required capabilities."""

    system_prompt = """Sei un analizzatore di task.
    Data una richiesta utente, identifica le capability richieste.

    Capability disponibili:
    - calculation: operazioni matematiche
    - echo: ripetizione messaggi
    - creative_writing: scrittura creativa
    - text_editing: modifica testi
    - formatting: formattazione documenti

    Rispondi SOLO con un JSON array di capability.
    Esempio: ["calculation", "creative_writing"]
    """

    async def analyze(self, task: str) -> list[str]:
        response = await self._call_llm(task)
        return json.loads(response)
```

### 2. TaskExecutor

Esegue i sub-task sugli agenti selezionati:

```python
class TaskExecutor:
    """Executes task parts on matched agents."""

    async def execute(
        self,
        task: str,
        agents: list[AgentBase],
        mode: str = "sequential"  # or "parallel"
    ) -> list[ExecutionResult]
```

### 3. SmartRouter

Orchestrator principale:

```python
class SmartRouter:
    """Routes tasks to appropriate agents based on capabilities."""

    def __init__(
        self,
        registry: AgentRegistry,
        analyzer: AnalyzerAgent,
        executor: TaskExecutor,
        event_handler: Optional[Callable] = None
    )

    async def route(self, task: str) -> RouterResult
```

## SSE Events

| Event | Data | When |
|-------|------|------|
| `routing_started` | `{task_id, task}` | Inizio routing |
| `analysis_started` | `{task_id}` | Analyzer inizia |
| `analysis_completed` | `{task_id, capabilities[]}` | Capability estratte |
| `discovery_started` | `{task_id, capability}` | Ricerca in registry |
| `discovery_completed` | `{task_id, capability, agents[]}` | Agenti trovati |
| `execution_started` | `{task_id, agent_id}` | Esecuzione inizia |
| `execution_completed` | `{task_id, agent_id, result}` | Esecuzione finita |
| `routing_completed` | `{task_id, results[]}` | Fine routing |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/router/route` | Route a task |
| GET | `/api/router/status/{id}` | Get routing status |
| GET | `/api/router/events/{id}` | SSE stream |
| GET | `/api/router/registry` | List registered agents |
| GET | `/static/router/` | Demo webpage |

## Frontend Sections

1. **Input**: Task input textarea + Route button
2. **Step 1 - Analyze**: Shows detected capabilities with animation
3. **Step 2 - Discover**: Shows registry search, matching agents highlighted
4. **Step 3 - Execute**: Shows each agent executing with results
5. **Registry Panel**: Live view of all registered agents
6. **Results**: Aggregated final output

## Implementation Phases

### Phase 1: Models & Base
- [ ] `agents/router/models.py` - Pydantic models
- [ ] Tests for models

### Phase 2: Analyzer Agent
- [ ] `agents/router/analyzer.py` - LLM capability extraction
- [ ] Unit tests with mocked LLM

### Phase 3: Executor
- [ ] `agents/router/executor.py` - Task execution
- [ ] Integration tests

### Phase 4: Router Orchestrator
- [ ] `agents/router/router.py` - SmartRouter
- [ ] SSE event emission
- [ ] Integration tests

### Phase 5: API
- [ ] `protocol/router_api.py` - FastAPI endpoints
- [ ] E2E tests

### Phase 6: Frontend
- [ ] `static/router/index.html`
- [ ] `static/router/app.js`
- [ ] `static/router/style.css`

### Phase 7: Documentation
- [ ] `docs/software-architecture/router-pattern.md`

## Educational Points

1. **Registry as Service Discovery**: Come trovare agenti dinamicamente
2. **Capability-based Routing**: Matching task → agent
3. **LLM for Task Analysis**: AI che capisce cosa serve
4. **Loose Coupling**: Agenti indipendenti, registry li connette
5. **Dynamic Composition**: Diversi agenti per diversi task
