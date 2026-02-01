"""Unit tests for research agents."""

import pytest

from agents.research import (
    SearchResult,
    AggregatedResult,
    WebSearchAgent,
    DocSearchAgent,
    CodeSearchAgent,
    MergeAgent,
)
from storage import MemoryStorage


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self):
        """Should create a valid SearchResult."""
        result = SearchResult(
            source="web",
            title="Test Title",
            content="Test content",
            url="https://example.com",
            relevance=0.85
        )

        assert result.source == "web"
        assert result.title == "Test Title"
        assert result.relevance == 0.85

    def test_search_result_optional_fields(self):
        """Should handle optional fields."""
        result = SearchResult(
            source="code",
            title="Code Example",
            content="def foo(): pass",
            relevance=0.7
        )

        assert result.url is None
        assert result.metadata == {}


class TestWebSearchAgent:
    """Tests for WebSearchAgent."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, storage):
        """Should return results for a query."""
        agent = WebSearchAgent(storage)
        results = await agent.search("python")

        assert len(results) > 0
        assert all(r.source == "web" for r in results)

    @pytest.mark.asyncio
    async def test_search_results_sorted_by_relevance(self, storage):
        """Results should be sorted by relevance descending."""
        agent = WebSearchAgent(storage)
        results = await agent.search("python async")

        relevances = [r.relevance for r in results]
        assert relevances == sorted(relevances, reverse=True)

    @pytest.mark.asyncio
    async def test_search_generic_query(self, storage):
        """Should return generic results for unknown queries."""
        agent = WebSearchAgent(storage)
        results = await agent.search("xyznonexistent123")

        assert len(results) > 0


class TestDocSearchAgent:
    """Tests for DocSearchAgent."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, storage):
        """Should return documentation results."""
        agent = DocSearchAgent(storage)
        results = await agent.search("pydantic")

        assert len(results) > 0
        assert all(r.source == "docs" for r in results)

    @pytest.mark.asyncio
    async def test_search_async_docs(self, storage):
        """Should find async documentation."""
        agent = DocSearchAgent(storage)
        results = await agent.search("async")

        assert len(results) > 0
        assert any("asyncio" in r.title.lower() for r in results)


class TestCodeSearchAgent:
    """Tests for CodeSearchAgent."""

    @pytest.mark.asyncio
    async def test_search_returns_code(self, storage):
        """Should return code examples."""
        agent = CodeSearchAgent(storage)
        results = await agent.search("async")

        assert len(results) > 0
        assert all(r.source == "code" for r in results)

    @pytest.mark.asyncio
    async def test_code_results_have_metadata(self, storage):
        """Code results should have language metadata."""
        agent = CodeSearchAgent(storage)
        results = await agent.search("pydantic")

        for r in results:
            if r.metadata:
                assert "language" in r.metadata


class TestMergeAgent:
    """Tests for MergeAgent."""

    @pytest.fixture
    def merge_agent(self, storage):
        return MergeAgent(storage)

    @pytest.fixture
    def sample_results(self):
        return {
            "web": [
                SearchResult(source="web", title="Web Result 1", content="...", relevance=0.9),
                SearchResult(source="web", title="Web Result 2", content="...", relevance=0.7),
            ],
            "docs": [
                SearchResult(source="docs", title="Doc Result 1", content="...", relevance=0.85),
            ],
            "code": [
                SearchResult(source="code", title="Code Result 1", content="...", relevance=0.8),
            ],
        }

    @pytest.mark.asyncio
    async def test_merge_combines_results(self, merge_agent, sample_results):
        """Should combine results from all sources."""
        aggregated = await merge_agent.merge_results(
            query="test",
            results_by_source=sample_results,
            search_time_ms=100
        )

        assert aggregated.total_results == 4
        assert len(aggregated.sources_searched) == 3

    @pytest.mark.asyncio
    async def test_merge_sorts_by_relevance(self, merge_agent, sample_results):
        """Merged results should be sorted by relevance."""
        aggregated = await merge_agent.merge_results(
            query="test",
            results_by_source=sample_results,
            search_time_ms=100
        )

        relevances = [r.relevance for r in aggregated.results]
        assert relevances == sorted(relevances, reverse=True)

    @pytest.mark.asyncio
    async def test_merge_generates_summary(self, merge_agent, sample_results):
        """Should generate a summary."""
        aggregated = await merge_agent.merge_results(
            query="test query",
            results_by_source=sample_results,
            search_time_ms=100
        )

        assert "test query" in aggregated.summary
        assert "4" in aggregated.summary  # total results

    @pytest.mark.asyncio
    async def test_merge_handles_empty_sources(self, merge_agent):
        """Should handle sources with no results."""
        results_by_source = {
            "web": [SearchResult(source="web", title="Only", content="...", relevance=0.5)],
            "docs": [],
            "code": [],
        }

        aggregated = await merge_agent.merge_results(
            query="test",
            results_by_source=results_by_source,
            search_time_ms=50
        )

        assert aggregated.total_results == 1
        assert len(aggregated.sources_searched) == 3

    @pytest.mark.asyncio
    async def test_merge_removes_duplicates(self, merge_agent):
        """Should remove duplicate titles."""
        results_by_source = {
            "web": [SearchResult(source="web", title="Same Title", content="...", relevance=0.9)],
            "docs": [SearchResult(source="docs", title="Same Title", content="...", relevance=0.7)],
        }

        aggregated = await merge_agent.merge_results(
            query="test",
            results_by_source=results_by_source,
            search_time_ms=50
        )

        # Should keep only one (the higher relevance one)
        assert aggregated.total_results == 1
        assert aggregated.results[0].relevance == 0.9
