"""Integration tests for PostgreSQL storage.

These tests require a running PostgreSQL instance.
Run: docker-compose up -d postgres
"""

import pytest
import os
from datetime import datetime

from storage.postgres import PostgresStorage
from storage.base import Message


# Skip if no PostgreSQL available
POSTGRES_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://a2a:a2a_dev_password@localhost:5432/a2a"
)


@pytest.fixture
async def storage():
    """Create a PostgresStorage instance and clean up after test."""
    storage = PostgresStorage(POSTGRES_URL)
    await storage.connect()

    # Clean tables before test
    await storage._execute("DELETE FROM messages")
    await storage._execute("DELETE FROM conversations")
    await storage._execute("DELETE FROM agent_states")

    yield storage

    await storage.disconnect()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPostgresStorageConversations:
    """Tests for conversation operations."""

    async def test_create_conversation(self, storage):
        """Should create conversation in database."""
        conv_id = await storage.create_conversation(["agent-a", "agent-b"])

        assert conv_id is not None
        assert len(conv_id) == 8

    async def test_create_conversation_persists(self, storage):
        """Should persist conversation data."""
        conv_id = await storage.create_conversation(["alice", "bob"])

        # Query directly
        row = await storage._fetchone(
            "SELECT participants FROM conversations WHERE id = $1",
            conv_id
        )

        assert row is not None
        assert set(row["participants"]) == {"alice", "bob"}


@pytest.mark.asyncio
@pytest.mark.integration
class TestPostgresStorageMessages:
    """Tests for message operations."""

    async def test_save_and_get_messages(self, storage):
        """Should save and retrieve messages."""
        conv_id = await storage.create_conversation(["a", "b"])

        msg = Message(
            id="msg-1",
            sender="a",
            receiver="b",
            content="Hello PostgreSQL!",
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        )

        await storage.save_message(msg)
        messages = await storage.get_messages(conv_id)

        assert len(messages) == 1
        assert messages[0].content == "Hello PostgreSQL!"
        assert messages[0].sender == "a"

    async def test_messages_ordered_by_timestamp(self, storage):
        """Messages should be returned in timestamp order."""
        conv_id = await storage.create_conversation(["x", "y"])

        for i in range(3):
            msg = Message(
                id=f"msg-{i}",
                sender="x",
                receiver="y",
                content=f"Message {i}",
                timestamp=datetime.now(),
                metadata={"conversation_id": conv_id}
            )
            await storage.save_message(msg)

        messages = await storage.get_messages(conv_id)

        assert len(messages) == 3
        # Should be in timestamp order
        contents = [m.content for m in messages]
        assert contents == ["Message 0", "Message 1", "Message 2"]

    async def test_get_messages_nonexistent(self, storage):
        """Should return empty list for nonexistent conversation."""
        messages = await storage.get_messages("nonexistent")
        assert messages == []


@pytest.mark.asyncio
@pytest.mark.integration
class TestPostgresStorageAgentState:
    """Tests for agent state operations."""

    async def test_save_and_get_state(self, storage):
        """Should save and retrieve agent state."""
        await storage.save_agent_state("agent-1", {"counter": 5, "name": "test"})

        state = await storage.get_agent_state("agent-1")

        assert state["counter"] == 5
        assert state["name"] == "test"

    async def test_state_merge(self, storage):
        """Subsequent saves should merge state."""
        await storage.save_agent_state("agent-x", {"a": 1})
        await storage.save_agent_state("agent-x", {"b": 2})

        state = await storage.get_agent_state("agent-x")

        assert state["a"] == 1
        assert state["b"] == 2

    async def test_get_state_nonexistent(self, storage):
        """Should return empty dict for nonexistent agent."""
        state = await storage.get_agent_state("nonexistent")
        assert state == {}


@pytest.mark.asyncio
@pytest.mark.integration
class TestPostgresStorageUtilities:
    """Tests for utility methods."""

    async def test_get_all_conversations(self, storage):
        """Should return all conversations."""
        await storage.create_conversation(["a", "b"])
        await storage.create_conversation(["c", "d"])

        convs = storage.get_all_conversations()
        assert len(convs) >= 2

    async def test_get_all_states(self, storage):
        """Should return all agent states."""
        await storage.save_agent_state("agent-1", {"x": 1})
        await storage.save_agent_state("agent-2", {"y": 2})

        states = storage.get_all_states()

        assert len(states) >= 2
        assert "agent-1" in states
        assert "agent-2" in states


@pytest.mark.asyncio
@pytest.mark.integration
class TestPostgresStorageConnection:
    """Tests for connection management."""

    async def test_connect_disconnect(self):
        """Should connect and disconnect cleanly."""
        storage = PostgresStorage(POSTGRES_URL)

        await storage.connect()
        assert storage._pool is not None

        await storage.disconnect()
        assert storage._pool is None

    async def test_context_manager(self):
        """Should work as async context manager."""
        async with PostgresStorage(POSTGRES_URL) as storage:
            conv_id = await storage.create_conversation(["test", "user"])
            assert conv_id is not None
