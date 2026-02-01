"""
LLM Agent - Agente basato su Large Language Model.

CONCETTO: Questo agente usa un LLM (Claude) per decidere cosa fare.
A differenza degli agenti semplici, può:
- Capire linguaggio naturale
- Ragionare su problemi complessi
- Generare risposte creative

Per ora è uno stub - verrà implementato quando aggiungerai anthropic ai requirements.
"""

from typing import Any, Optional
import os

from storage.base import StorageBase, Message
from .base import AgentBase, AgentConfig


class LLMAgent(AgentBase):
    """
    Agente che usa Claude per elaborare i messaggi.

    Richiede: pip install anthropic
    E la variabile d'ambiente ANTHROPIC_API_KEY
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str = "Sei un assistente utile.",
        model: str = "claude-sonnet-4-20250514"
    ):
        config = AgentConfig(
            id=agent_id,
            name=f"LLM Agent ({agent_id})",
            description="Agente basato su Claude",
            capabilities=["conversation", "reasoning", "generation"]
        )
        super().__init__(config, storage)

        self.system_prompt = system_prompt
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy initialization del client Anthropic."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic()
            except ImportError:
                raise ImportError(
                    "Per usare LLMAgent installa anthropic: pip install anthropic"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Errore inizializzazione client Anthropic: {e}. "
                    "Assicurati di avere ANTHROPIC_API_KEY impostata."
                )
        return self._client

    async def think(self, message: Message) -> dict[str, Any]:
        """Usa Claude per elaborare il messaggio."""
        try:
            client = self._get_client()

            # Costruisci il contesto dalla cronologia
            conversation_id = message.metadata.get("conversation_id", "default")
            history = await self.storage.get_messages(conversation_id)

            # Converti in formato Claude
            messages = []
            for msg in history[-10:]:  # Ultimi 10 messaggi per contesto
                role = "user" if msg.sender != self.id else "assistant"
                messages.append({"role": role, "content": msg.content})

            # Aggiungi il messaggio corrente
            messages.append({"role": "user", "content": message.content})

            # Chiama Claude
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages
            )

            response_text = response.content[0].text

            return {
                "response": response_text,
                "actions": [],  # LLM agent base non esegue azioni
                "state_updates": {
                    "last_model": self.model,
                    "last_tokens": response.usage.output_tokens
                },
                "metadata": {
                    "model": self.model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    }
                }
            }

        except Exception as e:
            return {
                "response": f"Errore nell'elaborazione: {str(e)}",
                "actions": [],
                "state_updates": {"last_error": str(e)}
            }

    async def act(self, actions: list[dict]) -> list[dict]:
        """LLM Agent base non esegue azioni."""
        return []


class ToolUsingLLMAgent(LLMAgent):
    """
    LLM Agent che può usare tools definiti.

    TODO: Implementare quando si aggiunge il supporto tools.
    Questo è il pattern per agenti più avanzati che possono
    chiamare funzioni/API in base al ragionamento dell'LLM.
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str = "Sei un assistente con accesso a tools.",
        tools: list[dict] = None
    ):
        super().__init__(agent_id, storage, system_prompt)
        self.tools = tools or []

    def add_tool(self, name: str, description: str, handler: callable):
        """Aggiunge un tool che l'agente può usare."""
        self.tools.append({
            "name": name,
            "description": description,
            "handler": handler
        })

    async def act(self, actions: list[dict]) -> list[dict]:
        """Esegue tools chiamati dall'LLM."""
        # TODO: Implementare esecuzione tools
        # Questo richiede il supporto tool_use di Claude
        return []
