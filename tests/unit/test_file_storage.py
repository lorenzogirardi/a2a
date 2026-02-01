"""Unit tests for FileStorage."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from storage.file import FileStorage
from storage.base import Message


@pytest.fixture
def temp_dir():
    """Create a temporary directory for each test."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path)


@pytest.fixture
def storage(temp_dir):
    """FileStorage instance with temp directory."""
    return FileStorage(base_path=temp_dir)


class TestFileStorageConversations:
    """Tests for conversation operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, storage, temp_dir):
        """Should create conversation and persist to file."""
        conv_id = await storage.create_conversation(["agent-a", "agent-b"])

        assert conv_id is not None
        assert len(conv_id) == 8

        # File should exist
        conv_file = temp_dir / "conversations" / f"{conv_id}.json"
        assert conv_file.exists()

    @pytest.mark.asyncio
    async def test_create_conversation_persists_participants(self, storage):
        """Participants should be persisted."""
        conv_id = await storage.create_conversation(["alice", "bob", "charlie"])

        # Create new storage instance to verify persistence
        storage2 = FileStorage(base_path=storage.base_path)
        convs = storage2.get_all_conversations()

        assert conv_id in convs
        assert set(convs[conv_id].participants) == {"alice", "bob", "charlie"}


class TestFileStorageMessages:
    """Tests for message operations."""

    @pytest.mark.asyncio
    async def test_save_message(self, storage):
        """Should save message to conversation file."""
        conv_id = await storage.create_conversation(["a", "b"])

        msg = Message(
            id="msg-1",
            sender="a",
            receiver="b",
            content="Hello",
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        )

        await storage.save_message(msg)
        messages = await storage.get_messages(conv_id)

        assert len(messages) == 1
        assert messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_messages_persist_across_instances(self, storage, temp_dir):
        """Messages should persist when storage is recreated."""
        conv_id = await storage.create_conversation(["x", "y"])

        msg = Message(
            id="msg-persist",
            sender="x",
            receiver="y",
            content="Persistent message",
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        )
        await storage.save_message(msg)

        # New instance
        storage2 = FileStorage(base_path=temp_dir)
        messages = await storage2.get_messages(conv_id)

        assert len(messages) == 1
        assert messages[0].content == "Persistent message"

    @pytest.mark.asyncio
    async def test_get_messages_nonexistent(self, storage):
        """Should return empty list for nonexistent conversation."""
        messages = await storage.get_messages("nonexistent")
        assert messages == []


class TestFileStorageAgentState:
    """Tests for agent state operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_state(self, storage):
        """Should save and retrieve agent state."""
        await storage.save_agent_state("agent-1", {"counter": 5, "name": "test"})

        state = await storage.get_agent_state("agent-1")

        assert state["counter"] == 5
        assert state["name"] == "test"

    @pytest.mark.asyncio
    async def test_state_persists_across_instances(self, storage, temp_dir):
        """State should persist when storage is recreated."""
        await storage.save_agent_state("persistent-agent", {"value": 42})

        # New instance
        storage2 = FileStorage(base_path=temp_dir)
        state = await storage2.get_agent_state("persistent-agent")

        assert state["value"] == 42

    @pytest.mark.asyncio
    async def test_state_merge(self, storage):
        """Subsequent saves should merge state."""
        await storage.save_agent_state("agent-x", {"a": 1})
        await storage.save_agent_state("agent-x", {"b": 2})

        state = await storage.get_agent_state("agent-x")

        assert state["a"] == 1
        assert state["b"] == 2

    @pytest.mark.asyncio
    async def test_get_state_nonexistent(self, storage):
        """Should return empty dict for nonexistent agent."""
        state = await storage.get_agent_state("nonexistent")
        assert state == {}


class TestFileStorageUtilities:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_get_all_conversations(self, storage):
        """Should return all conversations."""
        await storage.create_conversation(["a", "b"])
        await storage.create_conversation(["c", "d"])

        convs = storage.get_all_conversations()
        assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_get_all_states(self, storage):
        """Should return all agent states."""
        await storage.save_agent_state("agent-1", {"x": 1})
        await storage.save_agent_state("agent-2", {"y": 2})

        states = storage.get_all_states()

        assert len(states) == 2
        assert "agent-1" in states
        assert "agent-2" in states


class TestFileStorageEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, storage):
        """Should handle rapid sequential writes."""
        import asyncio

        conv_id = await storage.create_conversation(["sender", "receiver"])

        async def send_message(i):
            msg = Message(
                id=f"msg-{i}",
                sender="sender",
                receiver="receiver",
                content=f"Message {i}",
                timestamp=datetime.now(),
                metadata={"conversation_id": conv_id}
            )
            await storage.save_message(msg)

        await asyncio.gather(*[send_message(i) for i in range(10)])

        messages = await storage.get_messages(conv_id)
        assert len(messages) == 10

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, storage):
        """Should handle special characters in message content."""
        conv_id = await storage.create_conversation(["a", "b"])

        msg = Message(
            id="msg-special",
            sender="a",
            receiver="b",
            content='Special: "quotes", newline\n, unicode: 你好 🎉',
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        )
        await storage.save_message(msg)

        messages = await storage.get_messages(conv_id)
        assert messages[0].content == msg.content
