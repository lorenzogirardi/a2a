# Tasks: Research Assistant

**Spec**: ./research-assistant.md
**Created**: 2026-02-01
**Status**: PENDING

---

## Context

Implementare un Research Assistant multi-agente con:
- OrchestratorAgent per coordinamento
- 3 SearchAgent paralleli (web, docs, code)
- MergeAgent per aggregazione risultati
- Mock data per focus su pattern architetturali

---

## Prerequisites

- [x] Struttura progetto base funzionante
- [x] FastMCP + FastAPI configurati
- [x] Test pyramid in place

---

## Tasks

### Phase 1: Foundation - Models e Base

- [ ] **Task 1**: Creare modelli Pydantic per risultati
  - Acceptance: `SearchResult` e `AggregatedResult` in `agents/research/models.py`
  - Files: `agents/research/__init__.py`, `agents/research/models.py`

- [ ] **Task 2**: Creare SearchAgent base class
  - Acceptance: Classe astratta con metodo `search(query) -> list[SearchResult]`
  - Files: `agents/research/base.py`

### Phase 2: Search Agents

- [ ] **Task 3**: Implementare WebSearchAgent (mock)
  - Acceptance: Ritorna risultati mock per query
  - Files: `agents/research/web_search.py`

- [ ] **Task 4**: Implementare DocSearchAgent (mock)
  - Acceptance: Ritorna risultati mock da "documentazione"
  - Files: `agents/research/doc_search.py`

- [ ] **Task 5**: Implementare CodeSearchAgent (mock)
  - Acceptance: Ritorna risultati mock da "codice"
  - Files: `agents/research/code_search.py`

### Phase 3: Orchestration

- [ ] **Task 6**: Implementare MergeAgent
  - Acceptance: Aggrega risultati, ordina per relevance, genera summary
  - Files: `agents/research/merge.py`

- [ ] **Task 7**: Implementare OrchestratorAgent
  - Acceptance: Dispatch parallelo, timeout handling, chiama MergeAgent
  - Files: `agents/research/orchestrator.py`

### Phase 4: Protocol Integration

- [ ] **Task 8**: Aggiungere endpoint FastAPI per research
  - Acceptance: `GET /api/research?q=...` funziona
  - Files: `protocol/api.py`

- [ ] **Task 9**: Aggiungere MCP tool per research
  - Acceptance: Tool `research(query)` disponibile
  - Files: `protocol/mcp_server.py`

### Phase 5: Tests

- [ ] **Task 10**: Unit tests per search agents
  - Acceptance: Test per WebSearch, DocSearch, CodeSearch
  - Files: `tests/unit/test_research_agents.py`

- [ ] **Task 11**: Integration test per orchestrazione
  - Acceptance: Test end-to-end della pipeline
  - Files: `tests/integration/test_research_pipeline.py`

---

## Completion Checklist

- [ ] All tasks marked complete
- [ ] All tests passing (`pytest`)
- [ ] Spec acceptance criteria met
- [ ] `status.md` updated
- [ ] Committed and pushed

---

## Notes

*Space for execution notes during implementation*
