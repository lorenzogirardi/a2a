"""Base class for search agents."""
from abc import abstractmethod
from typing import Any

from agents.base import AgentBase, AgentConfig
from storage.base import StorageBase, Message
from .models import SearchResult


class SearchAgentBase(AgentBase):
    """
    Base class for specialized search agents.

    Each search agent searches a specific source (web, docs, code)
    and returns structured SearchResult objects.
    """

    source_name: str = "unknown"

    def __init__(self, agent_id: str, storage: StorageBase):
        config = AgentConfig(
            id=agent_id,
            name=f"{self.source_name.title()} Search Agent",
            description=f"Searches {self.source_name} for relevant results",
            capabilities=["search", self.source_name]
        )
        super().__init__(config, storage)

    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]:
        """
        Search this source for the given query.

        Args:
            query: The search query

        Returns:
            List of SearchResult objects
        """
        pass

    async def think(self, message: Message) -> dict[str, Any]:
        """Process a search request."""
        query = message.content
        results = await self.search(query)

        return {
            "response": f"Found {len(results)} results for '{query}'",
            "actions": [],
            "state_updates": {
                "last_query": query,
                "last_result_count": len(results)
            },
            "metadata": {
                "results": [r.model_dump() for r in results]
            }
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        """No actions for search agents."""
        return []
