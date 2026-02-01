"""
LLM Agent - Agente basato su Large Language Model.

Usa LiteLLM per supportare multipli provider LLM (Claude, OpenAI, Ollama, ecc.)
con un'interfaccia unificata.

Configurazione via variabili d'ambiente:
- ANTHROPIC_API_KEY: per modelli Claude
- OPENAI_API_KEY: per modelli OpenAI
- LITELLM_API_BASE: per proxy custom
"""

from typing import Any
import asyncio

from storage.base import StorageBase, Message
from .base import AgentBase, AgentConfig


class LLMAgent(AgentBase):
    """
    Agente che usa LiteLLM per elaborare i messaggi.

    Supporta multipli provider:
    - Claude: model="claude-sonnet-4-5" (richiede ANTHROPIC_API_KEY)
    - OpenAI: model="gpt-4" (richiede OPENAI_API_KEY)
    - Ollama: model="ollama/llama2" (richiede server Ollama)

    LiteLLM gestisce automaticamente il routing basato sul nome del modello.
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str = "Sei un assistente utile.",
        model: str = "claude-sonnet-4-5"
    ):
        config = AgentConfig(
            id=agent_id,
            name=f"LLM Agent ({agent_id})",
            description="Agente basato su LLM",
            capabilities=["conversation", "reasoning", "generation"]
        )
        super().__init__(config, storage)

        self.system_prompt = system_prompt
        self.model = model

    async def think(self, message: Message) -> dict[str, Any]:
        """Usa LiteLLM per elaborare il messaggio."""
        try:
            import litellm

            # Costruisci il contesto dalla cronologia
            conversation_id = message.metadata.get("conversation_id", "default")
            history = await self.storage.get_messages(conversation_id)

            # Costruisci messaggi in formato OpenAI (usato da LiteLLM)
            messages = [{"role": "system", "content": self.system_prompt}]

            for msg in history[-10:]:  # Ultimi 10 messaggi per contesto
                role = "user" if msg.sender != self.id else "assistant"
                messages.append({"role": role, "content": msg.content})

            # Aggiungi il messaggio corrente
            messages.append({"role": "user", "content": message.content})

            # Chiama LLM via LiteLLM
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                max_tokens=1024
            )

            response_text = response.choices[0].message.content
            usage = response.usage

            return {
                "response": response_text,
                "actions": [],
                "state_updates": {
                    "last_model": self.model,
                    "last_tokens": usage.completion_tokens if usage else 0
                },
                "metadata": {
                    "model": self.model,
                    "usage": {
                        "input_tokens": usage.prompt_tokens if usage else 0,
                        "output_tokens": usage.completion_tokens if usage else 0
                    }
                }
            }

        except ImportError:
            return {
                "response": "Errore: litellm non installato. Esegui: pip install litellm",
                "actions": [],
                "state_updates": {"last_error": "litellm not installed"}
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
    LLM Agent che può usare tools.

    Pattern:
    1. Riceve messaggio
    2. LLM decide se usare tool o rispondere
    3. Se tool_use: esegue tool, manda risultato a LLM
    4. Loop fino a risposta finale

    Nota: Il supporto tool varia per provider. Claude e OpenAI supportano tools,
    altri provider potrebbero non supportarli.
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str = "Sei un assistente con accesso a tools. Usa i tools quando necessario.",
        model: str = "claude-sonnet-4-5",
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
            description: Descrizione per l'LLM
            input_schema: JSON Schema dei parametri
            handler: Funzione async/sync da chiamare (riceve dict, ritorna str)
        """
        self._tools[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": input_schema
                }
            },
            "handler": handler
        }

    def _get_tool_schemas(self) -> list[dict]:
        """Ritorna gli schemas dei tools per LiteLLM."""
        return [t["schema"] for t in self._tools.values()]

    async def _execute_tool(self, name: str, input_data: dict) -> str:
        """Esegue un tool e ritorna il risultato."""
        if name not in self._tools:
            return f"Error: Tool '{name}' not found"

        handler = self._tools[name]["handler"]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(input_data)
            else:
                result = handler(input_data)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    async def think(self, message: Message) -> dict[str, Any]:
        """Usa LiteLLM con tools per elaborare il messaggio."""
        if not self._tools:
            return await super().think(message)

        try:
            import litellm

            # Costruisci contesto
            conversation_id = message.metadata.get("conversation_id", "default")
            history = await self.storage.get_messages(conversation_id)

            # Costruisci messaggi
            messages = [{"role": "system", "content": self.system_prompt}]

            for msg in history[-10:]:
                role = "user" if msg.sender != self.id else "assistant"
                messages.append({"role": role, "content": msg.content})

            messages.append({"role": "user", "content": message.content})

            # Tool use loop
            tool_calls_log = []
            rounds = 0

            while rounds < self.max_tool_rounds:
                rounds += 1

                response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    max_tokens=1024,
                    tools=self._get_tool_schemas()
                )

                choice = response.choices[0]
                assistant_message = choice.message

                # Controlla se ci sono tool calls
                if not assistant_message.tool_calls:
                    # Risposta finale
                    return {
                        "response": assistant_message.content or "",
                        "actions": [],
                        "state_updates": {
                            "last_model": self.model,
                            "tool_calls": tool_calls_log
                        },
                        "metadata": {
                            "model": self.model,
                            "tool_rounds": rounds,
                            "tool_calls": tool_calls_log
                        }
                    }

                # Aggiungi risposta assistant ai messaggi
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Esegui ogni tool
                import json
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_input = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    result = await self._execute_tool(tool_name, tool_input)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result
                    })

                    # Aggiungi risultato
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            # Fallback se loop esaurito
            return {
                "response": "Reached maximum tool rounds without final response.",
                "actions": [],
                "state_updates": {"tool_calls": tool_calls_log},
                "metadata": {"tool_rounds": rounds, "tool_calls": tool_calls_log}
            }

        except ImportError:
            return {
                "response": "Errore: litellm non installato. Esegui: pip install litellm",
                "actions": [],
                "state_updates": {"last_error": "litellm not installed"}
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
