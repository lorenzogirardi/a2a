"""
Agent Registry - Central registry for agent discovery.

Provides:
- Agent registration and unregistration
- Discovery by ID
- Discovery by capabilities
- Listing and iteration
"""

from typing import Optional, Iterator
from .base import AgentBase


class AgentRegistry:
    """
    Central registry for discovering agents.

    Supports:
    - Registration with duplicate detection
    - Lookup by ID
    - Lookup by capabilities
    - Iteration over registered agents

    Example:
        registry = AgentRegistry()
        registry.register(EchoAgent("echo", storage))
        registry.register(CalculatorAgent("calc", storage))

        # Find by ID
        agent = registry.get("echo")

        # Find by capability
        calculators = registry.find_by_capability("calculation")

        # List all
        for agent_id in registry:
            print(agent_id)
    """

    def __init__(self):
        self._agents: dict[str, AgentBase] = {}

    def register(self, agent: AgentBase, replace: bool = False) -> None:
        """
        Register an agent in the registry.

        Args:
            agent: The agent to register
            replace: If True, replace existing agent with same ID

        Raises:
            ValueError: If agent ID already registered and replace=False
        """
        if agent.id in self._agents and not replace:
            raise ValueError(
                f"Agent '{agent.id}' already registered. "
                "Use replace=True to override."
            )

        self._agents[agent.id] = agent

    def unregister(self, agent_id: str) -> Optional[AgentBase]:
        """
        Remove an agent from the registry.

        Args:
            agent_id: ID of agent to remove

        Returns:
            The removed agent, or None if not found
        """
        return self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[AgentBase]:
        """
        Get an agent by ID.

        Args:
            agent_id: ID of the agent

        Returns:
            The agent, or None if not found
        """
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentBase]:
        """
        List all registered agents.

        Returns:
            List of all agents
        """
        return list(self._agents.values())

    def list_ids(self) -> list[str]:
        """
        List all registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self._agents.keys())

    def find_by_capability(self, capability: str) -> list[AgentBase]:
        """
        Find agents that have a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of agents with that capability
        """
        return [
            agent for agent in self._agents.values()
            if capability in agent.config.capabilities
        ]

    def find_by_capabilities(
        self,
        capabilities: list[str],
        match_all: bool = True
    ) -> list[AgentBase]:
        """
        Find agents by multiple capabilities.

        Args:
            capabilities: List of capabilities to search for
            match_all: If True, agent must have ALL capabilities.
                      If False, agent must have ANY capability.

        Returns:
            List of matching agents
        """
        result = []
        caps_set = set(capabilities)

        for agent in self._agents.values():
            agent_caps = set(agent.config.capabilities)

            if match_all:
                # Must have all
                if caps_set <= agent_caps:
                    result.append(agent)
            else:
                # Must have any
                if caps_set & agent_caps:
                    result.append(agent)

        return result

    def get_info(self, agent_id: str) -> Optional[dict]:
        """
        Get information about an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Dict with agent info, or None if not found
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        return {
            "id": agent.id,
            "name": agent.name,
            "description": agent.config.description,
            "capabilities": agent.config.capabilities
        }

    def get_all_info(self) -> dict[str, dict]:
        """
        Get information about all agents.

        Returns:
            Dict mapping agent_id -> info dict
        """
        return {
            agent_id: self.get_info(agent_id)
            for agent_id in self._agents
        }

    def items(self) -> Iterator[tuple[str, AgentBase]]:
        """Iterate over (id, agent) pairs."""
        return iter(self._agents.items())

    def __contains__(self, agent_id: str) -> bool:
        """Check if agent is registered."""
        return agent_id in self._agents

    def __len__(self) -> int:
        """Number of registered agents."""
        return len(self._agents)

    def __iter__(self) -> Iterator[str]:
        """Iterate over agent IDs."""
        return iter(self._agents)
