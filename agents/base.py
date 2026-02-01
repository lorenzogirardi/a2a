"""
Agent Base - Classe base per tutti gli agenti.

CONCETTO: Un agente è un'entità che può:
1. Ricevere messaggi (input)
2. Pensare/elaborare (think)
3. Agire/rispondere (act)
4. Salvare stato (memory)

Questa classe definisce l'interfaccia comune che tutti gli agenti devono seguire.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel

from storage.base import StorageBase, Message
from auth.permissions import (
    CallerContext,
    Permission,
    requires_permission,
    agent_context
)


class AgentConfig(BaseModel):
    """Configurazione di un agente."""
    id: str
    name: str
    description: str = ""
    capabilities: list[str] = []  # Cosa può fare questo agente


class AgentResponse(BaseModel):
    """Risposta di un agente."""
    content: str
    agent_id: str
    timestamp: datetime
    metadata: dict = {}


class AgentBase(ABC):
    """
    Classe base per tutti gli agenti.

    Ogni agente concreto deve implementare:
    - think(): logica di elaborazione
    - act(): azioni da compiere

    I metodi comuni (receive, respond, save_state) sono già implementati.
    """

    def __init__(self, config: AgentConfig, storage: StorageBase):
        self.config = config
        self.storage = storage
        self._internal_state: dict[str, Any] = {}

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    # ==================== METODI ASTRATTI ====================

    @abstractmethod
    async def think(self, message: Message) -> dict[str, Any]:
        """
        Elabora un messaggio e decide cosa fare.

        Returns:
            Un dizionario con:
            - 'response': testo della risposta
            - 'actions': lista di azioni da compiere
            - 'state_updates': modifiche allo stato interno
        """
        pass

    @abstractmethod
    async def act(self, actions: list[dict]) -> list[dict]:
        """
        Esegue le azioni decise in think().

        Args:
            actions: Lista di azioni da eseguire

        Returns:
            Lista di risultati delle azioni
        """
        pass

    # ==================== METODI COMUNI ====================

    @requires_permission(Permission.SEND_MESSAGES)
    async def receive_message(
        self,
        ctx: CallerContext,
        content: str,
        sender_id: str,
        conversation_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Riceve un messaggio e genera una risposta.

        Questo è il punto di ingresso principale per interagire con l'agente.
        """
        # Crea il messaggio
        message = Message(
            id=str(uuid.uuid4())[:8],
            sender=sender_id,
            receiver=self.id,
            content=content,
            timestamp=datetime.now(),
            metadata={
                "conversation_id": conversation_id or "default",
                "caller_context": ctx.model_dump()
            }
        )

        # Salva il messaggio in arrivo
        await self.storage.save_message(message)

        # Elabora il messaggio
        thought = await self.think(message)

        # Esegui eventuali azioni
        if thought.get("actions"):
            await self.act(thought["actions"])

        # Aggiorna lo stato se necessario
        if thought.get("state_updates"):
            await self._update_state(thought["state_updates"])

        # Crea e salva la risposta
        response_content = thought.get("response", "")

        response_message = Message(
            id=str(uuid.uuid4())[:8],
            sender=self.id,
            receiver=sender_id,
            content=response_content,
            timestamp=datetime.now(),
            metadata={"conversation_id": conversation_id or "default"}
        )
        await self.storage.save_message(response_message)

        return AgentResponse(
            content=response_content,
            agent_id=self.id,
            timestamp=response_message.timestamp,
            metadata=thought.get("metadata", {})
        )

    async def send_to_agent(
        self,
        target_agent: 'AgentBase',
        content: str,
        conversation_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Invia un messaggio a un altro agente.

        Crea automaticamente un contesto AGENT per la comunicazione.
        """
        # Quando un agente parla a un altro, usa il contesto AGENT
        ctx = agent_context(self.id)

        return await target_agent.receive_message(
            ctx=ctx,
            content=content,
            sender_id=self.id,
            conversation_id=conversation_id
        )

    @requires_permission(Permission.READ_STATE)
    async def get_state(self, ctx: CallerContext) -> dict[str, Any]:
        """Recupera lo stato dell'agente (con controllo permessi)."""
        saved_state = await self.storage.get_agent_state(self.id)
        return {**saved_state, **self._internal_state}

    async def _update_state(self, updates: dict[str, Any]) -> None:
        """Aggiorna lo stato interno e salva."""
        self._internal_state.update(updates)
        await self.storage.save_agent_state(self.id, updates)

    async def load_state(self) -> None:
        """Carica lo stato salvato dallo storage."""
        self._internal_state = await self.storage.get_agent_state(self.id)
        print(f"[Agent {self.id}] Stato caricato: {list(self._internal_state.keys())}")

    def __repr__(self) -> str:
        return f"<Agent {self.id}: {self.name}>"
