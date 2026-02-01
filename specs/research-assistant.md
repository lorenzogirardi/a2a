# Spec: Research Assistant

**Status**: DRAFT
**Created**: 2026-02-01
**Last Updated**: 2026-02-01

---

## 1. Objective

Implementare un sistema di ricerca multi-agente che:
- Riceve una query di ricerca
- Lancia ricerche parallele su fonti diverse (web, documenti, codice)
- Aggrega i risultati in una risposta unificata
- Dimostra pattern di orchestrazione e parallelismo

---

## 2. Requirements

### Functional Requirements

- [ ] FR1: OrchestratorAgent riceve query e coordina gli altri agenti
- [ ] FR2: Almeno 3 agenti di ricerca specializzati (WebSearch, DocSearch, CodeSearch)
- [ ] FR3: MergeAgent aggrega i risultati in formato unificato
- [ ] FR4: Risultati devono includere fonte, relevance score, contenuto
- [ ] FR5: Timeout per agenti lenti (non bloccare il sistema)

### Non-Functional Requirements

- [ ] NFR1: Ricerche parallele (non sequenziali)
- [ ] NFR2: Risposta aggregata in < 5s (mock)
- [ ] NFR3: Graceful handling se un agente fallisce

### Out of Scope

- Integrazione reale con API di ricerca (useremo mock)
- LLM per sintesi (useremo template semplici)
- UI/Frontend

---

## 3. Technical Strategy

### Affected Modules

- **Agents**: Nuovi agenti specializzati in `agents/research/`
- **Storage**: Nessuna modifica (usa MemoryStorage)
- **Protocol**: Esporre via FastMCP + FastAPI

### Nuovi Agenti

```
agents/research/
├── __init__.py
├── orchestrator.py    # OrchestratorAgent
├── web_search.py      # WebSearchAgent (mock)
├── doc_search.py      # DocSearchAgent (mock)
├── code_search.py     # CodeSearchAgent (mock)
└── merge.py           # MergeAgent
```

### Data Flow

```
                    ┌─────────────────┐
                    │ OrchestratorAgent│
                    └────────┬────────┘
                             │ dispatch (parallel)
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │WebSearchAgent│ │DocSearchAgent│ │CodeSearchAgent│
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             ▼
                    ┌─────────────────┐
                    │   MergeAgent    │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │  Final Response │
                    └─────────────────┘
```

### Result Schema

```python
class SearchResult(BaseModel):
    source: str           # "web" | "docs" | "code"
    title: str
    content: str
    url: Optional[str]
    relevance: float      # 0.0 - 1.0
    metadata: dict = {}

class AggregatedResult(BaseModel):
    query: str
    results: list[SearchResult]
    summary: str
    search_time_ms: int
    sources_searched: list[str]
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Parallel execution | asyncio.gather | Semplice, built-in Python |
| Mock data | Risposte predefinite | Focus su pattern, non API reali |
| Timeout | asyncio.wait_for | Evita blocchi da agenti lenti |
| Result format | Pydantic models | Validazione, serializzazione |

---

## 4. Acceptance Criteria

- [ ] AC1: Query "python async" ritorna risultati da tutte e 3 le fonti
- [ ] AC2: Risultati sono ordinati per relevance
- [ ] AC3: Se un agente fallisce, gli altri continuano
- [ ] AC4: API FastAPI `/api/research?q=...` funziona
- [ ] AC5: MCP tool `research` funziona
- [ ] AC6: Test unitari per ogni agente
- [ ] AC7: Test integrazione per orchestrazione

---

## 5. Open Questions

Nessuna domanda aperta - scope definito con mock.

---

## 6. References

- Pattern: [Fan-out/Fan-in](https://www.enterpriseintegrationpatterns.com/patterns/messaging/BroadcastAggregate.html)
- asyncio.gather: [Python docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- Codice esistente: `agents/simple_agent.py` per pattern agente
