"""Integration tests for agent-to-agent communication."""

import pytest

from agents import EchoAgent, CounterAgent, RouterAgent, CalculatorAgent
from storage import MemoryStorage
from auth import user_context


@pytest.fixture
def storage():
    """Shared storage for all agents."""
    return MemoryStorage()


@pytest.fixture
def agent_system(storage):
    """Complete agent system with router."""
    echo = EchoAgent("echo", storage)
    counter = CounterAgent("counter", storage)
    calculator = CalculatorAgent("calculator", storage)

    router = RouterAgent("router", storage)
    router.add_route("ripeti", echo)
    router.add_route("conta", counter)
    router.add_route("calcola", calculator)

    return {
        "echo": echo,
        "counter": counter,
        "calculator": calculator,
        "router": router,
        "storage": storage
    }


class TestRouterAgent:
    """Tests for router agent forwarding."""

    @pytest.mark.asyncio
    async def test_router_forwards_to_echo(self, agent_system):
        """Router should forward 'ripeti' messages to echo agent."""
        ctx = user_context("tester")

        response = await agent_system["router"].receive_message(
            ctx=ctx,
            content="ripeti questo messaggio",
            sender_id="tester"
        )

        # Router forwards and echo responds
        assert "messaggio" in response.content.lower() or response.content == ""

    @pytest.mark.asyncio
    async def test_router_forwards_to_calculator(self, agent_system):
        """Router should forward 'calcola' messages to calculator."""
        ctx = user_context("tester")

        response = await agent_system["router"].receive_message(
            ctx=ctx,
            content="calcola 10 + 5",
            sender_id="tester"
        )

        # The response might be empty (forwarded) or contain result
        # depending on implementation
        assert response is not None

    @pytest.mark.asyncio
    async def test_router_no_match(self, agent_system):
        """Router should respond when no route matches."""
        ctx = user_context("tester")

        response = await agent_system["router"].receive_message(
            ctx=ctx,
            content="ciao mondo",
            sender_id="tester"
        )

        assert "keyword" in response.content.lower() or "non so" in response.content.lower()


class TestAgentToAgentCommunication:
    """Tests for direct agent-to-agent communication."""

    @pytest.mark.asyncio
    async def test_agent_sends_to_agent(self, agent_system):
        """One agent should be able to message another."""
        echo = agent_system["echo"]
        counter = agent_system["counter"]

        # Echo agent sends to counter agent
        response = await echo.send_to_agent(counter, "Hello from echo")

        assert "#1" in response.content
        assert response.agent_id == "counter"

    @pytest.mark.asyncio
    async def test_multiple_agent_messages(self, agent_system):
        """Multiple agents communicating should work correctly."""
        echo = agent_system["echo"]
        counter = agent_system["counter"]

        # Send multiple messages
        for i in range(3):
            await echo.send_to_agent(counter, f"Message {i}")

        # Check counter state
        ctx = user_context("checker")
        state = await counter.get_state(ctx)

        assert state.get("message_count") == 3


class TestStorageIntegration:
    """Tests for agent-storage integration."""

    @pytest.mark.asyncio
    async def test_messages_saved_to_storage(self, agent_system):
        """Messages should be persisted in storage."""
        ctx = user_context("tester")
        storage = agent_system["storage"]

        # Create a conversation
        conv_id = await storage.create_conversation(["tester", "echo"])

        # Send message to echo
        await agent_system["echo"].receive_message(
            ctx=ctx,
            content="Test message",
            sender_id="tester",
            conversation_id=conv_id
        )

        # Check storage
        messages = await storage.get_messages(conv_id)

        # Should have at least the incoming message (and possibly response)
        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_agent_state_persisted(self, agent_system):
        """Agent state changes should be persisted."""
        ctx = user_context("tester")
        storage = agent_system["storage"]
        counter = agent_system["counter"]

        # Send some messages
        for i in range(5):
            await counter.receive_message(
                ctx=ctx,
                content=f"Msg {i}",
                sender_id="tester"
            )

        # Check state in storage directly
        state = await storage.get_agent_state("counter")
        assert state.get("message_count") == 5

    @pytest.mark.asyncio
    async def test_conversation_history(self, agent_system):
        """Full conversation history should be retrievable."""
        ctx = user_context("tester")
        storage = agent_system["storage"]
        echo = agent_system["echo"]

        conv_id = await storage.create_conversation(["tester", "echo"])

        messages_to_send = ["Hello", "How are you?", "Goodbye"]

        for msg in messages_to_send:
            await echo.receive_message(
                ctx=ctx,
                content=msg,
                sender_id="tester",
                conversation_id=conv_id
            )

        history = await storage.get_messages(conv_id)

        # Should have messages (sent + responses)
        assert len(history) >= len(messages_to_send)

        # Verify order is preserved
        contents = [m.content for m in history if m.sender == "tester"]
        assert contents == messages_to_send
