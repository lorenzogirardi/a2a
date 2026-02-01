"""
Router API - FastAPI endpoints for Smart Task Router.

Provides REST and SSE endpoints for task routing with real-time updates.
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime

from agents.registry import AgentRegistry
from agents.router import SmartRouter, TaskInput, RouterResult
from storage.memory import MemoryStorage


# Router instance (will be initialized on first use)
router = APIRouter(prefix="/api/router", tags=["router"])

# Storage for results and events
_results: dict[str, RouterResult] = {}
_event_queues: dict[str, asyncio.Queue] = {}

# Shared registry and router (lazy init)
_smart_router: Optional[SmartRouter] = None
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get or create the shared registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _register_default_agents(_registry)
    return _registry


def _register_default_agents(registry: AgentRegistry) -> None:
    """Register default agents with capabilities."""
    from storage.memory import MemoryStorage
    from agents.simple_agent import EchoAgent, CalculatorAgent

    storage = MemoryStorage()

    # Register simple agents
    echo = EchoAgent("echo", storage)
    echo.config.capabilities = ["echo"]
    registry.register(echo)

    calc = CalculatorAgent("calculator", storage)
    calc.config.capabilities = ["calculation"]
    registry.register(calc)

    # Register chain agents
    try:
        from agents.chain import WriterAgent, EditorAgent, PublisherAgent
        chain_storage = MemoryStorage()

        writer = WriterAgent(chain_storage)
        writer.config.capabilities = ["creative_writing"]
        registry.register(writer)

        editor = EditorAgent(chain_storage)
        editor.config.capabilities = ["text_editing"]
        registry.register(editor)

        publisher = PublisherAgent(chain_storage)
        publisher.config.capabilities = ["formatting"]
        registry.register(publisher)
    except ImportError:
        pass

    # Register specialist agents
    try:
        from agents.router.specialist_agents import (
            ResearchAgent,
            EstimationAgent,
            AnalysisAgent,
            TranslationAgent,
            SummaryAgent
        )
        specialist_storage = MemoryStorage()

        researcher = ResearchAgent(specialist_storage)
        registry.register(researcher)

        estimator = EstimationAgent(specialist_storage)
        registry.register(estimator)

        analyst = AnalysisAgent(specialist_storage)
        registry.register(analyst)

        translator = TranslationAgent(specialist_storage)
        registry.register(translator)

        summarizer = SummaryAgent(specialist_storage)
        registry.register(summarizer)
    except ImportError as e:
        print(f"Failed to register specialist agents: {e}")


def get_router() -> SmartRouter:
    """Get or create the shared smart router."""
    global _smart_router
    if _smart_router is None:
        storage = MemoryStorage()
        registry = get_registry()
        _smart_router = SmartRouter(
            registry=registry,
            storage=storage,
            event_handler=_broadcast_event
        )
    return _smart_router


def _broadcast_event(event: dict) -> None:
    """Broadcast event to all connected clients for this task."""
    task_id = event.get("data", {}).get("task_id")
    if task_id and task_id in _event_queues:
        try:
            _event_queues[task_id].put_nowait(event)
        except asyncio.QueueFull:
            pass


class RouteRequest(BaseModel):
    """Request to route a task."""
    task: str


class RouteResponse(BaseModel):
    """Response from starting a route."""
    task_id: str
    status: str
    message: str


@router.post("/route", response_model=RouteResponse)
async def route_task(request: RouteRequest):
    """
    Start routing a task.

    The task will be analyzed, matched to agents, and executed.
    Connect to /api/router/events/{task_id} for real-time updates.
    """
    task_input = TaskInput(task=request.task)
    task_id = task_input.task_id

    # Create event queue for this task
    _event_queues[task_id] = asyncio.Queue(maxsize=100)

    # Start routing in background
    smart_router = get_router()

    async def run_routing():
        result = await smart_router.route(task_input)
        _results[task_id] = result
        # Signal completion
        await _event_queues[task_id].put({"event": "result", "data": result.model_dump(mode='json')})

    asyncio.create_task(run_routing())

    return RouteResponse(
        task_id=task_id,
        status="started",
        message=f"Routing started. Connect to /api/router/events/{task_id} for updates."
    )


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get the status/result of a routing task."""
    if task_id in _results:
        return _results[task_id].model_dump(mode='json')

    if task_id in _event_queues:
        return {"task_id": task_id, "status": "in_progress"}

    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/events/{task_id}")
async def get_events(task_id: str):
    """SSE endpoint for real-time routing events."""
    if task_id not in _event_queues:
        # Create queue if task might start soon
        _event_queues[task_id] = asyncio.Queue(maxsize=100)

    async def event_generator():
        queue = _event_queues[task_id]

        # Send connected event
        yield f"event: connected\ndata: {{\"task_id\": \"{task_id}\"}}\n\n"

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)

                    event_type = event.get("event", "message")
                    data = event.get("data", {})

                    # Convert data to JSON string
                    import json
                    if isinstance(data, dict):
                        data_str = json.dumps(data, default=str)
                    else:
                        data_str = json.dumps(data.model_dump(mode='json') if hasattr(data, 'model_dump') else str(data))

                    yield f"event: {event_type}\ndata: {data_str}\n\n"

                    # If result event, we're done
                    if event_type == "result":
                        break

                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"event: ping\ndata: {{\"time\": \"{datetime.now().isoformat()}\"}}\n\n"

        finally:
            # Cleanup
            if task_id in _event_queues:
                del _event_queues[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/registry")
async def get_registry_info():
    """Get information about registered agents."""
    registry = get_registry()
    agents = []
    for agent in registry.list_all():
        agents.append({
            "id": agent.id,
            "name": agent.name,
            "capabilities": agent.config.capabilities,
            "description": agent.config.description
        })
    return {"agents": agents, "count": len(agents)}


@router.get("/capabilities")
async def get_capabilities():
    """Get list of available capabilities."""
    from agents.router.analyzer import AVAILABLE_CAPABILITIES
    return {
        "capabilities": [
            {"name": cap, "description": desc}
            for cap, desc in AVAILABLE_CAPABILITIES
        ]
    }
