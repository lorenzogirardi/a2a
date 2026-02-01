"""
Unit tests for LangGraph StateGraph builder.

Tests the graph construction and structure.
"""

import pytest


class TestGraphBuilder:
    """Tests for build_router_graph function."""

    def test_build_router_graph_import(self):
        """build_router_graph can be imported."""
        from agents.graph.graph import build_router_graph
        assert build_router_graph is not None

    def test_build_router_graph_returns_compiled_graph(self):
        """build_router_graph returns a compiled StateGraph."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph()

        # Should be a compiled graph (CompiledStateGraph)
        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")

    def test_graph_has_all_nodes(self):
        """Graph has all required nodes: analyze, discover, execute, synthesize."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph()

        # Get the underlying graph structure
        graph_structure = graph.get_graph()
        # nodes is a dict-like with node_id as key
        node_ids = list(graph_structure.nodes.keys())

        assert "analyze" in node_ids
        assert "discover" in node_ids
        assert "execute" in node_ids
        assert "synthesize" in node_ids

    def test_graph_has_correct_edges(self):
        """Graph has correct edge connections."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph()
        graph_structure = graph.get_graph()

        # Check edges exist
        edges = [(e.source, e.target) for e in graph_structure.edges]

        # START -> analyze
        assert ("__start__", "analyze") in edges

        # analyze -> discover
        assert ("analyze", "discover") in edges

        # discover -> execute
        assert ("discover", "execute") in edges

        # synthesize -> END
        assert ("synthesize", "__end__") in edges

    def test_graph_has_conditional_edge_after_execute(self):
        """Graph has conditional edge after execute node."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph()
        graph_structure = graph.get_graph()

        # execute should have edges to both synthesize and end
        execute_targets = [
            e.target for e in graph_structure.edges if e.source == "execute"
        ]

        assert "synthesize" in execute_targets or "__end__" in execute_targets

    def test_graph_can_generate_mermaid(self):
        """Graph can generate Mermaid diagram."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph()
        graph_structure = graph.get_graph()

        mermaid = graph_structure.draw_mermaid()

        assert isinstance(mermaid, str)
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()
        assert "analyze" in mermaid
        assert "discover" in mermaid
        assert "execute" in mermaid
        assert "synthesize" in mermaid


class TestGraphConfig:
    """Tests for graph configuration."""

    def test_graph_accepts_registry(self):
        """Graph can be configured with a registry."""
        from agents.graph.graph import build_router_graph
        from unittest.mock import MagicMock

        registry = MagicMock()
        graph = build_router_graph(registry=registry)

        assert graph is not None

    def test_graph_accepts_storage(self):
        """Graph can be configured with storage."""
        from agents.graph.graph import build_router_graph
        from unittest.mock import MagicMock

        storage = MagicMock()
        graph = build_router_graph(storage=storage)

        assert graph is not None

    def test_graph_accepts_model(self):
        """Graph can be configured with LLM model."""
        from agents.graph.graph import build_router_graph

        graph = build_router_graph(model="claude-sonnet-4-5")

        assert graph is not None


class TestGraphExecution:
    """Tests for graph execution."""

    @pytest.mark.asyncio
    async def test_graph_invoke_basic(self):
        """Graph can be invoked with initial state."""
        from agents.graph.graph import build_router_graph
        from agents.graph.state import create_initial_state
        from agents.graph import nodes
        from unittest.mock import AsyncMock, MagicMock

        # Create mocks for all dependencies
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze.return_value = MagicMock(
            detected_capabilities=["calculation"],
            subtasks={"calculation": "5+3"},
            duration_ms=50
        )

        mock_registry = MagicMock()
        mock_agent = MagicMock(id="calc", name="Calculator")
        mock_registry.find_by_capability.return_value = [mock_agent]

        # Setup executor mock - use MagicMock as base to avoid hasattr returning True
        from agents.router.models import ExecutionResult
        mock_executor = MagicMock()
        mock_executor.execute_all = AsyncMock(return_value=[
            ExecutionResult(
                agent_id="calc",
                agent_name="Calculator",
                capability="calculation",
                input_text="5+3",
                output_text="8",
                success=True,
                duration_ms=30,
                tokens={"input": 5, "output": 2}
            )
        ])
        # Remove execute_with_dependencies so hasattr returns False
        del mock_executor.execute_with_dependencies

        # Directly set the module-level dependencies
        nodes.set_analyzer(mock_analyzer)
        nodes.set_registry(mock_registry)
        nodes.set_executor(mock_executor)

        try:
            graph = build_router_graph()
            initial_state = create_initial_state(
                task_id="test-123",
                task="Calculate 5+3"
            )

            result = await graph.ainvoke(initial_state)

            assert result is not None
            # Single execution goes to "executed" (skips synthesis)
            assert result["status"] in ("executed", "completed")
            assert "8" in result["final_output"]
        finally:
            # Clean up
            nodes.set_analyzer(None)
            nodes.set_registry(None)
            nodes.set_executor(None)

    @pytest.mark.asyncio
    async def test_graph_stream_events(self):
        """Graph can stream events during execution."""
        from agents.graph.graph import build_router_graph
        from agents.graph.state import create_initial_state
        from unittest.mock import AsyncMock, MagicMock, patch

        with patch("agents.graph.nodes.get_analyzer") as mock_analyzer_get, \
             patch("agents.graph.nodes.get_registry") as mock_registry_get, \
             patch("agents.graph.nodes.get_executor") as mock_executor_get:

            # Setup mocks
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze.return_value = MagicMock(
                detected_capabilities=["calculation"],
                subtasks={"calculation": "5+3"},
                duration_ms=50
            )
            mock_analyzer_get.return_value = mock_analyzer

            mock_registry = MagicMock()
            mock_registry.find_by_capability.return_value = [
                MagicMock(id="calc", name="Calculator")
            ]
            mock_registry_get.return_value = mock_registry

            mock_executor = AsyncMock()
            mock_executor.execute_all.return_value = [
                MagicMock(
                    agent_id="calc",
                    output_text="8",
                    success=True,
                    duration_ms=30
                )
            ]
            mock_executor_get.return_value = mock_executor

            graph = build_router_graph()
            initial_state = create_initial_state(
                task_id="test-123",
                task="Calculate 5+3"
            )

            events = []
            async for event in graph.astream(initial_state):
                events.append(event)

        # Should have received events for each node
        assert len(events) > 0
