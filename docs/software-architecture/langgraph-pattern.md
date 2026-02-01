# LangGraph Integration Pattern

## Overview

The LangGraph integration provides DAG-based task orchestration with real-time visualization. It replaces the imperative SmartRouter with a declarative graph-based approach that offers:

- **State Management**: Typed state flowing through the graph
- **Conditional Routing**: Dynamic path selection based on execution results
- **Visualization**: Real-time graph updates via vis.js
- **Streaming**: SSE events for live UI updates

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Task                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                          │
│                                                                  │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│   │ Analyze  │────▶│ Discover │────▶│ Execute  │                │
│   └──────────┘     └──────────┘     └────┬─────┘                │
│                                          │                       │
│                         ┌────────────────┼────────────────┐      │
│                         ▼                ▼                ▼      │
│                    ┌────────┐      ┌────────┐      ┌────────┐   │
│                    │Agent 1 │      │Agent 2 │      │Agent 3 │   │
│                    └────┬───┘      └────┬───┘      └────┬───┘   │
│                         │               │               │        │
│                         └───────────────┼───────────────┘        │
│                                         ▼                        │
│                                  ┌────────────┐                  │
│                                  │ Synthesize │                  │
│                                  └─────┬──────┘                  │
└────────────────────────────────────────┼────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
             ┌──────────┐         ┌──────────┐         ┌──────────┐
             │ SSE      │         │ Graph    │         │ Result   │
             │ Events   │         │ Viz Data │         │ API      │
             └──────────┘         └──────────┘         └──────────┘
                    │                    │
                    └────────┬───────────┘
                             ▼
                    ┌──────────────────┐
                    │   vis.js Graph   │
                    │   Live Webpage   │
                    └──────────────────┘
```

## Components

### GraphState (`agents/graph/state.py`)

TypedDict defining the state flowing through the graph:

```python
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

Key features:
- **Annotated lists**: Use `operator.add` for reducers that combine results
- **Optional synthesis**: Only populated when synthesis is triggered
- **graph_data**: Contains vis.js node/edge updates

### Nodes (`agents/graph/nodes.py`)

Four processing nodes:

| Node | Purpose | Emits Events |
|------|---------|--------------|
| `analyze_node` | LLM extracts capabilities from task | Node creation, capability nodes |
| `discover_node` | Find agents in registry | Agent nodes, match edges |
| `execute_node` | Run agents on subtasks | Execution status updates |
| `synthesize_node` | Combine multiple outputs | Synthesis completion |

Each node emits graph updates for vis.js:

```python
async def analyze_node(state: GraphState, config: RunnableConfig) -> dict:
    _emit_graph_update(config, "add_node", node={
        "id": "analyze",
        "label": "Analyzer",
        "state": "running"
    })
    # ... processing ...
    _emit_graph_update(config, "update_node", node={
        "id": "analyze",
        "state": "completed"
    })
```

### Graph Builder (`agents/graph/graph.py`)

Constructs the StateGraph:

```python
def build_router_graph() -> CompiledStateGraph:
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("discover", discover_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    # Linear flow
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "discover")
    graph.add_edge("discover", "execute")

    # Conditional: synthesize if 2+ successful executions
    graph.add_conditional_edges(
        "execute",
        should_synthesize,
        {"synthesize": "synthesize", "end": END}
    )
    graph.add_edge("synthesize", END)

    return graph.compile()
```

### GraphRunner (`agents/graph/runner.py`)

Wraps graph execution with:
- Task tracking
- SSE event streaming
- Mermaid diagram generation

```python
runner = GraphRunner(registry, storage)

# Synchronous execution
result = await runner.run("Calculate 5+3")

# Streaming execution
async for event in runner.stream("Calculate 5+3"):
    print(event)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/run` | POST | Execute task through graph |
| `/api/graph/stream` | POST | Execute with SSE streaming |
| `/api/graph/events/{task_id}` | GET | SSE stream for running task |
| `/api/graph/status/{task_id}` | GET | Get task status |
| `/api/graph/structure` | GET | Get Mermaid diagram |
| `/api/graph/registry` | GET | List registered agents |

## SSE Events

| Event Type | Payload | Purpose |
|------------|---------|---------|
| `graph_update` | `{action, node/edge}` | vis.js updates |
| `execution_started` | `{task_id, task}` | Execution began |
| `execution_completed` | `{status, duration_ms}` | Execution finished |
| `execution_failed` | `{error}` | Error occurred |

## Visualization

The frontend (`static/graph/`) uses vis.js for real-time graph visualization:

```javascript
const network = new vis.Network(container, { nodes, edges }, {
    layout: {
        hierarchical: {
            direction: 'LR',
            sortMethod: 'directed'
        }
    }
});

// Handle SSE events
eventSource.addEventListener('graph_update', (e) => {
    const data = JSON.parse(e.data);
    if (data.action === 'add_node') {
        nodes.add({...});
    } else if (data.action === 'update_node') {
        nodes.update({...});
    }
});
```

### Node Colors

| State | Color |
|-------|-------|
| Pending | Gray (`#475569`) |
| Running | Yellow (`#f59e0b`) |
| Completed | Green (`#22c55e`) |
| Failed | Red (`#ef4444`) |

## Dependency Support

The graph supports task dependencies:

```python
# Analyzer can detect dependencies
{
    "capabilities": ["calculation", "creative_writing"],
    "subtasks": {
        "calculation": "5+3",
        "creative_writing": "write haiku about result"
    },
    "dependencies": {
        "creative_writing": ["calculation"]
    }
}
```

The `execute_node` respects dependencies via topological sort, injecting prior results into dependent tasks.

## Testing

### Unit Tests
```bash
pytest tests/unit/test_graph*.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_langgraph.py -v
```

## Usage Example

```python
from agents.graph import build_router_graph, create_initial_state

# Build graph with dependencies
graph = build_router_graph(
    registry=registry,
    storage=storage,
    model="claude-sonnet-4-5"
)

# Create initial state
state = create_initial_state(
    task_id="demo-1",
    task="Calculate 5+3 and write a haiku about the result"
)

# Execute
result = await graph.ainvoke(state)
print(result["final_output"])
```

## Demo

Access the visualization at: `http://localhost:8000/static/graph/`

Quick tasks:
- "calcola 5+3" (single agent)
- "quanto costa un razzo SpaceX?" (multi-agent with synthesis)
- "analizza i pro e contro del remote working e riassumi" (analysis + summary)
