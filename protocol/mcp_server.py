"""
MCP Server - Espone gli agenti tramite Model Context Protocol.

CONCETTO: MCP è il protocollo di Anthropic per connettere LLM a tools e dati.
Qui lo usiamo per:
1. Esporre i nostri agenti come "tools" che Claude può chiamare
2. Permettere a client esterni di interagire con gli agenti
3. Standardizzare la comunicazione

MCP usa JSON-RPC 2.0 su stdio o SSE.
"""

from typing import Any
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from agents.base import AgentBase
from storage.base import StorageBase
from auth.permissions import CallerContext, Role, user_context


class AgentMCPServer:
    """
    Server MCP che espone gli agenti registrati.

    Ogni agente diventa un tool che può essere chiamato.
    """

    def __init__(self, storage: StorageBase):
        self.storage = storage
        self.agents: dict[str, AgentBase] = {}
        self.server = Server("agent-server")

        self._setup_handlers()

    def register_agent(self, agent: AgentBase) -> None:
        """Registra un agente nel server."""
        self.agents[agent.id] = agent
        print(f"[MCP] Registrato agente: {agent.id}")

    def _setup_handlers(self) -> None:
        """Configura gli handler MCP."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Ritorna la lista di tools (agenti) disponibili."""
            tools = []

            for agent_id, agent in self.agents.items():
                tools.append(Tool(
                    name=f"agent_{agent_id}",
                    description=f"{agent.name}: {agent.config.description}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Il messaggio da inviare all'agente"
                            },
                            "conversation_id": {
                                "type": "string",
                                "description": "ID della conversazione (opzionale)"
                            },
                            "caller_id": {
                                "type": "string",
                                "description": "ID di chi sta chiamando"
                            },
                            "caller_role": {
                                "type": "string",
                                "enum": ["admin", "user", "guest"],
                                "description": "Ruolo del caller (default: user)"
                            }
                        },
                        "required": ["message"]
                    }
                ))

            # Tool per listare le conversazioni
            tools.append(Tool(
                name="list_conversations",
                description="Mostra tutte le conversazioni attive",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ))

            # Tool per vedere lo stato di un agente
            tools.append(Tool(
                name="get_agent_state",
                description="Recupera lo stato interno di un agente",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID dell'agente"
                        }
                    },
                    "required": ["agent_id"]
                }
            ))

            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Gestisce le chiamate ai tools."""

            # Tool per conversazioni
            if name == "list_conversations":
                from storage.memory import MemoryStorage
                if isinstance(self.storage, MemoryStorage):
                    convs = self.storage.get_all_conversations()
                    result = {
                        conv_id: {
                            "participants": conv.participants,
                            "message_count": len(conv.messages)
                        }
                        for conv_id, conv in convs.items()
                    }
                    return [TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, default=str)
                    )]
                return [TextContent(type="text", text="Storage non supporta questa operazione")]

            # Tool per stato agente
            if name == "get_agent_state":
                agent_id = arguments.get("agent_id")
                if agent_id not in self.agents:
                    return [TextContent(type="text", text=f"Agente '{agent_id}' non trovato")]

                ctx = user_context("mcp_client")
                state = await self.agents[agent_id].get_state(ctx)
                return [TextContent(
                    type="text",
                    text=json.dumps(state, indent=2, default=str)
                )]

            # Chiamata a un agente
            if name.startswith("agent_"):
                agent_id = name[6:]  # Rimuove "agent_"

                if agent_id not in self.agents:
                    return [TextContent(type="text", text=f"Agente '{agent_id}' non trovato")]

                agent = self.agents[agent_id]

                # Costruisci il contesto dal caller
                caller_id = arguments.get("caller_id", "mcp_anonymous")
                caller_role = arguments.get("caller_role", "user")

                role_map = {
                    "admin": Role.ADMIN,
                    "user": Role.USER,
                    "guest": Role.GUEST
                }

                ctx = CallerContext(
                    caller_id=caller_id,
                    role=role_map.get(caller_role, Role.USER),
                    metadata={"source": "mcp"}
                )

                # Invia il messaggio
                try:
                    response = await agent.receive_message(
                        ctx=ctx,
                        content=arguments["message"],
                        sender_id=caller_id,
                        conversation_id=arguments.get("conversation_id")
                    )

                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "agent": agent_id,
                            "response": response.content,
                            "timestamp": response.timestamp.isoformat(),
                            "metadata": response.metadata
                        }, indent=2)
                    )]

                except Exception as e:
                    return [TextContent(type="text", text=f"Errore: {str(e)}")]

            return [TextContent(type="text", text=f"Tool '{name}' non riconosciuto")]

    async def run(self) -> None:
        """Avvia il server MCP su stdio."""
        print("[MCP] Server in avvio...")
        print(f"[MCP] Agenti disponibili: {list(self.agents.keys())}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
