# LangGraph Execution: Esempio Dettagliato

> **Task**: "Avendo budget di 30000 dollari al mese, e dovendo costruire un piccolo team di ecommerce come andrebbe composto il team tecnico"

Questo documento illustra il flusso completo di esecuzione del sistema LangGraph, mostrando come una richiesta complessa viene scomposta, distribuita a più agenti specializzati, e infine sintetizzata in una risposta coerente.

---

## Overview del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER TASK                                       │
│  "avendo budget di 30000 dollari al mese, e dovendo costruire un piccolo    │
│   team di ecommerce come andrebbe composto il team tecnico"                 │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LANGGRAPH STATEGRAPH                                │
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────────────────────────────┐    │
│   │ ANALYZE  │────▶│ DISCOVER │────▶│           EXECUTE                │    │
│   │  (LLM)   │     │(Registry)│     │        (Parallel)                │    │
│   └──────────┘     └──────────┘     │  ┌─────────┐ ┌─────────┐ ┌─────┐│    │
│        │                            │  │Analyst  │ │Estimator│ │Resea││    │
│        │                            │  └────┬────┘ └────┬────┘ └──┬──┘│    │
│        ▼                            └───────┼──────────┼─────────┼───┘    │
│   ┌──────────┐                              │          │         │        │
│   │analysis  │                              └──────────┼─────────┘        │
│   │estimation│                                         │                  │
│   │research  │                                         ▼                  │
│   └──────────┘                              ┌──────────────────┐          │
│                                             │    SYNTHESIZE    │          │
│                                             │      (LLM)       │          │
│                                             └────────┬─────────┘          │
└──────────────────────────────────────────────────────┼──────────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │  FINAL OUTPUT  │
                                              └────────────────┘
```

---

## Fase 1: ANALYZE (Analisi del Task)

**Durata**: 4,100ms
**Nodo**: `analyze`
**Agente**: AnalyzerAgent (LLM-based)

### Cosa Succede

L'AnalyzerAgent riceve il task in linguaggio naturale e usa Claude per:

1. **Identificare le capabilities necessarie** (competenze richieste)
2. **Scomporre il task in subtask** specifici per ogni capability
3. **Determinare eventuali dipendenze** tra i subtask

### Input
```
"avendo budget di 30000 dollari al mese, e dovendo costruire
un piccolo team di ecommerce come andrebbe composto il team tecnico"
```

### Output dell'Analyzer
```json
{
  "detected_capabilities": ["analysis", "estimation", "research"],
  "subtasks": {
    "analysis": "Analizza i ruoli tecnici necessari per un team ecommerce
                e le priorità in base alle esigenze operative",
    "estimation": "Stima i costi mensili per ciascun ruolo tecnico
                  considerando il budget di 30000 dollari",
    "research": "Fornisci informazioni sui ruoli tecnici standard
                in un team ecommerce e le competenze richieste"
  },
  "dependencies": null
}
```

### Eventi SSE Generati

```
event: graph_update
data: {"action": "add_node", "node": {"id": "analyze", "label": "Analyzer", "state": "running"}}

event: graph_update
data: {"action": "update_node", "node": {"id": "analyze", "state": "completed", "duration_ms": 4100}}

event: graph_update
data: {"action": "add_node", "node": {"id": "cap_analysis", "label": "analysis", "type": "capability"}}

event: graph_update
data: {"action": "add_node", "node": {"id": "cap_estimation", "label": "estimation", "type": "capability"}}

event: graph_update
data: {"action": "add_node", "node": {"id": "cap_research", "label": "research", "type": "capability"}}
```

### Visualizzazione Grafo (dopo Fase 1)

```
        ┌──────────────┐
        │   Analyzer   │ ← COMPLETED (verde)
        │   (4.1s)     │
        └──────┬───────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ analysis │ │estimation│ │ research │  ← PENDING (grigio)
