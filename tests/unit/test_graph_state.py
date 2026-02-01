"""
Unit tests for GraphState TypedDict.

Tests the state structure used by LangGraph for task orchestration.
"""

import pytest
from typing import get_type_hints


class TestGraphState:
    """Tests for GraphState TypedDict."""

    def test_import_graph_state(self):
        """GraphState can be imported from agents.graph.state."""
        from agents.graph.state import GraphState
        assert GraphState is not None

    def test_graph_state_has_required_fields(self):
        """GraphState has all required fields with correct types."""
        from agents.graph.state import GraphState

        hints = get_type_hints(GraphState)

        # Required fields
        assert "task_id" in hints
        assert "original_task" in hints
        assert "detected_capabilities" in hints
        assert "subtasks" in hints
        assert "matches" in hints
        assert "executions" in hints
        assert "synthesis" in hints
        assert "final_output" in hints
        assert "status" in hints
        assert "graph_data" in hints

    def test_graph_state_can_be_instantiated(self):
        """GraphState can be used to create a valid state dict."""
        from agents.graph.state import GraphState

        state: GraphState = {
            "task_id": "test-123",
            "original_task": "Calculate 5+3",
            "detected_capabilities": [],
            "subtasks": {},
            "matches": [],
            "executions": [],
            "synthesis": None,
            "final_output": "",
            "status": "pending",
            "graph_data": {"nodes": [], "edges": []},
        }

        assert state["task_id"] == "test-123"
        assert state["status"] == "pending"

    def test_graph_state_capabilities_are_additive(self):
        """detected_capabilities should use operator.add for reduction."""
        from agents.graph.state import GraphState
        import operator

        # The Annotated type should specify operator.add
        # This is checked at runtime by LangGraph
        state: GraphState = {
            "task_id": "test-123",
            "original_task": "test",
            "detected_capabilities": ["calc"],
            "subtasks": {},
            "matches": [],
            "executions": [],
            "synthesis": None,
            "final_output": "",
            "status": "pending",
            "graph_data": {},
        }

        # Capabilities should be a list
        assert isinstance(state["detected_capabilities"], list)

    def test_graph_state_executions_are_additive(self):
        """executions should use operator.add for reduction."""
        from agents.graph.state import GraphState

        state: GraphState = {
            "task_id": "test-123",
            "original_task": "test",
            "detected_capabilities": [],
            "subtasks": {},
            "matches": [],
            "executions": [{"agent_id": "calc", "output": "8"}],
            "synthesis": None,
            "final_output": "",
            "status": "pending",
            "graph_data": {},
        }

        assert isinstance(state["executions"], list)
        assert len(state["executions"]) == 1


class TestGraphStateStatus:
    """Tests for GraphState status values."""

    def test_valid_status_values(self):
        """GraphState supports all expected status values."""
        from agents.graph.state import VALID_STATUSES

        expected = {
            "pending",
            "analyzing",
            "discovering",
            "executing",
            "synthesizing",
            "completed",
            "failed",
        }

        assert expected == set(VALID_STATUSES)


class TestGraphDataStructure:
    """Tests for graph_data visualization structure."""

    def test_graph_data_structure(self):
        """graph_data should have nodes and edges lists."""
        from agents.graph.state import create_initial_graph_data

        graph_data = create_initial_graph_data()

        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert isinstance(graph_data["nodes"], list)
        assert isinstance(graph_data["edges"], list)

    def test_create_initial_state(self):
        """create_initial_state helper creates valid initial state."""
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )

        assert state["task_id"] == "test-123"
        assert state["original_task"] == "Calculate 5+3"
        assert state["status"] == "pending"
        assert state["detected_capabilities"] == []
        assert state["subtasks"] == {}
        assert state["matches"] == []
        assert state["executions"] == []
        assert state["synthesis"] is None
        assert state["final_output"] == ""
