"""
SSE Transport - Server-Sent Events for real-time MCP communication.

Allows remote clients to:
- Call MCP tools via HTTP POST
- Receive streaming responses via SSE
- Subscribe to agent events
"""

import json
import asyncio
from typing import AsyncGenerator, Optional
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .mcp_server import get_agents, get_storage, setup_default_agents


router = APIRouter(prefix="/sse", tags=["SSE"])


# Event queue for broadcasting
_event_queues: dict[str, asyncio.Queue] = {}


class ToolCallRequest(BaseModel):
    """Request to call an MCP tool."""
    tool: str
    params: dict = {}


class SSEEvent(BaseModel):
    """Server-Sent Event structure."""
    event: str
    data: dict
    id: Optional[str] = None

    def format(self) -> str:
        """Format as SSE string."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {json.dumps(self.data)}")
        lines.append("")  # Empty line to end event
        return "\n".join(lines) + "\n"


async def event_generator(client_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events for a client."""
    queue = asyncio.Queue()
    _event_queues[client_id] = queue

    try:
        # Send initial connection event
        yield SSEEvent(
            event="connected",
            data={"client_id": client_id, "timestamp": datetime.now().isoformat()}
        ).format()

        # Keep connection alive and send events
        while True:
            try:
                # Wait for event with timeout (for keep-alive)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event.format()
            except asyncio.TimeoutError:
                # Send keep-alive ping
                yield SSEEvent(
                    event="ping",
                    data={"timestamp": datetime.now().isoformat()}
                ).format()
    finally:
        # Cleanup on disconnect
        _event_queues.pop(client_id, None)


def broadcast_event(event: SSEEvent) -> None:
    """Broadcast an event to all connected clients."""
    for queue in _event_queues.values():
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Skip if queue is full


@router.get("/events")
async def sse_events(request: Request):
    """
    SSE endpoint for receiving real-time events.

    Connect with: curl -N http://localhost:8000/sse/events

    Events:
    - connected: Initial connection confirmation
    - ping: Keep-alive (every 30s)
    - tool_result: Result from tool call
    - agent_message: Message from an agent
    """
    client_id = f"client-{id(request)}"

    return StreamingResponse(
        event_generator(client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/call")
async def call_tool(request: ToolCallRequest):
    """
    Call an MCP tool and broadcast result via SSE.

    Example:
        POST /sse/call
        {"tool": "research", "params": {"query": "python async"}}
    """
    tool_name = request.tool
    params = request.params

    # Available tools
    tools = {
        "list_agents": _call_list_agents,
        "send_message": _call_send_message,
        "research": _call_research,
        "get_agent_state": _call_get_agent_state,
    }

    if tool_name not in tools:
        return {
            "error": "tool_not_found",
            "available_tools": list(tools.keys())
        }

    # Call the tool
    try:
        result = await tools[tool_name](params)

        # Broadcast result to SSE clients
        broadcast_event(SSEEvent(
            event="tool_result",
            data={
                "tool": tool_name,
                "params": params,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        ))

        return {"success": True, "result": result}

    except Exception as e:
        return {"error": str(e)}


# Tool implementations

async def _call_list_agents(params: dict) -> dict:
    """List all agents."""
    agents = get_agents()
    return {
        agent_id: {
            "name": agent.name,
            "description": agent.config.description,
            "capabilities": agent.config.capabilities
        }
        for agent_id, agent in agents.items()
    }


async def _call_send_message(params: dict) -> dict:
    """Send message to an agent."""
    from auth.permissions import CallerContext, Role

    agent_id = params.get("agent_id")
    message = params.get("message")
    caller_id = params.get("caller_id", "sse_client")

    agents = get_agents()
    if agent_id not in agents:
        return {"error": f"Agent '{agent_id}' not found"}

    agent = agents[agent_id]
    ctx = CallerContext(caller_id=caller_id, role=Role.USER)

    response = await agent.receive_message(
        ctx=ctx,
        content=message,
        sender_id=caller_id
    )

    # Broadcast agent message event
    broadcast_event(SSEEvent(
        event="agent_message",
        data={
            "agent_id": agent_id,
            "response": response.content,
            "timestamp": response.timestamp.isoformat()
        }
    ))

    return {
        "agent_id": agent_id,
        "response": response.content,
        "timestamp": response.timestamp.isoformat()
    }


async def _call_research(params: dict) -> dict:
    """Perform research query."""
    from agents.research import OrchestratorAgent

    query = params.get("query", "")
    storage = get_storage()
    orchestrator = OrchestratorAgent(storage)

    result = await orchestrator.research(query)

    return result.model_dump()


async def _call_get_agent_state(params: dict) -> dict:
    """Get agent state."""
    from auth.permissions import user_context

    agent_id = params.get("agent_id")
    agents = get_agents()

    if agent_id not in agents:
        return {"error": f"Agent '{agent_id}' not found"}

    ctx = user_context("sse_client")
    state = await agents[agent_id].get_state(ctx)

    return state


@router.get("/status")
async def sse_status():
    """Get SSE connection status."""
    return {
        "connected_clients": len(_event_queues),
        "client_ids": list(_event_queues.keys())
    }
