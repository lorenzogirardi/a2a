# Platform Architecture

## Deployment Overview

```mermaid
graph TB
    subgraph "Docker Compose"
        subgraph "a2a-app"
            API[FastAPI :8000]
            MCP[FastMCP]
            SSE[SSE Handler]
        end

        subgraph "a2a-postgres"
            PG[(PostgreSQL :5432)]
        end
    end

    CLIENT[Clients] --> API
    API --> PG
```

## Container Architecture

```mermaid
graph LR
    subgraph "a2a-app"
        direction TB
        PY[Python 3.12-slim]
        UV[Uvicorn]
        FA[FastAPI App]
        PY --> UV --> FA
    end

    subgraph "a2a-postgres"
        direction TB
        PGA[PostgreSQL 16 Alpine]
        DATA[(Data Volume)]
        PGA --> DATA
    end

    a2a-app -->|DATABASE_URL| a2a-postgres
```

## Docker Compose Services

| Service | Image | Ports | Health Check |
|---------|-------|-------|--------------|
| `app` | `a2a-app` (built) | 8000 | `curl /health` |
| `postgres` | `postgres:16-alpine` | 5432 | `pg_isready` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | API bind address |
| `PORT` | `8000` | API port |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | - | Claude API key (for LLM agents) |

## Database Schema

```mermaid
erDiagram
    conversations {
        varchar id PK
        text[] participants
        timestamp created_at
    }

    messages {
        varchar id PK
        varchar conversation_id FK
        varchar sender
        varchar receiver
        text content
        timestamp timestamp
        jsonb metadata
    }

    agent_states {
        varchar agent_id PK
        jsonb state
        timestamp updated_at
    }

    conversations ||--o{ messages : contains
```

## Network Flow

```mermaid
flowchart LR
    subgraph External
        C[Client]
    end

    subgraph Docker Network
        A[a2a-app:8000]
        P[postgres:5432]
    end

    C -->|HTTP/SSE| A
    A -->|asyncpg| P
```

## Startup Sequence

```mermaid
sequenceDiagram
    participant DC as docker-compose
    participant PG as postgres
    participant APP as app

    DC->>PG: Start postgres
    PG->>PG: Run init-db.sql
    PG-->>DC: Healthy

    DC->>APP: Start app
    APP->>APP: Install dependencies
    APP->>APP: Start uvicorn
    APP->>PG: Connect (pool)
    APP-->>DC: Healthy
```

## Operations

### Start

```bash
docker-compose up -d
```

### Logs

```bash
docker-compose logs -f app
docker-compose logs -f postgres
```

### Stop

```bash
docker-compose down
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

## Monitoring

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | App health + agent count |
| `GET /sse/status` | SSE connection count |

### Logs

```bash
# All logs
docker-compose logs

# Follow app logs
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100
```

## Security

### Network Isolation

- PostgreSQL not exposed externally (internal Docker network)
- App exposes only port 8000

### Authentication

- Role-based access (Admin, User, Guest)
- CallerContext required for all operations
- Permission decorators on sensitive methods

### Secrets

| Secret | Storage | Usage |
|--------|---------|-------|
| `POSTGRES_PASSWORD` | docker-compose.yml | DB access |
| `ANTHROPIC_API_KEY` | Environment | Claude API |

## Scaling Considerations

### Current (Single Node)

```
docker-compose up -d
```

### Future (Multi-Node)

```mermaid
graph TB
    LB[Load Balancer]
    LB --> A1[app-1]
    LB --> A2[app-2]
    LB --> A3[app-3]
    A1 --> PG[(PostgreSQL)]
    A2 --> PG
    A3 --> PG
```

Requirements for scaling:
- Shared PostgreSQL (already supported)
- Session affinity for SSE connections
- Distributed agent state (Redis/PostgreSQL)
