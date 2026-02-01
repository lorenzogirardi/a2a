"""Integration tests for research pipeline."""

import pytest

from agents.research import OrchestratorAgent, create_research_system
from storage import MemoryStorage


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


@pytest.fixture
def orchestrator(storage):
    """Research orchestrator with all agents."""
    return create_research_system(storage)


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent orchestration."""

    @pytest.mark.asyncio
    async def test_research_returns_aggregated_result(self, orchestrator):
        """Research should return an AggregatedResult."""
        result = await orchestrator.research("python async")

        assert result.query == "python async"
        assert result.total_results > 0
        assert len(result.sources_searched) == 3
        assert result.search_time_ms >= 0

    @pytest.mark.asyncio
    async def test_research_searches_all_sources(self, orchestrator):
        """Should search web, docs, and code sources."""
        result = await orchestrator.research("python")

        sources = set(r.source for r in result.results)

        # Should have results from multiple sources
        assert len(sources) > 1
        assert "web" in result.sources_searched
        assert "docs" in result.sources_searched
        assert "code" in result.sources_searched

    @pytest.mark.asyncio
    async def test_research_results_sorted(self, orchestrator):
        """Results should be sorted by relevance."""
        result = await orchestrator.research("async agent")

        relevances = [r.relevance for r in result.results]
        assert relevances == sorted(relevances, reverse=True)

    @pytest.mark.asyncio
    async def test_research_generates_summary(self, orchestrator):
        """Should generate a meaningful summary."""
        result = await orchestrator.research("fastapi")

        assert result.summary is not None
        assert len(result.summary) > 0
        assert "fastapi" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_research_handles_unknown_query(self, orchestrator):
        """Should handle queries with no specific matches."""
        result = await orchestrator.research("xyznonexistent123abc")

        # Should still return results (generic ones)
        assert result.total_results > 0


class TestParallelExecution:
    """Tests for parallel search execution."""

    @pytest.mark.asyncio
    async def test_parallel_is_faster(self, storage):
        """Parallel execution should be faster than sequential."""
        import time

        orchestrator = OrchestratorAgent(storage)

        # Time the parallel research
        start = time.time()
        await orchestrator.research("python async patterns")
        elapsed = time.time() - start

        # Should complete quickly (mock searches are instant)
        # This mainly tests that gather works correctly
        assert elapsed < 1.0  # Should be very fast with mocks

    @pytest.mark.asyncio
    async def test_timeout_handling(self, storage):
        """Should handle slow agents gracefully."""
        import asyncio
        from agents.research import SearchAgentBase, SearchResult

        class SlowAgent(SearchAgentBase):
            source_name = "slow"

            def __init__(self, storage):
                super().__init__("slow-search", storage)

            async def search(self, query):
                await asyncio.sleep(10)  # Simulate slow search
                return []

        # Create orchestrator with short timeout
        orchestrator = OrchestratorAgent(
            storage,
            search_agents=[SlowAgent(storage)],
            timeout_seconds=0.1
        )

        # Should complete without hanging
        result = await orchestrator.research("test")

        # Slow agent should have been timed out
        assert result.total_results == 0


class TestResearchWithStorage:
    """Tests for research with storage integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_updates_state(self, orchestrator, storage):
        """Orchestrator should update its state."""
        from auth import user_context

        ctx = user_context("tester")

        # Use receive_message to trigger state update
        await orchestrator.receive_message(
            ctx=ctx,
            content="python async",
            sender_id="tester"
        )

        # Check state
        state = await orchestrator.get_state(ctx)
        assert state.get("last_query") == "python async"
        assert state.get("last_result_count") > 0
