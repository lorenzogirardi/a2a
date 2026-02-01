"""
PostgreSQL Storage - Production-ready database storage.

Uses asyncpg for async PostgreSQL access.
Requires: pip install asyncpg

Connection string format:
    postgresql://user:password@host:port/database
"""

import uuid
import json
from datetime import datetime
from typing import Any, Optional

from .base import StorageBase, Message, ConversationLog


class PostgresStorage(StorageBase):
    """
    PostgreSQL storage implementation.

    Features:
    - Connection pooling
    - Async operations
    - JSON state storage
    - Transaction support

    Usage:
        storage = PostgresStorage("postgresql://user:pass@localhost/db")
        await storage.connect()
        # ... use storage ...
        await storage.disconnect()

    Or as context manager:
        async with PostgresStorage(url) as storage:
            await storage.create_conversation(["a", "b"])
    """

    def __init__(self, connection_url: str, min_pool_size: int = 2, max_pool_size: int = 10):
        self._connection_url = connection_url
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool = None

        # Cache for sync utility methods
        self._conversations_cache: dict[str, ConversationLog] = {}
        self._states_cache: dict[str, dict] = {}

    async def connect(self) -> None:
        """Establish connection pool."""
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "asyncpg is required for PostgresStorage. "
                "Install with: pip install asyncpg"
            )

        self._pool = await asyncpg.create_pool(
            self._connection_url,
            min_size=self._min_pool_size,
            max_size=self._max_pool_size
        )
        print(f"[PostgresStorage] Connected to database")

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            print(f"[PostgresStorage] Disconnected from database")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def _ensure_connected(self):
        """Raise if not connected."""
        if self._pool is None:
            raise RuntimeError(
                "Not connected to database. Call connect() first."
            )

    async def _execute(self, query: str, *args) -> str:
        """Execute a query."""
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchone(self, query: str, *args) -> Optional[dict]:
        """Fetch one row."""
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def _fetchall(self, query: str, *args) -> list[dict]:
        """Fetch all rows."""
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def create_conversation(self, participants: list[str]) -> str:
        """Create a new conversation."""
        conv_id = str(uuid.uuid4())[:8]

        await self._execute(
            """
            INSERT INTO conversations (id, participants, created_at)
            VALUES ($1, $2, $3)
            """,
            conv_id,
            participants,
            datetime.now()
        )

        # Update cache
        self._conversations_cache[conv_id] = ConversationLog(
            conversation_id=conv_id,
            participants=participants,
            created_at=datetime.now()
        )

        print(f"[PostgresStorage] Created conversation {conv_id}")
        return conv_id

    async def save_message(self, message: Message) -> None:
        """Save a message."""
        conv_id = message.metadata.get("conversation_id")

        if conv_id:
            # Check if conversation exists
            exists = await self._fetchone(
                "SELECT id FROM conversations WHERE id = $1",
                conv_id
            )
            if not exists:
                # Create conversation
                await self._execute(
                    """
                    INSERT INTO conversations (id, participants, created_at)
                    VALUES ($1, $2, $3)
                    """,
                    conv_id,
                    [message.sender, message.receiver],
                    datetime.now()
                )

        await self._execute(
            """
            INSERT INTO messages (id, conversation_id, sender, receiver, content, timestamp, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            message.id,
            conv_id,
            message.sender,
            message.receiver,
            message.content,
            message.timestamp,
            json.dumps(message.metadata)
        )

        print(f"[PostgresStorage] Saved message from {message.sender}")

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Get messages for a conversation."""
        rows = await self._fetchall(
            """
            SELECT id, sender, receiver, content, timestamp, metadata
            FROM messages
            WHERE conversation_id = $1
            ORDER BY timestamp ASC
            """,
            conversation_id
        )

        return [
            Message(
                id=row["id"],
                sender=row["sender"],
                receiver=row["receiver"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
            for row in rows
        ]

    async def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Get agent state."""
        row = await self._fetchone(
            "SELECT state FROM agent_states WHERE agent_id = $1",
            agent_id
        )

        if row is None:
            return {}

        state = row["state"]
        # asyncpg returns dict directly for JSONB
        return state if isinstance(state, dict) else json.loads(state)

    async def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Save agent state (merge with existing)."""
        current = await self.get_agent_state(agent_id)
        current.update(state)

        await self._execute(
            """
            INSERT INTO agent_states (agent_id, state, updated_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (agent_id)
            DO UPDATE SET state = $2, updated_at = $3
            """,
            agent_id,
            json.dumps(current),
            datetime.now()
        )

        # Update cache
        self._states_cache[agent_id] = current

        print(f"[PostgresStorage] Updated state for {agent_id}")

    def get_all_conversations(self) -> dict[str, ConversationLog]:
        """
        Get all conversations (sync, uses cache).

        Note: For full data, use async methods directly.
        """
        return self._conversations_cache

    def get_all_states(self) -> dict[str, dict]:
        """
        Get all states (sync, uses cache).

        Note: For full data, use async methods directly.
        """
        return self._states_cache

    async def refresh_cache(self) -> None:
        """Refresh caches from database."""
        # Refresh conversations
        rows = await self._fetchall(
            "SELECT id, participants, created_at FROM conversations"
        )
        self._conversations_cache = {
            row["id"]: ConversationLog(
                conversation_id=row["id"],
                participants=row["participants"],
                created_at=row["created_at"]
            )
            for row in rows
        }

        # Refresh states
        rows = await self._fetchall(
            "SELECT agent_id, state FROM agent_states"
        )
        self._states_cache = {
            row["agent_id"]: (
                row["state"] if isinstance(row["state"], dict)
                else json.loads(row["state"])
            )
            for row in rows
        }