└──────────┘ └──────────┘ └──────────┘
```

---

## Fase 2: DISCOVER (Scoperta Agenti)

**Durata**: <1ms
**Nodo**: `discover`
**Componente**: AgentRegistry

### Cosa Succede

Il Discovery Node interroga l'AgentRegistry per trovare agenti che possono soddisfare ciascuna capability rilevata:

```python
# Per ogni capability, cerca agenti compatibili
for capability in ["analysis", "estimation", "research"]:
    agents = registry.find_by_capability(capability)
```

### Matching Risultato

| Capability | Agenti Trovati | Match |
|------------|---------------|-------|
| `analysis` | `analyst` (Analysis Agent) | ✅ |
| `estimation` | `estimator` (Estimation Agent) | ✅ |
| `research` | `researcher` (Research Agent) | ✅ |

### Eventi SSE Generati

```
event: graph_update
data: {"action": "add_node", "node": {"id": "discover", "label": "Discovery", "state": "running"}}

event: graph_update
data: {"action": "update_node", "node": {"id": "cap_analysis", "state": "matched", "agents": ["analyst"]}}

event: graph_update
data: {"action": "add_node", "node": {"id": "agent_analyst", "label": "Analysis Agent", "type": "agent"}}

event: graph_update
data: {"action": "add_edge", "edge": {"from": "cap_analysis", "to": "agent_analyst"}}

// ... ripetuto per estimation e research ...

event: graph_update
data: {"action": "update_node", "node": {"id": "discover", "state": "completed"}}
```

### Visualizzazione Grafo (dopo Fase 2)

```
                    ┌──────────────┐
                    │   Analyzer   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ analysis │ │estimation│ │ research │  ← MATCHED (blu)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Analyst  │ │Estimator │ │Researcher│  ← PENDING (grigio)
        │  Agent   │ │  Agent   │ │  Agent   │
        └──────────┘ └──────────┘ └──────────┘
                           │
                    ┌──────────────┐
                    │   Discovery  │ ← COMPLETED
                    └──────────────┘
```

---

## Fase 3: EXECUTE (Esecuzione Parallela)

**Durata Totale**: ~15,120ms (tempo massimo tra i 3 agenti)
**Nodo**: `execute`
**Pattern**: Fan-out parallelo

### Cosa Succede

Il TaskExecutor lancia **simultaneamente** i 3 agenti specializzati:

```python
# Esecuzione parallela con asyncio.gather
results = await asyncio.gather(
    analyst.execute(subtask_analysis),
    estimator.execute(subtask_estimation),
    researcher.execute(subtask_research)
)
```

### Dettaglio Esecuzioni

#### 1. Analysis Agent
- **Input**: "Analizza i ruoli tecnici necessari per un team ecommerce e le priorità..."
- **Durata**: 14,912ms
- **Token**: 110 input, 1024 output
- **Output**: Analisi dettagliata dei ruoli (Tier 1, Tier 2, Tier 3) con pro/contro e KPI

#### 2. Estimation Agent
- **Input**: "Stima i costi mensili per ciascun ruolo tecnico considerando il budget..."
- **Durata**: 12,280ms
- **Token**: 155 input, 1024 output
- **Output**: Tabella costi con distribuzione percentuale del budget

#### 3. Research Agent
- **Input**: "Fornisci informazioni sui ruoli tecnici standard in un team ecommerce..."
- **Durata**: 15,120ms
- **Token**: 124 input, 1024 output
- **Output**: Lista completa ruoli con competenze tecniche richieste

### Timeline Esecuzione Parallela

```
T=0ms      T=12,280ms   T=14,912ms   T=15,120ms
│          │            │            │
├──────────┼────────────┼────────────┤
│  Estimator ──────────▶│            │
├──────────┼────────────┼────────────┤
│     Analyst ─────────────────────▶ │
├──────────┼────────────┼────────────┤
│    Researcher ───────────────────────▶
├──────────┼────────────┼────────────┤

