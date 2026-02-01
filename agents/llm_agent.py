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
    LLM Agent che può usare tools definiti tramite Claude tool_use.

    Pattern:
    1. Riceve messaggio
    2. Claude decide se usare tool o rispondere
    3. Se tool_use: esegue tool, manda risultato a Claude
    4. Loop fino a risposta finale
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str = "Sei un assistente con accesso a tools. Usa i tools quando necessario.",
        model: str = "claude-sonnet-4-20250514",
        max_tool_rounds: int = 5
    ):
        super().__init__(agent_id, storage, system_prompt, model)
        self._tools: dict[str, dict] = {}  # name -> {schema, handler}
        self.max_tool_rounds = max_tool_rounds

    def add_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: callable
    ) -> None:
        """
        Aggiunge un tool che l'agente può usare.

        Args:
            name: Nome univoco del tool
            description: Descrizione per Claude
            input_schema: JSON Schema dei parametri
            handler: Funzione async da chiamare (riceve dict, ritorna str)
        """
        self._tools[name] = {
            "schema": {
                "name": name,
                "description": description,
                "input_schema": input_schema
            },
            "handler": handler
        }

    def _get_tool_schemas(self) -> list[dict]:
        """Ritorna gli schemas dei tools per Claude."""
        return [t["schema"] for t in self._tools.values()]

    async def _execute_tool(self, name: str, input_data: dict) -> str:
        """Esegue un tool e ritorna il risultato."""
        if name not in self._tools:
            return f"Error: Tool '{name}' not found"

        handler = self._tools[name]["handler"]
        try:
            # Handler può essere sync o async
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(input_data)
            else:
                result = handler(input_data)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    async def think(self, message: Message) -> dict[str, Any]:
        """Usa Claude con tool_use per elaborare il messaggio."""
        if not self._tools:
            # No tools, usa comportamento base
            return await super().think(message)

        try:
            client = self._get_client()

            # Costruisci contesto
            conversation_id = message.metadata.get("conversation_id", "default")
            history = await self.storage.get_messages(conversation_id)

            # Converti in formato Claude
            messages = []
            for msg in history[-10:]:
                role = "user" if msg.sender != self.id else "assistant"
                messages.append({"role": role, "content": msg.content})

            messages.append({"role": "user", "content": message.content})

            # Tool use loop
            tool_calls = []
            rounds = 0

            while rounds < self.max_tool_rounds:
                rounds += 1

                response = client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=self.system_prompt,
                    messages=messages,
                    tools=self._get_tool_schemas()
                )

                # Controlla stop_reason
                if response.stop_reason == "end_turn":
                    # Risposta finale
                    text_content = next(
                        (b.text for b in response.content if hasattr(b, "text")),
                        ""
                    )
                    return {
                        "response": text_content,
                        "actions": [],
                        "state_updates": {
                            "last_model": self.model,
                            "tool_calls": tool_calls
                        },
                        "metadata": {
                            "model": self.model,
                            "tool_rounds": rounds,
                            "tool_calls": tool_calls
                        }
                    }

                elif response.stop_reason == "tool_use":
                    # Estrai tool calls
                    tool_use_blocks = [
                        b for b in response.content
                        if hasattr(b, "type") and b.type == "tool_use"
                    ]

                    if not tool_use_blocks:
                        break

                    # Aggiungi risposta assistant ai messaggi
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Esegui ogni tool e raccogli risultati
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        tool_name = tool_block.name
                        tool_input = tool_block.input
                        tool_id = tool_block.id

                        result = await self._execute_tool(tool_name, tool_input)
                        tool_calls.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                    # Aggiungi risultati ai messaggi
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                else:
                    # Stop reason sconosciuto
                    break

            # Fallback se loop esaurito
            return {
                "response": "Reached maximum tool rounds without final response.",
                "actions": [],
                "state_updates": {"tool_calls": tool_calls},
                "metadata": {"tool_rounds": rounds, "tool_calls": tool_calls}
            }

        except Exception as e:
            return {
                "response": f"Errore nell'elaborazione: {str(e)}",
                "actions": [],
                "state_updates": {"last_error": str(e)}
            }

    async def act(self, actions: list[dict]) -> list[dict]:
        """Tools vengono eseguiti in think(), act() non usato."""
        return []
