# Software Architecture

## System Overview

```mermaid
graph TB
    subgraph "Clients"
        CLI[Claude CLI]
        WEB[Web Browser]
        APP[Applications]
    end

    subgraph "Protocol Layer"
        MCP[FastMCP Server]
        API[FastAPI REST]
        SSE[SSE Transport]
    end

    subgraph "Agent Layer"
        REG[Agent Registry]
        ECHO[EchoAgent]
        CALC[CalculatorAgent]
        LLM[LLMAgent]
        ORCH[OrchestratorAgent]
        CHAIN_P[ChainPipeline]
    end

    subgraph "Storage Layer"
        MEM[MemoryStorage]
        FILE[FileStorage]
        PG[PostgresStorage]
    end

    CLI --> MCP
    WEB --> API
    WEB --> SSE
    APP --> API

    MCP --> REG
    API --> REG
    SSE --> REG

    REG --> ECHO
    REG --> CALC
    REG --> LLM
    REG --> ORCH

    ECHO --> MEM
    CALC --> MEM
    LLM --> PG
    ORCH --> PG
```

## Component Diagram

```mermaid
graph LR
    subgraph "agents/"
        BASE[base.py<br/>AgentBase]
        SIMPLE[simple_agent.py<br/>Echo, Counter, Router]
        LLMA[llm_agent.py<br/>LLMAgent, ToolUsingLLMAgent]
        RESEARCH[research/<br/>Orchestrator, Search agents]
        CHAIN[chain/<br/>Writer, Editor, Publisher]
        REGISTRY[registry.py<br/>AgentRegistry]
    end

    subgraph "storage/"
        SBASE[base.py<br/>StorageBase]
        SMEM[memory.py<br/>MemoryStorage]
        SFILE[file.py<br/>FileStorage]
        SPG[postgres.py<br/>PostgresStorage]
    end

    subgraph "protocol/"
        PMCP[mcp_server.py<br/>FastMCP]
        PAPI[api.py<br/>FastAPI]
        PSSE[sse.py<br/>SSE Transport]
    end

    subgraph "auth/"
        AUTH[permissions.py<br/>Role, Permission, CallerContext]
    end

    SIMPLE --> BASE
    LLMA --> BASE
    RESEARCH --> BASE

    SMEM --> SBASE
    SFILE --> SBASE
    SPG --> SBASE

    PAPI --> PMCP
    PSSE --> PAPI

    BASE --> SBASE
    BASE --> AUTH
```

## Agent Pattern

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Agent
    participant S as Storage

    C->>A: receive_message(ctx, content)
    A->>S: get_state(agent_id)
    S-->>A: state
    A->>A: think(message)
    Note over A: Decide response & actions
    A->>A: act(actions)
    Note over A: Execute actions
    A->>S: save_message(message)
    A->>S: save_agent_state(state)
    A-->>C: AgentResponse
```

## Research Orchestration (Fan-out/Fan-in)

```mermaid
sequenceDiagram
    participant C as Client
    participant O as Orchestrator
    participant W as WebSearch
    participant D as DocSearch
    participant X as CodeSearch
    participant M as MergeAgent

    C->>O: research(query)

    par Parallel Search
        O->>W: search(query)
        O->>D: search(query)
        O->>X: search(query)
    end

    W-->>O: web_results
    D-->>O: doc_results
    X-->>O: code_results

    O->>M: merge_results(all_results)
    M-->>O: AggregatedResult

    O-->>C: AggregatedResult
