"""
Memory Storage - Implementazione in memoria dello storage.

CONCETTO: Questa è l'implementazione più semplice, utile per:
- Sviluppo e debug
- Test
- Capire come funziona lo storage

I dati vengono persi al riavvio. Per persistenza, si può
estendere con FileStorage o DatabaseStorage.
"""

import uuid
from datetime import datetime
from typing import Any

from .base import StorageBase, Message, ConversationLog


class MemoryStorage(StorageBase):
    """
    Storage in memoria con struttura dati esplicita.

    Struttura interna:
    - conversations: {conv_id: ConversationLog}
    - agent_states: {agent_id: {key: value}}
    """

    def __init__(self):
        self._conversations: dict[str, ConversationLog] = {}
        self._agent_states: dict[str, dict[str, Any]] = {}

    async def create_conversation(self, participants: list[str]) -> str:
        """Crea una nuova conversazione tra i partecipanti."""
        conv_id = str(uuid.uuid4())[:8]  # ID corto per leggibilità

        self._conversations[conv_id] = ConversationLog(
            conversation_id=conv_id,
            participants=participants,
            created_at=datetime.now()
        )

        print(f"[Storage] Creata conversazione {conv_id} tra {participants}")
        return conv_id

    async def save_message(self, message: Message) -> None:
        """Salva un messaggio nella conversazione."""
        # Trova o crea la conversazione
        conv_id = message.metadata.get("conversation_id", "default")

        if conv_id not in self._conversations:
            await self.create_conversation([message.sender, message.receiver])
            conv_id = list(self._conversations.keys())[-1]

        self._conversations[conv_id].messages.append(message)
        print(f"[Storage] Salvato messaggio da {message.sender} a {message.receiver}")

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Recupera tutti i messaggi di una conversazione."""
        if conversation_id not in self._conversations:
            return []
        return self._conversations[conversation_id].messages

    async def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Recupera lo stato di un agente."""
        return self._agent_states.get(agent_id, {})

    async def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Salva lo stato di un agente (merge con esistente)."""
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = {}

        self._agent_states[agent_id].update(state)
        print(f"[Storage] Aggiornato stato di {agent_id}: {list(state.keys())}")

    def get_all_conversations(self) -> dict[str, ConversationLog]:
        """Utility per debug: vedi tutte le conversazioni."""
        return self._conversations

    def get_all_states(self) -> dict[str, dict]:
        """Utility per debug: vedi tutti gli stati."""
        return self._agent_states
