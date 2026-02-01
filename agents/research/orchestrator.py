"""Orchestrator agent for coordinating parallel searches."""
import asyncio
import time
from typing import Any, Optional

from agents.base import AgentBase, AgentConfig
from storage.base import StorageBase, Message
from auth.permissions import CallerContext, user_context

from .models import SearchResult, AggregatedResult
from .base import SearchAgentBase
from .web_search import WebSearchAgent
from .doc_search import DocSearchAgent
from .code_search import CodeSearchAgent
from .merge import MergeAgent


class OrchestratorAgent(AgentBase):
    """
    Orchestrator that coordinates parallel searches across multiple agents.

    Pattern: Fan-out/Fan-in
    1. Receives query
    2. Dispatches to multiple search agents in parallel
    3. Collects results
    4. Passes to MergeAgent for aggregation
    5. Returns unified result
    """

    def __init__(
        self,
        storage: StorageBase,
        search_agents: Optional[list[SearchAgentBase]] = None,
        timeout_seconds: float = 5.0
    ):
        config = AgentConfig(
            id="orchestrator",
            name="Research Orchestrator",
            description="Coordinates parallel searches across multiple sources",
            capabilities=["orchestrate", "parallel_search", "aggregate"]
        )
        super().__init__(config, storage)

        # Initialize search agents
        if search_agents is None:
            self.search_agents = [
                WebSearchAgent(storage),
                DocSearchAgent(storage),
                CodeSearchAgent(storage),
            ]
        else:
            self.search_agents = search_agents

        # Initialize merge agent
        self.merge_agent = MergeAgent(storage)

        # Timeout for individual searches
        self.timeout_seconds = timeout_seconds

    async def research(self, query: str) -> AggregatedResult:
        """
        Perform parallel research across all sources.

        Args:
            query: The search query

        Returns:
            AggregatedResult with merged results from all sources
        """
        start_time = time.time()

        # Create tasks for parallel execution
        async def search_with_timeout(agent: SearchAgentBase) -> tuple[str, list[SearchResult]]:
            try:
                results = await asyncio.wait_for(
                    agent.search(query),
                    timeout=self.timeout_seconds
                )
                return (agent.source_name, results)
            except asyncio.TimeoutError:
                print(f"[Orchestrator] Timeout for {agent.source_name} search")
                return (agent.source_name, [])
            except Exception as e:
                print(f"[Orchestrator] Error in {agent.source_name} search: {e}")
                return (agent.source_name, [])

        # Execute all searches in parallel
        tasks = [search_with_timeout(agent) for agent in self.search_agents]
        results = await asyncio.gather(*tasks)

        # Convert to dict
        results_by_source = {source: result_list for source, result_list in results}

        # Calculate search time
        search_time_ms = int((time.time() - start_time) * 1000)

        # Merge results
        aggregated = await self.merge_agent.merge_results(
            query=query,
            results_by_source=results_by_source,
            search_time_ms=search_time_ms
        )

        return aggregated

    async def think(self, message: Message) -> dict[str, Any]:
        """Process a research request."""
        query = message.content

        # Perform research
        result = await self.research(query)

        return {
            "response": result.summary,
            "actions": [],
            "state_updates": {
                "last_query": query,
                "last_result_count": result.total_results,
                "last_search_time_ms": result.search_time_ms
            },
            "metadata": {
                "aggregated_result": result.model_dump()
            }
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        """No actions for orchestrator."""
        return []


def create_research_system(storage: StorageBase) -> OrchestratorAgent:
    """
    Factory function to create a complete research system.

    Returns:
        Configured OrchestratorAgent with all search agents
    """
    return OrchestratorAgent(storage)
