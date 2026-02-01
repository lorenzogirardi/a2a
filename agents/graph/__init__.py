"""
LangGraph-based task orchestration module.

Provides DAG-based execution with:
- State management via TypedDict
- Node functions for each processing phase
- Conditional edges for synthesis
- Real-time graph visualization data
"""

from .state import GraphState, create_initial_state, create_initial_graph_data, VALID_STATUSES
from .nodes import analyze_node, discover_node, execute_node, synthesize_node, should_synthesize
from .graph import build_router_graph

__all__ = [
    "GraphState",
    "create_initial_state",
    "create_initial_graph_data",
    "VALID_STATUSES",
    "analyze_node",
    "discover_node",
    "execute_node",
    "synthesize_node",
    "should_synthesize",
    "build_router_graph",
]
