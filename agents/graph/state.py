"""
GraphState - TypedDict for LangGraph state management.

Defines the state structure passed between nodes in the LangGraph DAG.
Uses Annotated types with reducers for list aggregation.
"""

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
import operator


# Valid status values for the graph execution
VALID_STATUSES = [
    "pending",
    "analyzing",
    "discovering",
    "executing",
    "synthesizing",
    "completed",
    "failed",
]


class GraphState(TypedDict):
    """
    State structure for the LangGraph router.

    Each node receives the full state and returns updates to specific keys.
    Annotated types with operator.add indicate list reduction (append).
    """

    # Input - set at graph start
    task_id: str
    original_task: str

    # Phase 1: Analysis output
    detected_capabilities: Annotated[list[str], operator.add]
    subtasks: dict[str, str]  # capability -> subtask text
    dependencies: Optional[dict[str, list[str]]]  # capability -> [depends_on_capabilities]

    # Phase 2: Discovery output
    matches: list[dict[str, Any]]  # [{capability, agent_ids, matched}]

    # Phase 3: Execution output
    executions: Annotated[list[dict[str, Any]], operator.add]

    # Phase 4: Synthesis output
    synthesis: Optional[dict[str, Any]]

    # Final output
    final_output: str
    status: str

    # Graph visualization data for vis.js
    graph_data: dict[str, Any]


def create_initial_graph_data() -> dict[str, Any]:
    """
    Create initial graph data structure for vis.js visualization.

    Returns:
        Dict with empty nodes and edges lists.
    """
    return {
        "nodes": [],
        "edges": [],
    }


def create_initial_state(task_id: str, task: str) -> GraphState:
    """
    Create a valid initial state for the graph.

    Args:
        task_id: Unique identifier for this task
        task: The original task text

    Returns:
        GraphState with all fields initialized
    """
    return GraphState(
        task_id=task_id,
        original_task=task,
        detected_capabilities=[],
        subtasks={},
        dependencies=None,
        matches=[],
        executions=[],
        synthesis=None,
        final_output="",
        status="pending",
        graph_data=create_initial_graph_data(),
    )