Tempo totale: 15,120ms (non 42,312ms se fossero sequenziali!)
Risparmio: ~64% del tempo
```

### Eventi SSE Generati

```
event: graph_update
data: {"action": "add_node", "node": {"id": "execute", "label": "Executor", "state": "running"}}

// Quando ogni agente completa:
event: graph_update
data: {"action": "update_node", "node": {"id": "agent_analyst", "state": "completed", "duration_ms": 14912}}

event: graph_update
data: {"action": "update_node", "node": {"id": "agent_estimator", "state": "completed", "duration_ms": 12280}}

event: graph_update
data: {"action": "update_node", "node": {"id": "agent_researcher", "state": "completed", "duration_ms": 15120}}

event: graph_update
data: {"action": "update_node", "node": {"id": "execute", "state": "completed"}}
```

### Visualizzazione Grafo (dopo Fase 3)

```
                    ┌──────────────┐
                    │   Analyzer   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ analysis │ │estimation│ │ research │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Analyst  │ │Estimator │ │Researcher│  ← COMPLETED (verde)
        │ (14.9s)  │ │ (12.3s)  │ │ (15.1s)  │
        └──────────┘ └──────────┘ └──────────┘
```

---

## Fase 4: Decisione Condizionale

**Funzione**: `should_synthesize(state)`

### Logica

```python
def should_synthesize(state: GraphState) -> str:
    """Decide se sintetizzare o terminare."""
    successful = [e for e in state["executions"] if e.get("success")]

    if len(successful) > 1:
        return "synthesize"  # → vai al nodo synthesize
    else:
        return "end"         # → vai direttamente a END
```

### Risultato in questo caso

- Esecuzioni successful: **3** (analyst, estimator, researcher)
- Condizione `len(successful) > 1`: **True**
- **Decisione**: → `"synthesize"`

---

## Fase 5: SYNTHESIZE (Sintesi Finale)

**Durata**: 13,000ms
**Nodo**: `synthesize`
**Agente**: SynthesizerAgent (LLM-based)

### Cosa Succede

Il SynthesizerAgent riceve tutti gli output dei 3 agenti e li integra in una risposta coerente:

```python
synthesis_prompt = f"""
Integra le seguenti risposte di agenti specializzati in una risposta
unificata e coerente.

Task originale: {original_task}

RISPOSTA ANALYST:
{analyst_output}

RISPOSTA ESTIMATOR:
{estimator_output}

RISPOSTA RESEARCHER:
{researcher_output}

Crea una sintesi che:
1. Combini le informazioni senza ripetizioni
2. Risolva eventuali contraddizioni
3. Mantenga la struttura più utile
4. Fornisca una risposta completa e actionable
"""
```

### Output Sintetizzato

Il Synthesizer produce un documento strutturato che:

1. **Unifica** la composizione del team (da Analyst + Estimator)
2. **Integra** i costi specifici (da Estimator)
3. **Aggiunge** competenze tecniche dettagliate (da Researcher)
4. **Organizza** in sezioni logiche (Configurazione, Timeline, KPI)

### Eventi SSE Generati

```
event: graph_update
data: {"action": "add_node", "node": {"id": "synthesize", "label": "Synthesizer", "state": "running"}}

event: graph_update
data: {"action": "add_edge", "edge": {"from": "agent_analyst", "to": "synthesize"}}

event: graph_update
data: {"action": "add_edge", "edge": {"from": "agent_estimator", "to": "synthesize"}}

event: graph_update
data: {"action": "add_edge", "edge": {"from": "agent_researcher", "to": "synthesize"}}

event: graph_update
data: {"action": "update_node", "node": {"id": "synthesize", "state": "completed", "duration_ms": 13000}}
```

### Visualizzazione Grafo Finale

```
                    ┌──────────────┐
                    │   Analyzer   │ COMPLETED
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ analysis │ │estimation│ │ research │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Analyst  │ │Estimator │ │Researcher│ COMPLETED
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             └────────────┼────────────┘
                          ▼
                   ┌─────────────┐
                   │ Synthesizer │ COMPLETED
                   │   (13s)     │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   OUTPUT    │
                   └─────────────┘
