"""
Storage Base - Interfaccia astratta per salvare le informazioni degli agenti.

CONCETTO: Gli agenti devono poter salvare e recuperare informazioni.
Usando un'interfaccia astratta, possiamo cambiare implementazione
(memoria -> file -> database) senza modificare gli agenti.
"""

from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    """Messaggio scambiato tra agenti."""
    id: str
    sender: str           # ID dell'agente che invia
    receiver: str         # ID dell'agente che riceve
    content: str          # Contenuto del messaggio
    timestamp: datetime
    metadata: dict = {}   # Dati extra (es. permessi del caller)


class ConversationLog(BaseModel):
    """Log di una conversazione tra agenti."""
    conversation_id: str
    messages: list[Message] = []
    participants: list[str] = []
    created_at: datetime


class StorageBase(ABC):
    """
    Interfaccia base per lo storage.

    Ogni implementazione (memory, file, database) deve implementare questi metodi.
    """

    @abstractmethod
    async def save_message(self, message: Message) -> None:
        """Salva un messaggio."""
        pass

    @abstractmethod
    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Recupera tutti i messaggi di una conversazione."""
        pass

    @abstractmethod
    async def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Recupera lo stato salvato di un agente."""
        pass

    @abstractmethod
    async def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Salva lo stato di un agente."""
        pass

    @abstractmethod
    async def create_conversation(self, participants: list[str]) -> str:
        """Crea una nuova conversazione, ritorna l'ID."""
        pass
