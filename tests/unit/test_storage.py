"""Unit tests for storage layer."""

import pytest
from datetime import datetime

from storage import MemoryStorage, Message, ConversationLog


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


class TestMemoryStorage:
    """Tests for MemoryStorage."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, storage):
        """Should create a conversation and return ID."""
        conv_id = await storage.create_conversation(["alice", "bob"])

        assert conv_id is not None
        assert len(conv_id) == 8  # Short UUID

    @pytest.mark.asyncio
    async def test_save_and_get_messages(self, storage):
        """Should save and retrieve messages."""
        conv_id = await storage.create_conversation(["alice", "bob"])

        message = Message(
            id="msg-1",
            sender="alice",
            receiver="bob",
            content="Hello Bob!",
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        )

        await storage.save_message(message)

        messages = await storage.get_messages(conv_id)
        assert len(messages) == 1
        assert messages[0].content == "Hello Bob!"
        assert messages[0].sender == "alice"

    @pytest.mark.asyncio
    async def test_multiple_messages(self, storage):
        """Should handle multiple messages in a conversation."""
        conv_id = await storage.create_conversation(["alice", "bob"])

        for i in range(5):
            message = Message(
                id=f"msg-{i}",
                sender="alice" if i % 2 == 0 else "bob",
                receiver="bob" if i % 2 == 0 else "alice",
                content=f"Message {i}",
                timestamp=datetime.now(),
                metadata={"conversation_id": conv_id}
            )
            await storage.save_message(message)

        messages = await storage.get_messages(conv_id)
        assert len(messages) == 5

    @pytest.mark.asyncio
    async def test_agent_state_save_and_get(self, storage):
        """Should save and retrieve agent state."""
        await storage.save_agent_state("agent-1", {"count": 5, "name": "Test"})

        state = await storage.get_agent_state("agent-1")
        assert state["count"] == 5
        assert state["name"] == "Test"

    @pytest.mark.asyncio
    async def test_agent_state_merge(self, storage):
        """Should merge state updates."""
        await storage.save_agent_state("agent-1", {"count": 5})
        await storage.save_agent_state("agent-1", {"name": "Test"})

        state = await storage.get_agent_state("agent-1")
        assert state["count"] == 5
        assert state["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_state(self, storage):
        """Should return empty dict for nonexistent agent."""
        state = await storage.get_agent_state("nonexistent")
        assert state == {}

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, storage):
        """Should return empty list for nonexistent conversation."""
        messages = await storage.get_messages("nonexistent")
        assert messages == []

    def test_get_all_conversations(self, storage):
        """Should return all conversations."""
        import asyncio

        async def setup():
            await storage.create_conversation(["a", "b"])
            await storage.create_conversation(["c", "d"])

        asyncio.get_event_loop().run_until_complete(setup())

        convs = storage.get_all_conversations()
        assert len(convs) == 2

    def test_get_all_states(self, storage):
        """Should return all agent states."""
        import asyncio

        async def setup():
            await storage.save_agent_state("agent-1", {"x": 1})
            await storage.save_agent_state("agent-2", {"y": 2})

        asyncio.get_event_loop().run_until_complete(setup())

        states = storage.get_all_states()
        assert len(states) == 2
        assert "agent-1" in states
        assert "agent-2" in states
