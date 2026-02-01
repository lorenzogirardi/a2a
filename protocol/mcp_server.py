"""
FastMCP Server - Espone gli agenti tramite Model Context Protocol.

Usa FastMCP per una API più semplice basata su decoratori.
"""

import json
from typing import Optional
from fastmcp import FastMCP

from agents.base import AgentBase
from storage.base import StorageBase
from storage.memory import MemoryStorage
from auth.permissions import CallerContext, Role, user_context, admin_context

# Registry globale degli agenti (condiviso con FastAPI)
_storage: Optional[StorageBase] = None
_agents: dict[str, AgentBase] = {}


def get_storage() -> StorageBase:
    """Ritorna lo storage condiviso."""
    global _storage
    if _storage is None:
        _storage = MemoryStorage()
    return _storage


def get_agents() -> dict[str, AgentBase]:
    """Ritorna il registry degli agenti."""
    return _agents


def register_agent(agent: AgentBase) -> None:
    """Registra un agente nel registry globale."""
    _agents[agent.id] = agent
    print(f"[MCP] Registrato agente: {agent.id}")


def set_storage(storage: StorageBase) -> None:
    """Imposta lo storage globale."""
    global _storage
    _storage = storage


# Crea il server FastMCP
mcp = FastMCP("a2a-agents")


@mcp.tool()
def list_agents() -> str:
    """Lista tutti gli agenti disponibili con le loro capacità."""
    agents = get_agents()
    result = {
        agent_id: {
            "name": agent.name,
            "description": agent.config.description,
            "capabilities": agent.config.capabilities
        }
        for agent_id, agent in agents.items()
    }
    return json.dumps(result, indent=2)


@mcp.tool()
async def send_message(
    agent_id: str,
    message: str,
    caller_id: str = "mcp_user",
    caller_role: str = "user",
    conversation_id: Optional[str] = None
) -> str:
    """
    Invia un messaggio a un agente specifico.

    Args:
        agent_id: ID dell'agente destinatario
        message: Il messaggio da inviare
        caller_id: ID di chi sta chiamando
        caller_role: Ruolo del caller (admin, user, guest)
        conversation_id: ID conversazione (opzionale)
    """
    agents = get_agents()

    if agent_id not in agents:
        return json.dumps({
            "error": "agent_not_found",
            "message": f"Agente '{agent_id}' non trovato",
            "available_agents": list(agents.keys())
        })

    agent = agents[agent_id]

    # Costruisci il contesto
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

    try:
        response = await agent.receive_message(
            ctx=ctx,
            content=message,
            sender_id=caller_id,
            conversation_id=conversation_id
        )

        return json.dumps({
            "agent": agent_id,
            "response": response.content,
            "timestamp": response.timestamp.isoformat(),
            "metadata": response.metadata
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": "agent_error",
            "message": str(e),
            "agent": agent_id
        })


@mcp.tool()
async def get_agent_state(agent_id: str) -> str:
    """
    Recupera lo stato interno di un agente.

    Args:
        agent_id: ID dell'agente
    """
    agents = get_agents()

    if agent_id not in agents:
        return json.dumps({
            "error": "agent_not_found",
            "message": f"Agente '{agent_id}' non trovato"
        })

    ctx = user_context("mcp_client")
    state = await agents[agent_id].get_state(ctx)

    return json.dumps(state, indent=2, default=str)


@mcp.tool()
def list_conversations() -> str:
    """Mostra tutte le conversazioni attive."""
    storage = get_storage()

    if isinstance(storage, MemoryStorage):
        convs = storage.get_all_conversations()
        result = {
            conv_id: {
                "participants": conv.participants,
                "message_count": len(conv.messages),
                "created_at": conv.created_at.isoformat()
            }
            for conv_id, conv in convs.items()
        }
        return json.dumps(result, indent=2)

    return json.dumps({"error": "Storage non supporta questa operazione"})


@mcp.tool()
async def get_conversation_messages(conversation_id: str) -> str:
    """
    Recupera i messaggi di una conversazione.

    Args:
        conversation_id: ID della conversazione
    """
    storage = get_storage()
    messages = await storage.get_messages(conversation_id)

    result = [
        {
            "id": msg.id,
            "sender": msg.sender,
            "receiver": msg.receiver,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

    return json.dumps(result, indent=2)


@mcp.resource("agents://list")
def resource_agents_list() -> str:
    """Lista degli agenti come risorsa."""
    return list_agents()


@mcp.resource("agents://{agent_id}/state")
async def resource_agent_state(agent_id: str) -> str:
    """Stato di un agente come risorsa."""
    return await get_agent_state(agent_id)


# ============================================
# Research Tools
# ============================================

_research_orchestrator = None


def get_research_orchestrator():
    """Get or create the research orchestrator."""
    global _research_orchestrator
    if _research_orchestrator is None:
        from agents.research import OrchestratorAgent
        _research_orchestrator = OrchestratorAgent(get_storage())
    return _research_orchestrator


@mcp.tool()
async def research(query: str) -> str:
    """
    Perform multi-source research on a query.

    Searches web, documentation, and code sources in parallel,
    then aggregates and ranks the results.

    Args:
        query: The research query (e.g., "python async patterns")

    Returns:
        JSON with aggregated results from all sources
    """
    orchestrator = get_research_orchestrator()
    result = await orchestrator.research(query)

    return json.dumps(result.model_dump(), indent=2, default=str)


def setup_default_agents() -> None:
    """Setup degli agenti di default per testing."""
    from agents import EchoAgent, CounterAgent, CalculatorAgent, RouterAgent

    storage = get_storage()

    echo = EchoAgent("echo", storage)
    counter = CounterAgent("counter", storage)
    calculator = CalculatorAgent("calculator", storage)

    router = RouterAgent("router", storage)
    router.add_route("calcola", calculator)
    router.add_route("ripeti", echo)
    router.add_route("conta", counter)

    register_agent(echo)
    register_agent(counter)
    register_agent(calculator)
    register_agent(router)


if __name__ == "__main__":
    setup_default_agents()
    mcp.run()
