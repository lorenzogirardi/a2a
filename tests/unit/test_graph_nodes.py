"""
Unit tests for LangGraph nodes.

Tests the individual node functions: analyze, discover, execute, synthesize.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAnalyzeNode:
    """Tests for analyze_node function."""

    @pytest.mark.asyncio
    async def test_analyze_node_import(self):
        """analyze_node can be imported."""
        from agents.graph.nodes import analyze_node
        assert analyze_node is not None

    @pytest.mark.asyncio
    async def test_analyze_node_detects_capabilities(self):
        """analyze_node detects capabilities from task."""
        from agents.graph.nodes import analyze_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )

        # Mock the analyzer
        with patch("agents.graph.nodes.get_analyzer") as mock_get:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze.return_value = MagicMock(
                detected_capabilities=["calculation"],
                subtasks={"calculation": "5+3"}
            )
            mock_get.return_value = mock_analyzer

            result = await analyze_node(state, config={})

        assert "detected_capabilities" in result
        assert "subtasks" in result
        assert "calculation" in result["detected_capabilities"]

    @pytest.mark.asyncio
    async def test_analyze_node_emits_graph_update(self):
        """analyze_node emits graph_update events."""
        from agents.graph.nodes import analyze_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )

        events = []
        config = {"configurable": {"stream_writer": events.append}}

        with patch("agents.graph.nodes.get_analyzer") as mock_get:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze.return_value = MagicMock(
                detected_capabilities=["calculation"],
                subtasks={"calculation": "5+3"}
            )
            mock_get.return_value = mock_analyzer

            result = await analyze_node(state, config=config)

        # Should have emitted graph update events
        graph_updates = [e for e in events if e.get("type") == "graph_update"]
        assert len(graph_updates) > 0

    @pytest.mark.asyncio
    async def test_analyze_node_updates_status(self):
        """analyze_node updates status to analyzing."""
        from agents.graph.nodes import analyze_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )

        with patch("agents.graph.nodes.get_analyzer") as mock_get:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze.return_value = MagicMock(
                detected_capabilities=["calculation"],
                subtasks={"calculation": "5+3"}
            )
            mock_get.return_value = mock_analyzer

            result = await analyze_node(state, config={})

        assert result.get("status") == "analyzed"


class TestDiscoverNode:
    """Tests for discover_node function."""

    @pytest.mark.asyncio
    async def test_discover_node_import(self):
        """discover_node can be imported."""
        from agents.graph.nodes import discover_node
        assert discover_node is not None

    @pytest.mark.asyncio
    async def test_discover_node_finds_agents(self):
        """discover_node finds agents for capabilities."""
        from agents.graph.nodes import discover_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )
        state["detected_capabilities"] = ["calculation"]
        state["subtasks"] = {"calculation": "5+3"}

        with patch("agents.graph.nodes.get_registry") as mock_get:
            mock_registry = MagicMock()
            mock_agent = MagicMock(id="calc-agent", name="Calculator")
            mock_registry.find_by_capability.return_value = [mock_agent]
            mock_get.return_value = mock_registry

            result = await discover_node(state, config={})

        assert "matches" in result
        assert len(result["matches"]) == 1
        assert result["matches"][0]["capability"] == "calculation"
        assert "calc-agent" in result["matches"][0]["agent_ids"]

    @pytest.mark.asyncio
    async def test_discover_node_handles_no_match(self):
        """discover_node handles capabilities with no matching agents."""
        from agents.graph.nodes import discover_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Do something unknown"
        )
        state["detected_capabilities"] = ["unknown_capability"]
        state["subtasks"] = {"unknown_capability": "do it"}

        with patch("agents.graph.nodes.get_registry") as mock_get:
            mock_registry = MagicMock()
            mock_registry.find_by_capability.return_value = []
            mock_get.return_value = mock_registry

            result = await discover_node(state, config={})

        assert "matches" in result
        assert len(result["matches"]) == 1
        assert result["matches"][0]["matched"] is False


class TestExecuteNode:
    """Tests for execute_node function."""

    @pytest.mark.asyncio
    async def test_execute_node_import(self):
        """execute_node can be imported."""
        from agents.graph.nodes import execute_node
        assert execute_node is not None

    @pytest.mark.asyncio
    async def test_execute_node_runs_agents(self):
        """execute_node runs agents for matched capabilities."""
        from agents.graph.nodes import execute_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3"
        )
        state["detected_capabilities"] = ["calculation"]
        state["subtasks"] = {"calculation": "5+3"}
        state["matches"] = [
            {"capability": "calculation", "agent_ids": ["calc"], "matched": True}
        ]

        with patch("agents.graph.nodes.get_executor") as mock_get:
            mock_executor = AsyncMock()
            mock_executor.execute_all.return_value = [
                MagicMock(
                    agent_id="calc",
                    agent_name="Calculator",
                    capability="calculation",
                    input_text="5+3",
                    output_text="8",
                    success=True,
                    duration_ms=50,
                    tokens={"input": 10, "output": 5}
                )
            ]
            mock_get.return_value = mock_executor

            result = await execute_node(state, config={})

        assert "executions" in result
        assert len(result["executions"]) == 1
        assert result["executions"][0]["output_text"] == "8"

    @pytest.mark.asyncio
    async def test_execute_node_respects_dependencies(self):
        """execute_node respects task dependencies if specified."""
        from agents.graph.nodes import execute_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Calculate 5+3 and write a haiku about the result"
        )
        state["detected_capabilities"] = ["calculation", "creative_writing"]
        state["subtasks"] = {
            "calculation": "5+3",
            "creative_writing": "write haiku about result"
        }
        state["matches"] = [
            {"capability": "calculation", "agent_ids": ["calc"], "matched": True},
            {"capability": "creative_writing", "agent_ids": ["writer"], "matched": True}
        ]
        # Dependencies: creative_writing depends on calculation
        state["dependencies"] = {"creative_writing": ["calculation"]}

        with patch("agents.graph.nodes.get_executor") as mock_get:
            mock_executor = AsyncMock()
            # Should be called with dependency context
            mock_executor.execute_with_dependencies.return_value = [
                MagicMock(
                    agent_id="calc",
                    output_text="8",
                    success=True
                ),
                MagicMock(
                    agent_id="writer",
                    output_text="Eight petals fall\nMathematics in the spring\nNumbers bloom with joy",
                    success=True
                )
            ]
            mock_get.return_value = mock_executor

            result = await execute_node(state, config={})

        assert "executions" in result


class TestSynthesizeNode:
    """Tests for synthesize_node function."""

    @pytest.mark.asyncio
    async def test_synthesize_node_import(self):
        """synthesize_node can be imported."""
        from agents.graph.nodes import synthesize_node
        assert synthesize_node is not None

    @pytest.mark.asyncio
    async def test_synthesize_node_integrates_outputs(self):
        """synthesize_node integrates multiple execution outputs."""
        from agents.graph.nodes import synthesize_node
        from agents.graph.state import create_initial_state

        state = create_initial_state(
            task_id="test-123",
            task="Research topic X"
        )
        state["executions"] = [
            {
                "agent_id": "web",
                "agent_name": "Web Agent",
                "capability": "research",
                "input_text": "research topic X",
                "output_text": "Web result",
                "duration_ms": 100,
                "success": True,
                "tokens": {"input": 10, "output": 20}
            },
            {
                "agent_id": "docs",
                "agent_name": "Docs Agent",
                "capability": "research",
                "input_text": "research topic X",
                "output_text": "Docs result",
                "duration_ms": 150,
                "success": True,
                "tokens": {"input": 15, "output": 25}
            },
        ]

        with patch("agents.graph.nodes.get_synthesizer") as mock_get:
            mock_synthesizer = AsyncMock()
            mock_synthesizer.synthesize.return_value = {
                "synthesized_output": "Combined: Web result + Docs result",
                "duration_ms": 100,
                "sources": ["web", "docs"],
                "tokens": {"input": 50, "output": 30}
            }
            mock_get.return_value = mock_synthesizer

            result = await synthesize_node(state, config={})

        assert "synthesis" in result
        assert "Combined" in result["synthesis"]["synthesized_output"]
        assert result["final_output"] == result["synthesis"]["synthesized_output"]


class TestShouldSynthesize:
    """Tests for should_synthesize conditional edge function."""

    def test_should_synthesize_import(self):
        """should_synthesize can be imported."""
        from agents.graph.nodes import should_synthesize
        assert should_synthesize is not None

    def test_should_synthesize_with_multiple_successful(self):
        """should_synthesize returns 'synthesize' with 2+ successful executions."""
        from agents.graph.nodes import should_synthesize
        from agents.graph.state import create_initial_state

        state = create_initial_state(task_id="test", task="test")
        state["executions"] = [
            {"agent_id": "a", "success": True},
            {"agent_id": "b", "success": True},
        ]

        result = should_synthesize(state)
        assert result == "synthesize"

    def test_should_synthesize_with_single_successful(self):
        """should_synthesize returns 'end' with only 1 successful execution."""
        from agents.graph.nodes import should_synthesize
        from agents.graph.state import create_initial_state

        state = create_initial_state(task_id="test", task="test")
        state["executions"] = [
            {"agent_id": "a", "success": True},
        ]

        result = should_synthesize(state)
        assert result == "end"

    def test_should_synthesize_with_no_successful(self):
        """should_synthesize returns 'end' with no successful executions."""
        from agents.graph.nodes import should_synthesize
        from agents.graph.state import create_initial_state

        state = create_initial_state(task_id="test", task="test")
        state["executions"] = [
            {"agent_id": "a", "success": False},
        ]

        result = should_synthesize(state)
        assert result == "end"

    def test_should_synthesize_mixed_results(self):
        """should_synthesize only counts successful executions."""
        from agents.graph.nodes import should_synthesize
        from agents.graph.state import create_initial_state

        state = create_initial_state(task_id="test", task="test")
        state["executions"] = [
            {"agent_id": "a", "success": True},
            {"agent_id": "b", "success": False},
            {"agent_id": "c", "success": True},
        ]

        result = should_synthesize(state)
        assert result == "synthesize"
