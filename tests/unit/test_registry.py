"""Unit tests for AgentRegistry."""

import pytest

from agents.registry import AgentRegistry
from agents import EchoAgent, CounterAgent, CalculatorAgent
from storage import MemoryStorage


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


@pytest.fixture
def registry():
    """Fresh registry for each test."""
    return AgentRegistry()


@pytest.fixture
def populated_registry(registry, storage):
    """Registry with some agents."""
    echo = EchoAgent("echo", storage)
    counter = CounterAgent("counter", storage)
    calc = CalculatorAgent("calculator", storage)

    registry.register(echo)
    registry.register(counter)
    registry.register(calc)

    return registry


class TestAgentRegistration:
    """Tests for agent registration."""

    def test_register_agent(self, registry, storage):
        """Should register an agent."""
        agent = EchoAgent("test-echo", storage)
        registry.register(agent)

        assert "test-echo" in registry
        assert registry.get("test-echo") is agent

    def test_register_duplicate_raises(self, registry, storage):
        """Should raise on duplicate registration."""
        agent1 = EchoAgent("same-id", storage)
        agent2 = CounterAgent("same-id", storage)

        registry.register(agent1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(agent2)

    def test_register_duplicate_replace(self, registry, storage):
        """Should replace if replace=True."""
        agent1 = EchoAgent("replaceable", storage)
        agent2 = CounterAgent("replaceable", storage)

        registry.register(agent1)
        registry.register(agent2, replace=True)

        assert registry.get("replaceable") is agent2

    def test_unregister_agent(self, registry, storage):
        """Should unregister an agent."""
        agent = EchoAgent("to-remove", storage)
        registry.register(agent)

        removed = registry.unregister("to-remove")

        assert removed is agent
        assert "to-remove" not in registry

    def test_unregister_nonexistent(self, registry):
        """Should return None for nonexistent agent."""
        result = registry.unregister("nonexistent")
        assert result is None


class TestAgentDiscovery:
    """Tests for agent discovery."""

    def test_get_agent(self, populated_registry):
        """Should get agent by ID."""
        agent = populated_registry.get("echo")
        assert agent is not None
        assert agent.id == "echo"

    def test_get_nonexistent(self, populated_registry):
        """Should return None for nonexistent agent."""
        agent = populated_registry.get("nonexistent")
        assert agent is None

    def test_list_all(self, populated_registry):
        """Should list all agents."""
        agents = populated_registry.list_all()

        assert len(agents) == 3
        ids = [a.id for a in agents]
        assert "echo" in ids
        assert "counter" in ids
        assert "calculator" in ids

    def test_list_ids(self, populated_registry):
        """Should list all agent IDs."""
        ids = populated_registry.list_ids()

        assert set(ids) == {"echo", "counter", "calculator"}

    def test_contains(self, populated_registry):
        """Should support 'in' operator."""
        assert "echo" in populated_registry
        assert "nonexistent" not in populated_registry


class TestCapabilityDiscovery:
    """Tests for capability-based discovery."""

    def test_find_by_capability(self, populated_registry):
        """Should find agents by capability."""
        # Echo has 'echo', Counter has 'stateful', Calculator has 'calculation'
        agents = populated_registry.find_by_capability("echo")

        assert len(agents) == 1
        assert agents[0].id == "echo"

    def test_find_by_capability_multiple(self, populated_registry):
        """Should find multiple agents with same capability."""
        # Calculator has both 'calculate' and 'math'
        agents = populated_registry.find_by_capability("math")

        ids = [a.id for a in agents]
        assert "calculator" in ids

    def test_find_by_capability_none(self, populated_registry):
        """Should return empty list for unknown capability."""
        agents = populated_registry.find_by_capability("teleportation")
        assert agents == []

    def test_find_by_capabilities_all(self, populated_registry):
        """Should find agents with ALL specified capabilities."""
        # Calculator has both 'calculate' and 'math'
        agents = populated_registry.find_by_capabilities(
            ["calculate", "math"],
            match_all=True
        )

        assert len(agents) == 1
        assert agents[0].id == "calculator"

    def test_find_by_capabilities_any(self, populated_registry):
        """Should find agents with ANY specified capability."""
        agents = populated_registry.find_by_capabilities(
            ["echo", "calculate"],
            match_all=False
        )

        ids = [a.id for a in agents]
        assert "echo" in ids
        assert "calculator" in ids


class TestRegistryInfo:
    """Tests for registry information."""

    def test_get_info(self, populated_registry):
        """Should return info about an agent."""
        info = populated_registry.get_info("echo")

        assert info["id"] == "echo"
        assert "name" in info
        assert "description" in info
        assert "capabilities" in info

    def test_get_info_nonexistent(self, populated_registry):
        """Should return None for nonexistent agent."""
        info = populated_registry.get_info("nonexistent")
        assert info is None

    def test_get_all_info(self, populated_registry):
        """Should return info about all agents."""
        all_info = populated_registry.get_all_info()

        assert len(all_info) == 3
        assert "echo" in all_info
        assert all_info["echo"]["id"] == "echo"


class TestRegistryLen:
    """Tests for registry length."""

    def test_len_empty(self, registry):
        """Should return 0 for empty registry."""
        assert len(registry) == 0

    def test_len_populated(self, populated_registry):
        """Should return correct count."""
        assert len(populated_registry) == 3


class TestRegistryIteration:
    """Tests for iterating over registry."""

    def test_iter(self, populated_registry):
        """Should iterate over agent IDs."""
        ids = list(populated_registry)
        assert set(ids) == {"echo", "counter", "calculator"}

    def test_items(self, populated_registry):
        """Should iterate over (id, agent) pairs."""
        items = dict(populated_registry.items())

        assert len(items) == 3
        assert items["echo"].id == "echo"
