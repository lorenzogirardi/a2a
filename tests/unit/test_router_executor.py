"""Unit tests for TaskExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from agents.router.executor import TaskExecutor
from agents.router.models import CapabilityMatch
from agents.registry import AgentRegistry
from agents.base import AgentResponse


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.id = "test-agent"
    agent.name = "Test Agent"
    agent.config = MagicMock()
    agent.config.capabilities = ["calculation"]
    agent.receive_message = AsyncMock(return_value=AgentResponse(
        content="42",
        agent_id="test-agent",
        timestamp=datetime.now()
    ))
    return agent


@pytest.fixture
def executor(registry):
    return TaskExecutor(registry=registry)


class TestTaskExecutor:
    """Tests for TaskExecutor."""

    def test_init(self, executor, registry):
        """TaskExecutor should initialize with registry."""
        assert executor.registry == registry

    @pytest.mark.asyncio
    async def test_execute_on_agent(self, executor, mock_agent):
        """TaskExecutor should execute subtask on agent."""
        result = await executor.execute_on_agent(
            agent=mock_agent,
            capability="calculation",
            subtask="calculate 6 * 7",
            task_id="test-123"
        )

        assert result.success is True
        assert result.agent_id == "test-agent"
        assert result.output_text == "42"
        assert result.capability == "calculation"
        mock_agent.receive_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_on_agent_records_duration(self, executor, mock_agent):
        """TaskExecutor should record execution duration."""
        result = await executor.execute_on_agent(
            agent=mock_agent,
            capability="test",
            subtask="test task",
            task_id="test-dur"
        )

        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_on_agent_handles_error(self, executor, mock_agent):
        """TaskExecutor should handle agent errors gracefully."""
        mock_agent.receive_message = AsyncMock(side_effect=Exception("Agent error"))

        result = await executor.execute_on_agent(
            agent=mock_agent,
            capability="test",
            subtask="test task",
            task_id="test-err"
        )

        assert result.success is False
        assert "Agent error" in result.error

    @pytest.mark.asyncio
    async def test_execute_all(self, executor, registry, mock_agent):
        """TaskExecutor should execute all subtasks."""
        registry.register(mock_agent)

        matches = [
            CapabilityMatch(
                capability="calculation",
                agent_ids=["test-agent"],
                matched=True
            )
        ]
        subtasks = {"calculation": "calculate 6 * 7"}

        results = await executor.execute_all(
            matches=matches,
            subtasks=subtasks,
            task_id="test-all"
        )

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_execute_all_skips_unmatched(self, executor):
        """TaskExecutor should skip unmatched capabilities."""
        matches = [
            CapabilityMatch(
                capability="unknown",
                agent_ids=[],
                matched=False
            )
        ]
        subtasks = {"unknown": "do something"}

        results = await executor.execute_all(
            matches=matches,
            subtasks=subtasks,
            task_id="test-skip"
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_all_multiple_capabilities(self, executor, registry):
        """TaskExecutor should execute multiple capabilities."""
        agent1 = MagicMock()
        agent1.id = "calc-agent"
        agent1.name = "Calculator"
        agent1.config = MagicMock()
        agent1.config.capabilities = ["calculation"]
        agent1.receive_message = AsyncMock(return_value=AgentResponse(
            content="45",
            agent_id="calc-agent",
            timestamp=datetime.now()
        ))

        agent2 = MagicMock()
        agent2.id = "echo-agent"
        agent2.name = "Echo"
        agent2.config = MagicMock()
        agent2.config.capabilities = ["echo"]
        agent2.receive_message = AsyncMock(return_value=AgentResponse(
            content="hello",
            agent_id="echo-agent",
            timestamp=datetime.now()
        ))

        registry.register(agent1)
        registry.register(agent2)

        matches = [
            CapabilityMatch(capability="calculation", agent_ids=["calc-agent"], matched=True),
            CapabilityMatch(capability="echo", agent_ids=["echo-agent"], matched=True)
        ]
        subtasks = {
            "calculation": "15 * 3",
            "echo": "say hello"
        }

        results = await executor.execute_all(
            matches=matches,
            subtasks=subtasks,
            task_id="test-multi"
        )

        assert len(results) == 2
        assert all(r.success for r in results)


class TestTaskExecutorEvents:
    """Tests for TaskExecutor event emission."""

    @pytest.mark.asyncio
    async def test_emits_execution_started(self, registry, mock_agent):
        """TaskExecutor should emit execution_started event."""
        events = []
        executor = TaskExecutor(
            registry=registry,
            event_handler=lambda e: events.append(e)
        )

        await executor.execute_on_agent(
            agent=mock_agent,
            capability="test",
            subtask="test",
            task_id="test-evt"
        )

        assert any(e["event"] == "execution_started" for e in events)

    @pytest.mark.asyncio
    async def test_emits_execution_completed(self, registry, mock_agent):
        """TaskExecutor should emit execution_completed event."""
        events = []
        executor = TaskExecutor(
            registry=registry,
            event_handler=lambda e: events.append(e)
        )

        await executor.execute_on_agent(
            agent=mock_agent,
            capability="test",
            subtask="test",
            task_id="test-evt"
        )

        completed = [e for e in events if e["event"] == "execution_completed"]
        assert len(completed) == 1
        assert completed[0]["data"]["success"] is True