```

---

## Riepilogo Temporale

| Fase | Nodo | Durata | Note |
|------|------|--------|------|
| 1 | Analyze | 4,100ms | LLM decomposition |
| 2 | Discover | <1ms | Registry lookup |
| 3 | Execute | 15,120ms | 3 agenti in parallelo |
| 4 | Condition | <1ms | Routing decision |
| 5 | Synthesize | 13,000ms | LLM integration |
| | **TOTALE** | **~59,446ms** | |

### Confronto con Esecuzione Sequenziale

```
Parallelo:   4.1s + 0s + 15.1s + 0s + 13s = ~32.2s effettivi
Sequenziale: 4.1s + 0s + (14.9 + 12.3 + 15.1)s + 0s + 13s = ~59.4s

Nota: Il tempo totale include overhead di comunicazione e serializzazione.
```

---

## Struttura del Codice

### State (TypedDict)

```python
# agents/graph/state.py
class GraphState(TypedDict):
    task_id: str
    original_task: str
    detected_capabilities: Annotated[list[str], operator.add]
    subtasks: dict[str, str]
    dependencies: Optional[dict[str, list[str]]]
    matches: list[dict[str, Any]]
    executions: Annotated[list[dict[str, Any]], operator.add]
    synthesis: Optional[dict[str, Any]]
    final_output: str
    status: str
    graph_data: dict[str, Any]
```

### Graph Builder

```python
# agents/graph/graph.py
def build_router_graph() -> CompiledStateGraph:
    graph = StateGraph(GraphState)

    # Nodi
    graph.add_node("analyze", analyze_node)
    graph.add_node("discover", discover_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    # Edges
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "discover")
    graph.add_edge("discover", "execute")

    # Conditional edge
    graph.add_conditional_edges(
        "execute",
        should_synthesize,
        {"synthesize": "synthesize", "end": END}
    )

    graph.add_edge("synthesize", END)

    return graph.compile()
```

---

## Output Finale

Il sistema produce una risposta completa e strutturata:

```markdown
# Composizione Team Tecnico E-commerce con Budget $30,000/mese

## COMPOSIZIONE TEAM RACCOMANDATA

### Configurazione Ottimale (5 persone)

| Ruolo | Allocazione Budget | Responsabilità |
|-------|-------------------|----------------|
| Senior Full-Stack Developer (Lead) | $10,000/mese (33%) | Architettura, sviluppo, integrazioni |
| Mid-Level Frontend Developer | $6,000/mese (20%) | UI/UX, React/Next.js |
| Junior Backend Developer | $4,500/mese (15%) | API, database |
| QA Engineer | $5,000/mese (17%) | Test automation, CI/CD |
| DevOps Specialist (Part-time) | $4,500/mese (15%) | Cloud, monitoring |

**TOTALE: $30,000/mese**

## PRIORITÀ DI ASSUNZIONE

**FASE 1 (Mese 1-2):** Senior Full-Stack + Mid Frontend + QA
**FASE 2 (Mese 3-6):** Junior Backend + DevOps
**FASE 3 (dopo 12 mesi):** Product Manager, Data Analyst, UX Designer
```

---

## Conclusioni

Il sistema LangGraph dimostra:

1. **Decomposizione Intelligente**: Un task complesso viene automaticamente scomposto in subtask specializzati
2. **Discovery Dinamico**: Gli agenti vengono selezionati in base alle capabilities richieste
3. **Esecuzione Parallela**: Massima efficienza temporale con fan-out pattern
4. **Sintesi Coerente**: Output multipli vengono integrati in una risposta unificata
5. **Tracciabilità Completa**: Ogni step è visualizzato in tempo reale nel grafo

### Link Correlati

- [LangGraph Pattern](./langgraph-pattern.md)
- [Router Pattern](./router-pattern.md)
- [Chain Pattern](./chain-pattern.md)
