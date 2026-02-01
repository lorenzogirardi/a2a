"""
Simple Agent - Agente con logica predefinita (no LLM).

CONCETTO: Questo agente dimostra il pattern base senza dipendere da un LLM.
Utile per:
- Capire il flusso di esecuzione
- Testing
- Agenti con comportamento deterministico
- Prototipazione rapida
"""

from typing import Any
import re

from storage.base import StorageBase, Message
from .base import AgentBase, AgentConfig


class EchoAgent(AgentBase):
    """
    Agente semplice che fa echo dei messaggi.

    Utile per testing e per capire il flusso.
    """

    def __init__(self, agent_id: str, storage: StorageBase):
        config = AgentConfig(
            id=agent_id,
            name=f"Echo Agent ({agent_id})",
            description="Ripete i messaggi ricevuti",
            capabilities=["echo"]
        )
        super().__init__(config, storage)

    async def think(self, message: Message) -> dict[str, Any]:
        """Semplicemente prepara l'echo."""
        return {
            "response": f"Echo da {self.id}: {message.content}",
            "actions": [],
            "state_updates": {"last_message": message.content}
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        """Nessuna azione da eseguire."""
        return []


class CounterAgent(AgentBase):
    """
    Agente che conta i messaggi ricevuti.

    Dimostra come usare lo stato persistente.
    """

    def __init__(self, agent_id: str, storage: StorageBase):
        config = AgentConfig(
            id=agent_id,
            name=f"Counter Agent ({agent_id})",
            description="Conta i messaggi ricevuti",
            capabilities=["count"]
        )
        super().__init__(config, storage)

    async def think(self, message: Message) -> dict[str, Any]:
        """Incrementa il contatore e risponde."""
        current_count = self._internal_state.get("message_count", 0) + 1

        return {
            "response": f"Messaggio #{current_count} da {message.sender}: '{message.content}'",
            "actions": [],
            "state_updates": {"message_count": current_count}
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        return []


class RouterAgent(AgentBase):
    """
    Agente che smista messaggi ad altri agenti in base a regole.

    Dimostra la comunicazione agent-to-agent.
    """

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        routes: dict[str, 'AgentBase'] = None
    ):
        config = AgentConfig(
            id=agent_id,
            name=f"Router Agent ({agent_id})",
            description="Smista messaggi ad altri agenti",
            capabilities=["route", "delegate"]
        )
        super().__init__(config, storage)
        self.routes: dict[str, AgentBase] = routes or {}

    def add_route(self, keyword: str, agent: AgentBase) -> None:
        """Aggiunge una regola di routing."""
        self.routes[keyword.lower()] = agent
        print(f"[Router {self.id}] Aggiunta route: '{keyword}' -> {agent.id}")

    async def think(self, message: Message) -> dict[str, Any]:
        """Decide a chi inoltrare il messaggio."""
        content_lower = message.content.lower()

        # Cerca una route che matcha
        for keyword, agent in self.routes.items():
            if keyword in content_lower:
                return {
                    "response": "",  # La risposta verrà dall'agente target
                    "actions": [{
                        "type": "forward",
                        "target_agent": agent,
                        "message": message.content,
                        "original_sender": message.sender
                    }],
                    "state_updates": {"last_route": keyword}
                }

        # Nessuna route trovata
        available = list(self.routes.keys())
        return {
            "response": f"Non so a chi inoltrare questo messaggio. "
                       f"Keyword disponibili: {available}",
            "actions": [],
            "state_updates": {}
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        """Esegue il forwarding ai target agents."""
        results = []

        for action in actions:
            if action["type"] == "forward":
                target = action["target_agent"]
                response = await self.send_to_agent(
                    target,
                    action["message"]
                )
                results.append({
                    "action": "forward",
                    "target": target.id,
                    "response": response.content
                })

        return results


class CalculatorAgent(AgentBase):
    """
    Agente che esegue calcoli matematici semplici.

    Dimostra logica più complessa con pattern matching.
    """

    def __init__(self, agent_id: str, storage: StorageBase):
        config = AgentConfig(
            id=agent_id,
            name=f"Calculator Agent ({agent_id})",
            description="Esegue calcoli matematici",
            capabilities=["calculate", "math"]
        )
        super().__init__(config, storage)

    async def think(self, message: Message) -> dict[str, Any]:
        """Cerca operazioni matematiche nel messaggio."""
        content = message.content

        # Pattern per operazioni: "5 + 3", "10 * 2", etc.
        pattern = r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, content)

        if not match:
            return {
                "response": "Non ho trovato un'operazione matematica. "
                           "Prova con formato: '5 + 3' o '10 * 2'",
                "actions": [],
                "state_updates": {}
            }

        num1, op, num2 = match.groups()
        num1, num2 = float(num1), float(num2)

        return {
            "response": "",  # Calcolato in act()
            "actions": [{
                "type": "calculate",
                "num1": num1,
                "num2": num2,
                "operator": op
            }],
            "state_updates": {"last_calculation": f"{num1} {op} {num2}"},
            "metadata": {"needs_calculation": True}
        }

    async def act(self, actions: list[dict]) -> list[dict]:
        results = []

        for action in actions:
            if action["type"] == "calculate":
                num1 = action["num1"]
                num2 = action["num2"]
                op = action["operator"]

                ops = {
                    "+": lambda a, b: a + b,
                    "-": lambda a, b: a - b,
                    "*": lambda a, b: a * b,
                    "/": lambda a, b: a / b if b != 0 else "Errore: divisione per zero"
                }

                result = ops[op](num1, num2)

                # Aggiorna la risposta
                results.append({
                    "type": "calculation_result",
                    "expression": f"{num1} {op} {num2}",
                    "result": result
                })

        return results

    async def receive_message(self, ctx, content, sender_id, conversation_id=None):
        """Override per gestire il risultato del calcolo."""
        from auth.permissions import CallerContext

        message = Message(
            id="temp",
            sender=sender_id,
            receiver=self.id,
            content=content,
            timestamp=__import__('datetime').datetime.now(),
            metadata={}
        )

        thought = await self.think(message)

        if thought.get("actions"):
            results = await self.act(thought["actions"])
            if results:
                calc_result = results[0]
                thought["response"] = f"{calc_result['expression']} = {calc_result['result']}"

        # Chiama il metodo base per il resto
        from .base import AgentResponse
        return AgentResponse(
            content=thought["response"],
            agent_id=self.id,
            timestamp=__import__('datetime').datetime.now(),
            metadata=thought.get("metadata", {})
        )
