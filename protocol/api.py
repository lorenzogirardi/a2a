"""
FastAPI REST API - Espone gli agenti tramite HTTP REST.

Complementa FastMCP per client non-MCP (curl, browser, altri servizi).
"""

import os
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth.permissions import CallerContext, Role, PermissionDenied
from .mcp_server import get_agents, get_storage, setup_default_agents
from .sse import router as sse_router
from .chain_router import router as chain_router
from .router_api import router as router_api

# ============================================
# Pydantic Models
# ============================================


class MessageRequest(BaseModel):
    """Richiesta per inviare un messaggio a un agente."""
    message: str
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Risposta da un agente."""
    agent_id: str
    response: str
    timestamp: str
    metadata: dict = {}


class AgentInfo(BaseModel):
    """Informazioni su un agente."""
    id: str
    name: str
    description: str
    capabilities: list[str]


class ConversationInfo(BaseModel):
    """Informazioni su una conversazione."""
    id: str
    participants: list[str]
    message_count: int
    created_at: str


class HealthResponse(BaseModel):
    """Risposta health check."""
    status: str
    agents_count: int
    storage_type: str


class ErrorResponse(BaseModel):
    """Risposta di errore."""
    error: str
    message: str
    details: Optional[dict] = None


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="A2A Agent API",
    description="REST API per interagire con gli agenti A2A",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include SSE router
app.include_router(sse_router)

# Include Chain router
app.include_router(chain_router)

# Include Router API
app.include_router(router_api)

# Mount static files for chain demo
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "chain")
if os.path.exists(_static_dir):
    app.mount("/static/chain", StaticFiles(directory=_static_dir, html=True), name="chain-static")

# Mount static files for router demo
_router_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "router")
if os.path.exists(_router_static_dir):
    app.mount("/static/router", StaticFiles(directory=_router_static_dir, html=True), name="router-static")


# ============================================
# Dependencies
# ============================================

async def get_caller_context(
    x_caller_id: str = Header(default="api_anonymous"),
    x_caller_role: str = Header(default="user")
) -> CallerContext:
    """Estrae il CallerContext dagli header HTTP."""
    role_map = {
        "admin": Role.ADMIN,
        "user": Role.USER,
        "guest": Role.GUEST
    }

    return CallerContext(
        caller_id=x_caller_id,
        role=role_map.get(x_caller_role, Role.USER),
        metadata={"source": "api"}
    )


# ============================================
# Endpoints
# ============================================

@app.on_event("startup")
async def startup_event():
    """Setup iniziale all'avvio del server."""
    setup_default_agents()
    print("[API] Server avviato con agenti di default")


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    agents = get_agents()
    storage = get_storage()

    return HealthResponse(
        status="ok",
        agents_count=len(agents),
        storage_type=type(storage).__name__
    )


@app.get("/api/agents", response_model=dict[str, AgentInfo], tags=["Agents"])
async def list_agents():
    """Lista tutti gli agenti disponibili."""
    agents = get_agents()

    return {
        agent_id: AgentInfo(
            id=agent_id,
            name=agent.name,
            description=agent.config.description,
            capabilities=agent.config.capabilities
        )
        for agent_id, agent in agents.items()
    }


@app.get("/api/agents/{agent_id}", response_model=AgentInfo, tags=["Agents"])
async def get_agent(agent_id: str):
    """Dettagli di un agente specifico."""
    agents = get_agents()

    if agent_id not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agente '{agent_id}' non trovato"
        )

    agent = agents[agent_id]
    return AgentInfo(
        id=agent_id,
        name=agent.name,
        description=agent.config.description,
        capabilities=agent.config.capabilities
    )


@app.post(
    "/api/agents/{agent_id}/message",
    response_model=MessageResponse,
    tags=["Agents"]
)
async def send_message(
    agent_id: str,
    request: MessageRequest,
    ctx: CallerContext = Depends(get_caller_context)
):
    """
    Invia un messaggio a un agente.

    Headers opzionali:
    - X-Caller-ID: ID del chiamante (default: api_anonymous)
    - X-Caller-Role: Ruolo (admin, user, guest) (default: user)
    """
    agents = get_agents()

    if agent_id not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agente '{agent_id}' non trovato"
        )

    agent = agents[agent_id]

    try:
        response = await agent.receive_message(
            ctx=ctx,
            content=request.message,
            sender_id=ctx.caller_id,
            conversation_id=request.conversation_id
        )

        return MessageResponse(
            agent_id=agent_id,
            response=response.content,
            timestamp=response.timestamp.isoformat(),
            metadata=response.metadata
        )

    except PermissionDenied as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "permission_denied",
                "message": str(e),
                "required_permission": e.permission.value
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "agent_error",
                "message": str(e)
            }
        )


@app.get("/api/agents/{agent_id}/state", tags=["Agents"])
async def get_agent_state(
    agent_id: str,
    ctx: CallerContext = Depends(get_caller_context)
):
    """Recupera lo stato interno di un agente."""
    agents = get_agents()

    if agent_id not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agente '{agent_id}' non trovato"
        )

    try:
        state = await agents[agent_id].get_state(ctx)
        return state

    except PermissionDenied as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "permission_denied",
                "message": str(e)
            }
        )


@app.get("/api/conversations", response_model=list[ConversationInfo], tags=["Conversations"])
async def list_conversations():
    """Lista tutte le conversazioni attive."""
    from storage.memory import MemoryStorage

    storage = get_storage()

    if not isinstance(storage, MemoryStorage):
        raise HTTPException(
            status_code=501,
            detail="Storage non supporta questa operazione"
        )

    convs = storage.get_all_conversations()

    return [
        ConversationInfo(
            id=conv_id,
            participants=conv.participants,
            message_count=len(conv.messages),
            created_at=conv.created_at.isoformat()
        )
        for conv_id, conv in convs.items()
    ]


@app.get("/api/conversations/{conversation_id}/messages", tags=["Conversations"])
async def get_conversation_messages(conversation_id: str):
    """Recupera i messaggi di una conversazione."""
    storage = get_storage()
    messages = await storage.get_messages(conversation_id)

    return [
        {
            "id": msg.id,
            "sender": msg.sender,
            "receiver": msg.receiver,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]


# ============================================
# Research Endpoints
# ============================================

_research_orchestrator = None


def get_research_orchestrator():
    """Get or create the research orchestrator."""
    global _research_orchestrator
    if _research_orchestrator is None:
        from agents.research import OrchestratorAgent
        _research_orchestrator = OrchestratorAgent(get_storage())
    return _research_orchestrator


@app.get("/api/research", tags=["Research"])
async def research(q: str):
    """
    Perform multi-source research on a query.

    Searches web, documentation, and code sources in parallel,
    then aggregates and ranks the results.

    Args:
        q: The research query (e.g., "python async patterns")

    Returns:
        Aggregated results from all sources
    """
    orchestrator = get_research_orchestrator()
    result = await orchestrator.research(q)

    return result.model_dump()


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(PermissionDenied)
async def permission_denied_handler(request, exc: PermissionDenied):
    """Handler globale per PermissionDenied."""
    return {
        "error": "permission_denied",
        "caller": exc.caller_id,
        "permission": exc.permission.value,
        "operation": exc.operation
    }
