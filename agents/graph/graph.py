"""
LangGraph StateGraph Builder - Builds the router execution graph.

Creates a DAG with nodes for analyze, discover, execute, and synthesize.
Uses conditional edges to decide whether synthesis is needed.
"""

from typing import Any, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from .state import GraphState
from .nodes import (
    analyze_node,
    discover_node,
    execute_node,
    synthesize_node,
    should_synthesize,
    set_analyzer,
    set_registry,
    set_executor,
    set_synthesizer,
)


def build_router_graph(
    registry: Optional[Any] = None,
    storage: Optional[Any] = None,
    model: str = "claude-sonnet-4-5"
) -> CompiledStateGraph:
    """
    Build the LangGraph router graph.

    The graph has 4 processing nodes:
    1. analyze: Detect capabilities from task
    2. discover: Find agents for capabilities
    3. execute: Run subtasks on agents
    4. synthesize: Combine multiple outputs (conditional)

    Flow:
    START -> analyze -> discover -> execute --(conditional)--> synthesize -> END
                                          |                               |
                                          +-------> END <-----------------+

    Args:
        registry: AgentRegistry for agent discovery
        storage: StorageBase for agent state
        model: LLM model for analyzer and synthesizer

    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize dependencies if provided
    if registry:
        set_registry(registry)

        # Create executor with registry
        from agents.router.executor import TaskExecutor
        executor = TaskExecutor(registry=registry)
        set_executor(executor)

    if storage:
        # Create analyzer and synthesizer with storage
        from agents.router.analyzer import AnalyzerAgent
        from agents.router.synthesizer import SynthesizerAgent

        analyzer = AnalyzerAgent(storage=storage, model=model)
        synthesizer = SynthesizerAgent(storage=storage, model=model)

        set_analyzer(analyzer)
        set_synthesizer(synthesizer)

    # Build the graph
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("discover", discover_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    # Add edges
    # START -> analyze
    graph.add_edge(START, "analyze")

    # analyze -> discover
    graph.add_edge("analyze", "discover")

    # discover -> execute
    graph.add_edge("discover", "execute")

    # Conditional edge after execute
    graph.add_conditional_edges(
        "execute",
        should_synthesize,
        {
            "synthesize": "synthesize",
            "end": END
        }
    )

    # synthesize -> END
    graph.add_edge("synthesize", END)

    # Compile and return
    return graph.compile()


def get_graph_structure(graph: CompiledStateGraph) -> dict[str, Any]:
    """
    Get the graph structure for visualization.

    Returns a dict with:
    - mermaid: Mermaid diagram string
    - nodes: List of node info
    - edges: List of edge info

    Args:
        graph: Compiled graph

    Returns:
        Dict with graph structure info
    """
    graph_def = graph.get_graph()

    # Get nodes - handle both dict and list formats
    if isinstance(graph_def.nodes, dict):
        nodes = [
            {"id": node_id, "name": node_id}
            for node_id in graph_def.nodes.keys()
        ]
    else:
        nodes = [
            {"id": n if isinstance(n, str) else n.id, "name": n if isinstance(n, str) else getattr(n, 'name', n.id)}
            for n in graph_def.nodes
        ]

    # Get edges
    edges = [
        {
            "source": e.source if hasattr(e, 'source') else e[0],
            "target": e.target if hasattr(e, 'target') else e[1],
            "conditional": getattr(e, 'conditional', False) if hasattr(e, 'conditional') else False
        }
        for e in graph_def.edges
    ]

    # Generate Mermaid
    mermaid = graph_def.draw_mermaid()

    return {
        "mermaid": mermaid,
        "nodes": nodes,
        "edges": edges
    }