```

## Chain Pipeline (Sequential Processing)

See: [chain-pattern.md](./chain-pattern.md)

## Smart Task Router (Capability-Based Discovery)

See: [router-pattern.md](./router-pattern.md)

```mermaid
sequenceDiagram
    participant C as Client
    participant R as SmartRouter
    participant A as AnalyzerAgent
    participant Reg as AgentRegistry
    participant E as TaskExecutor
    participant Ag as Matched Agents

    C->>R: route(task)
    R->>A: analyze(task)
    A-->>R: {capabilities, subtasks}

    loop For each capability
        R->>Reg: find_by_capability(cap)
        Reg-->>R: matched_agents[]
    end

    R->>E: execute_all(matches, subtasks)

    loop For each match
        E->>Ag: receive_message(subtask)
        Ag-->>E: result
    end

    E-->>R: execution_results[]
    R-->>C: RouterResult
```

**Key Features:**
- LLM-based task analysis
- Registry for dynamic agent discovery
- Capability-based matching
- Parallel execution of subtasks

```mermaid
sequenceDiagram
    participant C as Client
    participant P as Pipeline
    participant W as Writer
    participant E as Editor
    participant Pub as Publisher
    participant UI as Browser

    C->>P: run(prompt)
    P-->>UI: SSE: pipeline_started

    P->>W: transform(prompt)
    P-->>UI: SSE: step_started(writer)
    W-->>P: draft_text
    P-->>UI: SSE: step_completed(writer, tokens)
    P-->>UI: SSE: message_passed(writer→editor)

    P->>E: transform(draft_text)
    P-->>UI: SSE: step_started(editor)
    E-->>P: edited_text
    P-->>UI: SSE: step_completed(editor, tokens)
    P-->>UI: SSE: message_passed(editor→publisher)

    P->>Pub: transform(edited_text)
    P-->>UI: SSE: step_started(publisher)
    Pub-->>P: final_text
    P-->>UI: SSE: step_completed(publisher, tokens)

    P-->>UI: SSE: pipeline_completed
    P-->>UI: SSE: result
    P-->>C: PipelineResult
```

**Key Features:**
- Sequential agent execution with SSE events
- Token tracking per step (via LiteLLM)
- KPI dashboard: duration, tokens, cost
- Agent communication visualization
- Real-time UI updates

## Storage Abstraction

```mermaid
classDiagram
    class StorageBase {
        <<abstract>>
        +save_message(message)
        +get_messages(conversation_id)
        +get_agent_state(agent_id)
        +save_agent_state(agent_id, state)
        +create_conversation(participants)
    }

    class MemoryStorage {
        -_conversations: dict
        -_agent_states: dict
    }

    class FileStorage {
        -base_path: Path
        -_lock: asyncio.Lock
    }

    class PostgresStorage {
        -_pool: asyncpg.Pool
        -_connection_url: str
    }

    StorageBase <|-- MemoryStorage
    StorageBase <|-- FileStorage
    StorageBase <|-- PostgresStorage
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/{id}` | Get agent info |
| POST | `/api/agents/{id}/message` | Send message |
| GET | `/api/agents/{id}/state` | Get agent state |
| GET | `/api/research?q=...` | Research query |
| GET | `/sse/events` | SSE stream |
| POST | `/sse/call` | Call tool via SSE |
| POST | `/api/chain/run` | Start chain pipeline |
| GET | `/api/chain/status/{id}` | Get pipeline status |
| GET | `/api/chain/agents` | List chain agents |
| GET | `/api/chain/events/{id}` | SSE events stream |
| GET | `/static/chain/` | Chain demo webpage |
| POST | `/api/router/route` | Route task to agents |
| GET | `/api/router/status/{id}` | Get routing status |
| GET | `/api/router/registry` | List registered agents |
| GET | `/api/router/events/{id}` | SSE events stream |
| GET | `/static/router/` | Router demo webpage |

## Error Handling

```mermaid
flowchart TD
    REQ[Request] --> AUTH{Auth Check}
    AUTH -->|Denied| E403[403 Forbidden]
    AUTH -->|OK| AGENT{Agent Exists?}
    AGENT -->|No| E404[404 Not Found]
    AGENT -->|Yes| EXEC[Execute]
    EXEC -->|Error| E500[500 Error]
    EXEC -->|OK| R200[200 Response]
```
