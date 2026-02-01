"""Merge agent for aggregating search results."""
from typing import Any
from datetime import datetime

from agents.base import AgentBase, AgentConfig
from storage.base import StorageBase, Message
from .models import SearchResult, AggregatedResult


class MergeAgent(AgentBase):
    """
    Agent that merges results from multiple search agents.

    Responsibilities:
    - Combine results from different sources
    - Sort by relevance
    - Remove duplicates
    - Generate summary
    """

    def __init__(self, storage: StorageBase):
        config = AgentConfig(
            id="merge",
            name="Merge Agent",
            description="Aggregates and summarizes search results from multiple sources",
            capabilities=["merge", "aggregate", "summarize"]
        )
        super().__init__(config, storage)

    async def merge_results(
        self,
        query: str,
        results_by_source: dict[str, list[SearchResult]],
        search_time_ms: int
    ) -> AggregatedResult:
        """
        Merge results from multiple sources into a single aggregated result.

        Args:
            query: Original search query
            results_by_source: Dict of source -> results
            search_time_ms: Total search time

        Returns:
            AggregatedResult with combined, sorted results
        """
        # Flatten all results
        all_results: list[SearchResult] = []
        sources_searched = []

        for source, results in results_by_source.items():
            sources_searched.append(source)
            all_results.extend(results)

        # Sort by relevance (descending)
        all_results.sort(key=lambda x: x.relevance, reverse=True)

        # Remove duplicates by title (keep highest relevance)
        seen_titles = set()
        unique_results = []
        for result in all_results:
            if result.title not in seen_titles:
                seen_titles.add(result.title)
                unique_results.append(result)

        # Generate summary
        summary = self._generate_summary(query, unique_results, sources_searched)

        return AggregatedResult(
            query=query,
            results=unique_results,
            summary=summary,
            search_time_ms=search_time_ms,
            sources_searched=sources_searched,
            total_results=len(unique_results)
        )

    def _generate_summary(
        self,
        query: str,
        results: list[SearchResult],
        sources: list[str]
    ) -> str:
        """Generate a summary of the search results."""
        if not results:
            return f"No results found for '{query}'."

        # Count by source
        source_counts = {}
        for r in results:
            source_counts[r.source] = source_counts.get(r.source, 0) + 1

        # Build summary
        parts = [f"Found {len(results)} results for '{query}'"]

        source_parts = []
        for source in sources:
            count = source_counts.get(source, 0)
            source_parts.append(f"{count} from {source}")

        if source_parts:
            parts.append(f" ({', '.join(source_parts)})")

        # Add top result info
        if results:
            top = results[0]
            parts.append(f". Top result: '{top.title}' (relevance: {top.relevance:.2f})")

        return "".join(parts)

    async def think(self, message: Message) -> dict[str, Any]:
        """Process merge request (used when called as regular agent)."""
        # This is called if MergeAgent is used via receive_message
        # In practice, merge_results is called directly by Orchestrator
        return {
            "response": "MergeAgent is designed to be called via merge_results()",
            "actions": [],
            "state_updates": {}
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        """No actions for merge agent."""
        return []
