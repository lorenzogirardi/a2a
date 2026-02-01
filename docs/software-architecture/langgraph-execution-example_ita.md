# LangGraph Execution: Esempio Dettagliato

> **Task**: "Avendo budget di 30000 dollari al mese, e dovendo costruire un piccolo team di ecommerce come andrebbe composto il team tecnico"

Questo documento illustra il flusso completo di esecuzione del sistema LangGraph, mostrando come una richiesta complessa viene scomposta, distribuita a più agenti specializzati, e infine sintetizzata in una risposta coerente.

## Demo Video

[![Demo LangGraph Execution](https://res.cloudinary.com/ethzero/video/upload/so_3,w_800/v1769976053/ai/a2a/agent-discovery-graph.jpg)](https://res.cloudinary.com/ethzero/video/upload/v1769976053/ai/a2a/agent-discovery-graph.mp4)

*Clicca sull'immagine per vedere il video dell'esecuzione in tempo reale*

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

## Comunicazione tra Nodi: Lo State

I nodi LangGraph **non comunicano direttamente tra loro**. Ogni nodo riceve lo stato corrente, lo modifica, e passa lo stato aggiornato al nodo successivo.

```python
# agents/graph/state.py
class GraphState(TypedDict):
    # Input iniziale
    task_id: str
    original_task: str

    # Output di ANALYZE → Input di DISCOVER
    detected_capabilities: Annotated[list[str], operator.add]
    subtasks: dict[str, str]  # capability → subtask description
    dependencies: Optional[dict[str, list[str]]]

    # Output di DISCOVER → Input di EXECUTE
    matches: list[dict[str, Any]]  # capability → agent_ids

    # Output di EXECUTE → Input di SYNTHESIZE
    executions: Annotated[list[dict[str, Any]], operator.add]

    # Output di SYNTHESIZE
    synthesis: Optional[dict[str, Any]]
    final_output: str
    status: str
```

### Flusso dello State

```
┌─────────────┐    state["original_task"]     ┌─────────────┐
│   ANALYZE   │ ─────────────────────────────▶│  DISCOVER   │
└─────────────┘    + detected_capabilities    └─────────────┘
                   + subtasks                        │
                                                     │ state["matches"]
                                                     ▼
┌─────────────┐    state["executions"]        ┌─────────────┐
│  SYNTHESIZE │ ◀─────────────────────────────│   EXECUTE   │
└─────────────┘                               └─────────────┘
       │
       │ state["final_output"]
       ▼
    OUTPUT
```

---

## Fase 1: ANALYZE - Selezione delle Capabilities

**Durata**: 4,100ms
**Nodo**: `analyze`
**Componente**: AnalyzerAgent (LLM-based)

### Come l'Analyzer Decide le Capabilities

L'Analyzer usa un LLM (Claude) con un prompt strutturato che:

1. **Analizza semanticamente** il task in linguaggio naturale
2. **Identifica le competenze necessarie** mappandole a capabilities note
3. **Scompone in subtask** indipendenti per ogni capability

```python
# agents/router/analyzer.py
ANALYZER_PROMPT = """
Analizza il seguente task e identifica le capabilities necessarie.

CAPABILITIES DISPONIBILI:
- analysis: Analisi approfondita, pro/contro, valutazioni
- estimation: Stime di costi, tempi, quantità
- research: Ricerca informazioni, dati, riferimenti
- calculation: Operazioni matematiche
- translation: Traduzione tra lingue
- summary: Riassunto di testi lunghi

TASK: {task}

Rispondi in JSON:
{{
  "capabilities": ["cap1", "cap2", ...],
  "subtasks": {{
    "cap1": "descrizione subtask specifico per cap1",
    "cap2": "descrizione subtask specifico per cap2"
  }},
  "dependencies": null  // o {{"cap2": ["cap1"]}} se cap2 dipende da cap1
}}
"""
```

### Criteri di Selezione

| Parole chiave nel task | Capability selezionata |
|------------------------|------------------------|
| "analizza", "valuta", "pro e contro" | `analysis` |
| "quanto costa", "stima", "budget" | `estimation` |
| "cerca", "informazioni su", "come funziona" | `research` |
| "calcola", numeri, operazioni | `calculation` |
| "traduci", lingua specifica | `translation` |
| "riassumi", "sintetizza" | `summary` |

### Output per questo Task

Il task menziona "budget" (estimation), "team tecnico" (research), e implicitamente richiede valutazione dei ruoli (analysis):

```json
{
  "detected_capabilities": ["analysis", "estimation", "research"],
  "subtasks": {
    "analysis": "Analizza i ruoli tecnici necessari per un team ecommerce e le priorità in base alle esigenze operative",
    "estimation": "Stima i costi mensili per ciascun ruolo tecnico considerando il budget di 30000 dollari",
    "research": "Fornisci informazioni sui ruoli tecnici standard in un team ecommerce e le competenze richieste"
  },
  "dependencies": null
}
```

---

## Fase 2: DISCOVER - Matching Capability → Agenti

**Durata**: <1ms
**Nodo**: `discover`
**Componente**: AgentRegistry

### Come Funziona il Registry

Ogni agente, alla registrazione, dichiara le proprie **capabilities**:

```python
# agents/router/specialist_agents.py
class ResearchAgent(LLMAgent):
    def __init__(self, storage):
        config = AgentConfig(
            id="researcher",
            name="Research Agent",
            description="Ricerca informazioni e dati",
            capabilities=["research", "search", "info"]  # ← Capabilities dichiarate
        )
        super().__init__(config, storage)

class EstimationAgent(LLMAgent):
    def __init__(self, storage):
        config = AgentConfig(
            id="estimator",
            name="Estimation Agent",
            capabilities=["estimation", "estimate", "cost", "pricing"]
        )

class AnalysisAgent(LLMAgent):
    def __init__(self, storage):
        config = AgentConfig(
            id="analyst",
            name="Analysis Agent",
            capabilities=["analysis", "analyze", "evaluation"]
        )
```

### Algoritmo di Matching

```python
# agents/graph/nodes.py - discover_node
def discover_node(state: GraphState, config: RunnableConfig) -> dict:
    matches = []

    for capability in state["detected_capabilities"]:
        # Cerca agenti che dichiarano questa capability
        agents = registry.find_by_capability(capability)

        matches.append({
            "capability": capability,
            "agent_ids": [a.id for a in agents],
            "matched": len(agents) > 0
        })

    return {"matches": matches}
```

```python
# agents/registry.py
class AgentRegistry:
    def find_by_capability(self, capability: str) -> list[AgentBase]:
        """Trova tutti gli agenti che dichiarano una capability."""
        result = []
        for agent in self._agents.values():
            if capability in agent.config.capabilities:
                result.append(agent)
        return result
```

### Risultato del Matching

| Capability richiesta | Agenti nel Registry | Match |
|---------------------|---------------------|-------|
| `analysis` | `analyst` (capabilities: ["analysis", "analyze", "evaluation"]) | ✅ |
| `estimation` | `estimator` (capabilities: ["estimation", "estimate", "cost"]) | ✅ |
| `research` | `researcher` (capabilities: ["research", "search", "info"]) | ✅ |

### Cosa Succede se Non c'è Match?

```python
# Se nessun agente matcha una capability:
{
    "capability": "translation",
    "agent_ids": [],
    "matched": false  # ← Capability non soddisfatta
}
```

Nell'Execute Node, le capabilities senza match vengono **saltate** (o gestite con fallback).

---

## Fase 3: EXECUTE - Esecuzione Parallela degli Agenti

**Durata Totale**: ~15,120ms
**Nodo**: `execute`
**Pattern**: Fan-out parallelo con `asyncio.gather`

### Meccanismo di Esecuzione

```python
# agents/graph/nodes.py - execute_node
async def execute_node(state: GraphState, config: RunnableConfig) -> dict:
    executions = []
    tasks = []

    for match in state["matches"]:
        if not match["matched"]:
            continue  # Skip capabilities senza agenti

        capability = match["capability"]
        agent_id = match["agent_ids"][0]  # Prende il primo agente disponibile
        agent = registry.get(agent_id)
        subtask = state["subtasks"][capability]

        # Crea task async per esecuzione parallela
        tasks.append(execute_single_agent(agent, subtask, capability))

    # ESECUZIONE PARALLELA: tutti gli agenti partono insieme
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {"executions": results}
```

### Perché Parallelo e Non Sequenziale?

```
SEQUENZIALE (se fossero dipendenti):
├── Analyst ────────────────▶ (14.9s)
│                             ├── Estimator ──────▶ (12.3s)
│                             │                     ├── Researcher ──▶ (15.1s)
│                             │                     │
Totale: 14.9 + 12.3 + 15.1 = 42.3 secondi

PARALLELO (indipendenti):
├── Analyst ────────────────▶ (14.9s)
├── Estimator ──────────────▶ (12.3s)    } Eseguiti contemporaneamente
├── Researcher ─────────────▶ (15.1s)
│
Totale: max(14.9, 12.3, 15.1) = 15.1 secondi

Risparmio: ~64% del tempo
```

### Comunicazione Agente ← → Executor

Ogni agente viene invocato con `receive_message()`:

```python
async def execute_single_agent(agent, subtask, capability):
    start = time.time()

    # Chiama l'agente con il subtask
    response = await agent.receive_message(
        ctx=agent_context("executor"),
        content=subtask,
        sender_id="executor"
    )

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "capability": capability,
        "input_text": subtask,
        "output_text": response.content,
        "duration_ms": int((time.time() - start) * 1000),
        "success": True,
        "tokens": response.metadata.get("tokens", {})
    }
```

### Output delle Esecuzioni

```json
{
  "executions": [
    {
      "agent_id": "analyst",
      "capability": "analysis",
      "output_text": "# Analisi dei Ruoli Tecnici per Team E-commerce\n\n## TIER 1 - PRIORITÀ CRITICA...",
      "duration_ms": 14912,
      "success": true
    },
    {
      "agent_id": "estimator",
      "capability": "estimation",
      "output_text": "# Stima Costi Mensili per Ruoli Tecnici\n\n| Ruolo | Costo | % Budget |...",
      "duration_ms": 12280,
      "success": true
    },
    {
      "agent_id": "researcher",
      "capability": "research",
      "output_text": "# Ruoli Tecnici Standard in un Team E-commerce\n\n## 1. Full Stack Developer...",
      "duration_ms": 15120,
      "success": true
    }
  ]
}
```

---

## Fase 4: Decisione Condizionale

**Funzione**: `should_synthesize(state)`

### Logica di Routing

```python
def should_synthesize(state: GraphState) -> str:
    """Decide se serve sintesi o se l'output è già pronto."""
    successful = [e for e in state["executions"] if e.get("success")]

    if len(successful) > 1:
        # Più agenti hanno risposto → serve integrazione
        return "synthesize"
    elif len(successful) == 1:
        # Un solo agente → usa direttamente il suo output
        return "end"
    else:
        # Nessun agente → errore
        return "end"
```

### Scenari Possibili

| Esecuzioni successful | Decisione | Motivo |
|-----------------------|-----------|--------|
| 0 | → END | Errore, nessun output |
| 1 | → END | Output singolo, non serve sintesi |
| 2+ | → SYNTHESIZE | Serve integrare multiple risposte |

### In questo caso

- Esecuzioni successful: **3** (analyst, estimator, researcher)
- Condizione `len(successful) > 1`: **True**
- **Decisione**: → `"synthesize"`

---

## Fase 5: SYNTHESIZE - Integrazione delle Risposte

**Durata**: 13,000ms
**Nodo**: `synthesize`
**Componente**: SynthesizerAgent (LLM-based)

### Come il Synthesizer Integra le Risposte

Il Synthesizer riceve **tutti gli output** degli agenti e li combina:

```python
# agents/router/synthesizer.py
SYNTHESIS_PROMPT = """
Sei un esperto nell'integrare informazioni da fonti multiple.

TASK ORIGINALE: {original_task}

RISPOSTE DEGLI AGENTI SPECIALIZZATI:

--- ANALYST ---
{analyst_output}

--- ESTIMATOR ---
{estimator_output}

--- RESEARCHER ---
{researcher_output}

ISTRUZIONI:
1. Combina le informazioni SENZA ripetizioni
2. Risolvi eventuali CONTRADDIZIONI (es. cifre diverse)
3. Usa la STRUTTURA più chiara tra quelle proposte
4. Produci una risposta COMPLETA e ACTIONABLE

RISPOSTA INTEGRATA:
"""
```

### Criteri di Sintesi

| Aspetto | Strategia |
|---------|-----------|
| **Dati numerici** | Preferisce Estimator (specialista costi) |
| **Lista ruoli** | Unisce Researcher + Analyst senza duplicati |
| **Priorità** | Segue l'ordine di Analyst (valutazione) |
| **Competenze tecniche** | Prende dettagli da Researcher |
| **Struttura** | Usa tabelle dove possibile |

### Output Sintetizzato

```markdown
# Composizione Team Tecnico E-commerce con Budget $30,000/mese

## COMPOSIZIONE TEAM RACCOMANDATA

| Ruolo | Allocazione Budget | Responsabilità |
|-------|-------------------|----------------|
| Senior Full-Stack Developer (Lead) | $10,000/mese (33%) | Architettura, sviluppo |
| Mid-Level Frontend Developer | $6,000/mese (20%) | UI/UX, React/Next.js |
| Junior Backend Developer | $4,500/mese (15%) | API, database |
| QA Engineer | $5,000/mese (17%) | Test automation |
| DevOps Specialist (Part-time) | $4,500/mese (15%) | Cloud, monitoring |

**TOTALE: $30,000/mese**
```

---

## Riepilogo del Flusso

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. ANALYZE                                                                  │
│     Input:  "task in linguaggio naturale"                                   │
│     Output: capabilities[], subtasks{}                                      │
│     Come:   LLM analizza semanticamente → mappa a capabilities note         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. DISCOVER                                                                 │
│     Input:  capabilities[]                                                  │
│     Output: matches[] (capability → agent_ids)                              │
│     Come:   Registry.find_by_capability() per ogni capability               │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. EXECUTE                                                                  │
│     Input:  matches[], subtasks{}                                           │
│     Output: executions[] (agent outputs)                                    │
│     Come:   asyncio.gather() → agent.receive_message() in parallelo         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. CONDITION: should_synthesize(state)                                      │
│     Se executions.success > 1  →  SYNTHESIZE                                │
│     Altrimenti                 →  END                                       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. SYNTHESIZE                                                               │
│     Input:  executions[] (tutti gli output)                                 │
│     Output: final_output (risposta integrata)                               │
│     Come:   LLM combina, deduplica, risolve contraddizioni                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tempi di Esecuzione

| Fase | Durata | Componente | Note |
|------|--------|------------|------|
| ANALYZE | 4,100ms | LLM (Claude) | Decomposizione semantica |
| DISCOVER | <1ms | Registry (in-memory) | Lookup O(n) |
| EXECUTE | 15,120ms | 3x LLM paralleli | Tempo = max(agenti) |
| CONDITION | <1ms | Python logic | Semplice if |
| SYNTHESIZE | 13,000ms | LLM (Claude) | Integrazione |
| **TOTALE** | **~32,200ms** | | |

---

## Struttura del Codice

### Graph Builder

```python
# agents/graph/graph.py
def build_router_graph() -> CompiledStateGraph:
    graph = StateGraph(GraphState)

    # Nodi (funzioni async)
    graph.add_node("analyze", analyze_node)
    graph.add_node("discover", discover_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    # Edges (flusso)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "discover")
    graph.add_edge("discover", "execute")

    # Conditional edge (routing dinamico)
    graph.add_conditional_edges(
        "execute",
        should_synthesize,
        {"synthesize": "synthesize", "end": END}
    )

    graph.add_edge("synthesize", END)

    return graph.compile()
```

---

## Nota: Visualizzazione UI (SSE)

La visualizzazione del grafo in tempo reale usa **Server-Sent Events (SSE)** per aggiornare la UI nel browser. Questo è **solo per osservabilità** - il sistema funziona identicamente senza UI.

```
Backend                              Frontend (opzionale)
   │                                       │
   │  emit_event({"node": "running"})      │
   │  ────────────────────────────────────▶│  vis.js update
   │                                       │
   │  (il lavoro vero avviene qui)         │
   │                                       │
   │  emit_event({"node": "completed"})    │
   │  ────────────────────────────────────▶│  vis.js update
```

SSE è un side-effect per debug/demo, non parte della logica di orchestrazione.

---

## Link Correlati

- [LangGraph Pattern](./langgraph-pattern.md)
- [Router Pattern](./router-pattern.md)
- [Chain Pattern](./chain-pattern.md)
