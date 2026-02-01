# Enterprise Architecture

## Overview

A2A (Agent-to-Agent) è un framework per la comunicazione e orchestrazione di agenti AI.

## Business Capabilities

```mermaid
graph TB
    subgraph "Core Capabilities"
        AC[Agent Communication]
        AO[Agent Orchestration]
        AD[Agent Discovery]
    end

    subgraph "Supporting Capabilities"
        ST[State Management]
        AU[Authentication & Authorization]
        MO[Monitoring & Observability]
    end

    subgraph "Integration Capabilities"
        MCP[MCP Protocol]
        REST[REST API]
        SSE[Real-time Events]
    end

    AC --> ST
    AO --> AC
    AD --> AC
    MCP --> AC
    REST --> AC
    SSE --> AC
    AU --> AC
```

## Domain Model

```mermaid
classDiagram
    class Agent {
        +id: string
        +name: string
        +capabilities: list
        +receive_message()
        +get_state()
    }

    class Message {
        +id: string
        +sender: string
        +receiver: string
        +content: string
        +timestamp: datetime
    }

    class Conversation {
        +id: string
        +participants: list
        +messages: list
    }

    class CallerContext {
        +caller_id: string
        +role: Role
        +permissions: list
    }

    Agent "1" --> "*" Message : sends
    Agent "1" --> "*" Message : receives
    Conversation "1" --> "*" Message : contains
    Agent "*" --> "1" CallerContext : requires
```

## Stakeholders

| Stakeholder | Concerns | How Addressed |
|-------------|----------|---------------|
| Developers | Easy agent creation | Simple base class, decorators |
| Operators | Deployment, monitoring | Docker, health endpoints |
| Security | Access control | Role-based permissions |
| Integrators | Protocol compatibility | MCP, REST, SSE support |

## Strategic Decisions

See [ADR-001: Agent Pattern](adr/001-agent-pattern.md)
