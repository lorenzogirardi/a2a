# A2A Documentation

Agent-to-Agent communication and orchestration framework.

## Quick Links

| I want to... | Go to |
|--------------|-------|
| Understand the business context | [Enterprise Architecture](enterprise-architecture/) |
| See how components work | [Software Architecture](software-architecture/) |
| Deploy and operate | [Platform Architecture](platform-architecture/) |

## Architecture Overview

```mermaid
graph TB
    subgraph "Enterprise"
        BC[Business Capabilities]
        DM[Domain Model]
    end

    subgraph "Software"
        AG[Agents]
        ST[Storage]
        PR[Protocol]
    end

    subgraph "Platform"
        DC[Docker]
        PG[PostgreSQL]
        MO[Monitoring]
    end

    BC --> AG
    DM --> ST
    AG --> DC
    ST --> PG
    PR --> MO
```

## Structure

```
docs/
├── enterprise-architecture/
│   ├── README.md          # Business capabilities, domain model
│   └── adr/               # Architecture Decision Records
├── software-architecture/
│   └── README.md          # Components, patterns, APIs
└── platform-architecture/
    └── README.md          # Docker, database, operations
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Agent** | Autonomous unit that receives messages, thinks, acts, responds |
| **Storage** | Pluggable persistence (Memory, File, PostgreSQL) |
| **Protocol** | Communication layer (MCP, REST, SSE) |
| **CallerContext** | Identity and permissions of the caller |

## Getting Started

```bash
# Start the system
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Try research API
curl "http://localhost:8000/api/research?q=python"
```
