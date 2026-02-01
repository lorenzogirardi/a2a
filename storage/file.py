"""
File Storage - Implementazione su filesystem dello storage.

Persiste i dati su file JSON per:
- Durabilità tra riavvii
- Debug (file leggibili)
- Backup semplice

Struttura:
    base_path/
    ├── conversations/
    │   └── {conv_id}.json
    └── states/
        └── {agent_id}.json
"""

import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import StorageBase, Message, ConversationLog


class FileStorage(StorageBase):
    """
    Storage su filesystem con file JSON.

    Thread-safe per operazioni async tramite lock.
    """

    def __init__(self, base_path: Path | str = "data"):
        self.base_path = Path(base_path)
        self._conversations_path = self.base_path / "conversations"
        self._states_path = self.base_path / "states"

        # Create directories
        self._conversations_path.mkdir(parents=True, exist_ok=True)
        self._states_path.mkdir(parents=True, exist_ok=True)

        # Lock for file operations
        self._lock = asyncio.Lock()

    def _conv_file(self, conv_id: str) -> Path:
        """Path to conversation file."""
        return self._conversations_path / f"{conv_id}.json"

    def _state_file(self, agent_id: str) -> Path:
        """Path to agent state file."""
        return self._states_path / f"{agent_id}.json"

    def _serialize_datetime(self, obj: Any) -> Any:
        """JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _load_conversation(self, conv_id: str) -> ConversationLog | None:
        """Load conversation from file."""
        path = self._conv_file(conv_id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct messages
        messages = [
            Message(
                id=m["id"],
                sender=m["sender"],
                receiver=m["receiver"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {})
            )
            for m in data.get("messages", [])
        ]

        return ConversationLog(
            conversation_id=data["conversation_id"],
            messages=messages,
            participants=data["participants"],
            created_at=datetime.fromisoformat(data["created_at"])
        )

    def _save_conversation(self, conv: ConversationLog) -> None:
        """Save conversation to file."""
        path = self._conv_file(conv.conversation_id)

        data = {
            "conversation_id": conv.conversation_id,
            "participants": conv.participants,
            "created_at": conv.created_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "receiver": m.receiver,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata
                }
                for m in conv.messages
            ]
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def create_conversation(self, participants: list[str]) -> str:
        """Crea una nuova conversazione tra i partecipanti."""
        async with self._lock:
            conv_id = str(uuid.uuid4())[:8]

            conv = ConversationLog(
                conversation_id=conv_id,
                participants=participants,
                created_at=datetime.now()
            )

            self._save_conversation(conv)
            print(f"[FileStorage] Creata conversazione {conv_id} tra {participants}")
            return conv_id

    async def save_message(self, message: Message) -> None:
        """Salva un messaggio nella conversazione."""
        async with self._lock:
            conv_id = message.metadata.get("conversation_id", "default")

            conv = self._load_conversation(conv_id)
            if conv is None:
                # Create new conversation
                conv_id = str(uuid.uuid4())[:8]
                conv = ConversationLog(
                    conversation_id=conv_id,
                    participants=[message.sender, message.receiver],
                    created_at=datetime.now()
                )

            conv.messages.append(message)
            self._save_conversation(conv)
            print(f"[FileStorage] Salvato messaggio da {message.sender} a {message.receiver}")

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Recupera tutti i messaggi di una conversazione."""
        conv = self._load_conversation(conversation_id)
        if conv is None:
            return []
        return conv.messages

    async def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Recupera lo stato di un agente."""
        path = self._state_file(agent_id)
        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Salva lo stato di un agente (merge con esistente)."""
        async with self._lock:
            current = await self.get_agent_state(agent_id)
            current.update(state)

            path = self._state_file(agent_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2, default=self._serialize_datetime)

            print(f"[FileStorage] Aggiornato stato di {agent_id}: {list(state.keys())}")

    def get_all_conversations(self) -> dict[str, ConversationLog]:
        """Utility: ritorna tutte le conversazioni."""
        result = {}
        for path in self._conversations_path.glob("*.json"):
            conv_id = path.stem
            conv = self._load_conversation(conv_id)
            if conv:
                result[conv_id] = conv
        return result

    def get_all_states(self) -> dict[str, dict]:
        """Utility: ritorna tutti gli stati degli agenti."""
        result = {}
        for path in self._states_path.glob("*.json"):
            agent_id = path.stem
            with open(path, "r", encoding="utf-8") as f:
                result[agent_id] = json.load(f)
        return result
