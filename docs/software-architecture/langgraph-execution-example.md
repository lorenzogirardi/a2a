# LangGraph Execution: Detailed Example

> **Task**: "With a budget of 30000 dollars per month, and needing to build a small ecommerce team, how should the technical team be composed"

This document illustrates the complete execution flow of the LangGraph system, showing how a complex request is decomposed, distributed to multiple specialized agents, and finally synthesized into a coherent response.

## Demo Video

[![Demo LangGraph Execution](https://res.cloudinary.com/ethzero/video/upload/so_3,w_800/v1769976053/ai/a2a/agent-discovery-graph.jpg)](https://res.cloudinary.com/ethzero/video/upload/v1769976053/ai/a2a/agent-discovery-graph.mp4)

*Click on the image to watch the real-time execution video*

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER TASK                                       │
│  "with a budget of 30000 dollars per month, and needing to build a small    │
│   ecommerce team, how should the technical team be composed"                │
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

## Node Communication: The State

LangGraph nodes **do not communicate directly with each other**. Each node receives the current state, modifies it, and passes the updated state to the next node.

```python
# agents/graph/state.py
class GraphState(TypedDict):
    # Initial input
    task_id: str
    original_task: str

    # Output of ANALYZE → Input of DISCOVER
    detected_capabilities: Annotated[list[str], operator.add]
    subtasks: dict[str, str]  # capability → subtask description
    dependencies: Optional[dict[str, list[str]]]

    # Output of DISCOVER → Input of EXECUTE
    matches: list[dict[str, Any]]  # capability → agent_ids

    # Output of EXECUTE → Input of SYNTHESIZE
    executions: Annotated[list[dict[str, Any]], operator.add]

    # Output of SYNTHESIZE
    synthesis: Optional[dict[str, Any]]
    final_output: str
    status: str
```

### State Flow

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

## Phase 1: ANALYZE - Capability Selection

**Duration**: 4,100ms
**Node**: `analyze`
**Component**: AnalyzerAgent (LLM-based)

### How the Analyzer Decides Capabilities

The Analyzer uses an LLM (Claude) with a structured prompt that:

1. **Semantically analyzes** the task in natural language
2. **Identifies required skills** mapping them to known capabilities
3. **Decomposes into subtasks** independent for each capability

```python
# agents/router/analyzer.py
ANALYZER_PROMPT = """
Analyze the following task and identify the required capabilities.

AVAILABLE CAPABILITIES:
- analysis: In-depth analysis, pros/cons, evaluations
- estimation: Cost, time, quantity estimates
- research: Information research, data, references
- calculation: Mathematical operations
- translation: Translation between languages
- summary: Summarizing long texts

TASK: {task}

Respond in JSON:
{{
  "capabilities": ["cap1", "cap2", ...],
  "subtasks": {{
    "cap1": "specific subtask description for cap1",
    "cap2": "specific subtask description for cap2"
  }},
  "dependencies": null  // or {{"cap2": ["cap1"]}} if cap2 depends on cap1
}}
"""
```

### Selection Criteria

| Keywords in task | Selected capability |
|------------------|---------------------|
| "analyze", "evaluate", "pros and cons" | `analysis` |
| "how much", "estimate", "budget" | `estimation` |
| "search", "information about", "how does it work" | `research` |
| "calculate", numbers, operations | `calculation` |
| "translate", specific language | `translation` |
| "summarize", "synthesize" | `summary` |

### Output for this Task

The task mentions "budget" (estimation), "technical team" (research), and implicitly requires role evaluation (analysis):

```json
{
  "detected_capabilities": ["analysis", "estimation", "research"],
  "subtasks": {
    "analysis": "Analyze the technical roles needed for an ecommerce team and priorities based on operational needs",
    "estimation": "Estimate monthly costs for each technical role considering the 30000 dollar budget",
    "research": "Provide information on standard technical roles in an ecommerce team and required skills"
  },
  "dependencies": null
}
```

---

## Phase 2: DISCOVER - Capability → Agent Matching

**Duration**: <1ms
**Node**: `discover`
**Component**: AgentRegistry

### How the Registry Works

Each agent, upon registration, declares its **capabilities**:

```python
# agents/router/specialist_agents.py
class ResearchAgent(LLMAgent):
    def __init__(self, storage):
        config = AgentConfig(
            id="researcher",
            name="Research Agent",
            description="Researches information and data",
            capabilities=["research", "search", "info"]  # ← Declared capabilities
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

### Matching Algorithm

```python
# agents/graph/nodes.py - discover_node
def discover_node(state: GraphState, config: RunnableConfig) -> dict:
    matches = []

    for capability in state["detected_capabilities"]:
        # Find agents that declare this capability
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
        """Find all agents that declare a capability."""
        result = []
        for agent in self._agents.values():
            if capability in agent.config.capabilities:
                result.append(agent)
        return result
```

### Matching Result

| Requested capability | Agents in Registry | Match |
|---------------------|---------------------|-------|
| `analysis` | `analyst` (capabilities: ["analysis", "analyze", "evaluation"]) | ✅ |
| `estimation` | `estimator` (capabilities: ["estimation", "estimate", "cost"]) | ✅ |
| `research` | `researcher` (capabilities: ["research", "search", "info"]) | ✅ |

### What Happens if There's No Match?

```python
# If no agent matches a capability:
{
    "capability": "translation",
    "agent_ids": [],
    "matched": false  # ← Capability not satisfied
}
```

In the Execute Node, capabilities without matches are **skipped** (or handled with fallback).

---

## Phase 3: EXECUTE - Parallel Agent Execution

**Total Duration**: ~15,120ms
**Node**: `execute`
**Pattern**: Parallel fan-out with `asyncio.gather`

### Execution Mechanism

```python
# agents/graph/nodes.py - execute_node
async def execute_node(state: GraphState, config: RunnableConfig) -> dict:
    executions = []
    tasks = []

    for match in state["matches"]:
        if not match["matched"]:
            continue  # Skip capabilities without agents

        capability = match["capability"]
        agent_id = match["agent_ids"][0]  # Takes the first available agent
        agent = registry.get(agent_id)
        subtask = state["subtasks"][capability]

        # Create async task for parallel execution
        tasks.append(execute_single_agent(agent, subtask, capability))

    # PARALLEL EXECUTION: all agents start together
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {"executions": results}
```

### Why Parallel and Not Sequential?

```
SEQUENTIAL (if they were dependent):
├── Analyst ────────────────▶ (14.9s)
│                             ├── Estimator ──────▶ (12.3s)
│                             │                     ├── Researcher ──▶ (15.1s)
│                             │                     │
Total: 14.9 + 12.3 + 15.1 = 42.3 seconds

PARALLEL (independent):
├── Analyst ────────────────▶ (14.9s)
├── Estimator ──────────────▶ (12.3s)    } Executed simultaneously
├── Researcher ─────────────▶ (15.1s)
│
Total: max(14.9, 12.3, 15.1) = 15.1 seconds

Savings: ~64% of time
```

### Agent ← → Executor Communication

Each agent is invoked with `receive_message()`:

```python
async def execute_single_agent(agent, subtask, capability):
    start = time.time()

    # Call the agent with the subtask
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

### Execution Output

```json
{
  "executions": [
    {
      "agent_id": "analyst",
      "capability": "analysis",
      "output_text": "# Technical Role Analysis for E-commerce Team\n\n## TIER 1 - CRITICAL PRIORITY...",
      "duration_ms": 14912,
      "success": true
    },
    {
      "agent_id": "estimator",
      "capability": "estimation",
      "output_text": "# Monthly Cost Estimates for Technical Roles\n\n| Role | Cost | % Budget |...",
      "duration_ms": 12280,
      "success": true
    },
    {
      "agent_id": "researcher",
      "capability": "research",
      "output_text": "# Standard Technical Roles in an E-commerce Team\n\n## 1. Full Stack Developer...",
      "duration_ms": 15120,
      "success": true
    }
  ]
}
```

---

## Phase 4: Conditional Decision

**Function**: `should_synthesize(state)`

### Routing Logic

```python
def should_synthesize(state: GraphState) -> str:
    """Decide if synthesis is needed or if output is ready."""
    successful = [e for e in state["executions"] if e.get("success")]

    if len(successful) > 1:
        # Multiple agents responded → integration needed
        return "synthesize"
    elif len(successful) == 1:
        # Single agent → use its output directly
        return "end"
    else:
        # No agents → error
        return "end"
```

### Possible Scenarios

| Successful executions | Decision | Reason |
|-----------------------|----------|--------|
| 0 | → END | Error, no output |
| 1 | → END | Single output, no synthesis needed |
| 2+ | → SYNTHESIZE | Need to integrate multiple responses |

### In this case

- Successful executions: **3** (analyst, estimator, researcher)
- Condition `len(successful) > 1`: **True**
- **Decision**: → `"synthesize"`

---

## Phase 5: SYNTHESIZE - Response Integration

**Duration**: 13,000ms
**Node**: `synthesize`
**Component**: SynthesizerAgent (LLM-based)

### How the Synthesizer Integrates Responses

The Synthesizer receives **all agent outputs** and combines them:

```python
# agents/router/synthesizer.py
SYNTHESIS_PROMPT = """
You are an expert at integrating information from multiple sources.

ORIGINAL TASK: {original_task}

SPECIALIZED AGENT RESPONSES:

--- ANALYST ---
{analyst_output}

--- ESTIMATOR ---
{estimator_output}

--- RESEARCHER ---
{researcher_output}

INSTRUCTIONS:
1. Combine information WITHOUT repetitions
2. Resolve any CONTRADICTIONS (e.g., different figures)
3. Use the CLEAREST structure among those proposed
4. Produce a COMPLETE and ACTIONABLE response

INTEGRATED RESPONSE:
"""
```

### Synthesis Criteria

| Aspect | Strategy |
|--------|----------|
| **Numerical data** | Prefer Estimator (cost specialist) |
| **Role list** | Merge Researcher + Analyst without duplicates |
| **Priorities** | Follow Analyst's order (evaluation) |
| **Technical skills** | Take details from Researcher |
| **Structure** | Use tables where possible |

### Synthesized Output

```markdown
# E-commerce Technical Team Composition with $30,000/month Budget

## RECOMMENDED TEAM COMPOSITION

| Role | Budget Allocation | Responsibilities |
|------|-------------------|------------------|
| Senior Full-Stack Developer (Lead) | $10,000/month (33%) | Architecture, development |
| Mid-Level Frontend Developer | $6,000/month (20%) | UI/UX, React/Next.js |
| Junior Backend Developer | $4,500/month (15%) | API, database |
| QA Engineer | $5,000/month (17%) | Test automation |
| DevOps Specialist (Part-time) | $4,500/month (15%) | Cloud, monitoring |

**TOTAL: $30,000/month**
```

---

## Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. ANALYZE                                                                  │
│     Input:  "task in natural language"                                      │
│     Output: capabilities[], subtasks{}                                      │
│     How:    LLM semantically analyzes → maps to known capabilities          │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. DISCOVER                                                                 │
│     Input:  capabilities[]                                                  │
│     Output: matches[] (capability → agent_ids)                              │
│     How:    Registry.find_by_capability() for each capability               │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. EXECUTE                                                                  │
│     Input:  matches[], subtasks{}                                           │
│     Output: executions[] (agent outputs)                                    │
│     How:    asyncio.gather() → agent.receive_message() in parallel          │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. CONDITION: should_synthesize(state)                                      │
│     If executions.success > 1  →  SYNTHESIZE                                │
│     Otherwise                  →  END                                       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ state
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. SYNTHESIZE                                                               │
│     Input:  executions[] (all outputs)                                      │
│     Output: final_output (integrated response)                              │
│     How:    LLM combines, deduplicates, resolves contradictions             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Times

| Phase | Duration | Component | Notes |
|-------|----------|-----------|-------|
| ANALYZE | 4,100ms | LLM (Claude) | Semantic decomposition |
| DISCOVER | <1ms | Registry (in-memory) | O(n) lookup |
| EXECUTE | 15,120ms | 3x parallel LLMs | Time = max(agents) |
| CONDITION | <1ms | Python logic | Simple if |
| SYNTHESIZE | 13,000ms | LLM (Claude) | Integration |
| **TOTAL** | **~32,200ms** | | |

---

## Code Structure

### Graph Builder

```python
# agents/graph/graph.py
def build_router_graph() -> CompiledStateGraph:
    graph = StateGraph(GraphState)

    # Nodes (async functions)
    graph.add_node("analyze", analyze_node)
    graph.add_node("discover", discover_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    # Edges (flow)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "discover")
    graph.add_edge("discover", "execute")

    # Conditional edge (dynamic routing)
    graph.add_conditional_edges(
        "execute",
        should_synthesize,
        {"synthesize": "synthesize", "end": END}
    )

    graph.add_edge("synthesize", END)

    return graph.compile()
```

---

## Note: UI Visualization (SSE)

Real-time graph visualization uses **Server-Sent Events (SSE)** to update the UI in the browser. This is **for observability only** - the system works identically without the UI.

```
Backend                              Frontend (optional)
   │                                       │
   │  emit_event({"node": "running"})      │
   │  ────────────────────────────────────▶│  vis.js update
   │                                       │
   │  (the real work happens here)         │
   │                                       │
   │  emit_event({"node": "completed"})    │
   │  ────────────────────────────────────▶│  vis.js update
```

SSE is a side-effect for debug/demo, not part of the orchestration logic.

---

## Related Links

- [LangGraph Pattern](./langgraph-pattern.md)
- [Router Pattern](./router-pattern.md)
- [Chain Pattern](./chain-pattern.md)
