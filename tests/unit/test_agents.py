"""Unit tests for agents."""

import pytest
from datetime import datetime

from agents import EchoAgent, CounterAgent, CalculatorAgent
from agents.base import AgentConfig, AgentResponse
from storage import MemoryStorage
from auth import user_context, guest_context, admin_context, PermissionDenied


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


@pytest.fixture
def echo_agent(storage):
    """Echo agent instance."""
    return EchoAgent("test-echo", storage)


@pytest.fixture
def counter_agent(storage):
    """Counter agent instance."""
    return CounterAgent("test-counter", storage)


@pytest.fixture
def calculator_agent(storage):
    """Calculator agent instance."""
    return CalculatorAgent("test-calc", storage)


class TestEchoAgent:
    """Tests for EchoAgent."""

    @pytest.mark.asyncio
    async def test_echo_responds_with_message(self, echo_agent):
        """Echo agent should include the original message in response."""
        ctx = user_context("tester")
        response = await echo_agent.receive_message(
            ctx=ctx,
            content="Hello World",
            sender_id="tester"
        )

        assert isinstance(response, AgentResponse)
        assert "Hello World" in response.content
        assert response.agent_id == "test-echo"

    @pytest.mark.asyncio
    async def test_echo_saves_state(self, echo_agent):
        """Echo agent should save last message in state."""
        ctx = user_context("tester")
        await echo_agent.receive_message(
            ctx=ctx,
            content="Test message",
            sender_id="tester"
        )

        state = await echo_agent.get_state(ctx)
        assert state.get("last_message") == "Test message"


class TestCounterAgent:
    """Tests for CounterAgent."""

    @pytest.mark.asyncio
    async def test_counter_increments(self, counter_agent):
        """Counter should increment with each message."""
        ctx = user_context("tester")

        # First message
        response1 = await counter_agent.receive_message(
            ctx=ctx,
            content="First",
            sender_id="tester"
        )
        assert "#1" in response1.content

        # Second message
        response2 = await counter_agent.receive_message(
            ctx=ctx,
            content="Second",
            sender_id="tester"
        )
        assert "#2" in response2.content

    @pytest.mark.asyncio
    async def test_counter_persists_count(self, counter_agent):
        """Counter should persist count in state."""
        ctx = user_context("tester")

        for i in range(5):
            await counter_agent.receive_message(
                ctx=ctx,
                content=f"Message {i}",
                sender_id="tester"
            )

        state = await counter_agent.get_state(ctx)
        assert state.get("message_count") == 5


class TestCalculatorAgent:
    """Tests for CalculatorAgent."""

    @pytest.mark.asyncio
    async def test_addition(self, calculator_agent):
        """Calculator should handle addition."""
        ctx = user_context("tester")
        response = await calculator_agent.receive_message(
            ctx=ctx,
            content="calcola 5 + 3",
            sender_id="tester"
        )

        assert "8" in response.content

    @pytest.mark.asyncio
    async def test_multiplication(self, calculator_agent):
        """Calculator should handle multiplication."""
        ctx = user_context("tester")
        response = await calculator_agent.receive_message(
            ctx=ctx,
            content="quanto fa 7 * 6?",
            sender_id="tester"
        )

        assert "42" in response.content

    @pytest.mark.asyncio
    async def test_division(self, calculator_agent):
        """Calculator should handle division."""
        ctx = user_context("tester")
        response = await calculator_agent.receive_message(
            ctx=ctx,
            content="10 / 2",
            sender_id="tester"
        )

        assert "5" in response.content

    @pytest.mark.asyncio
    async def test_no_operation_found(self, calculator_agent):
        """Calculator should handle missing operations gracefully."""
        ctx = user_context("tester")
        response = await calculator_agent.receive_message(
            ctx=ctx,
            content="ciao come stai",
            sender_id="tester"
        )

        assert "non ho trovato" in response.content.lower() or "operazione" in response.content.lower()


class TestAgentPermissions:
    """Tests for agent permission system."""

    @pytest.mark.asyncio
    async def test_user_can_send_message(self, echo_agent):
        """User role should be able to send messages."""
        ctx = user_context("normal_user")
        response = await echo_agent.receive_message(
            ctx=ctx,
            content="Hello",
            sender_id="normal_user"
        )

        assert response.content is not None

    @pytest.mark.asyncio
    async def test_guest_cannot_send_message(self, echo_agent):
        """Guest role should not be able to send messages."""
        ctx = guest_context("visitor")

        with pytest.raises(PermissionDenied):
            await echo_agent.receive_message(
                ctx=ctx,
                content="Hello",
                sender_id="visitor"
            )

    @pytest.mark.asyncio
    async def test_guest_can_read_state(self, echo_agent):
        """Guest role should be able to read agent state."""
        # First, add some state
        admin = admin_context("admin")
        await echo_agent.receive_message(
            ctx=admin,
            content="Setup message",
            sender_id="admin"
        )

        # Guest should be able to read
        guest = guest_context("visitor")
        state = await echo_agent.get_state(guest)

        assert isinstance(state, dict)

    @pytest.mark.asyncio
    async def test_admin_can_do_everything(self, echo_agent):
        """Admin role should have all permissions."""
        ctx = admin_context("superuser")

        response = await echo_agent.receive_message(
            ctx=ctx,
            content="Admin message",
            sender_id="superuser"
        )
        assert response.content is not None

        state = await echo_agent.get_state(ctx)
        assert isinstance(state, dict)
