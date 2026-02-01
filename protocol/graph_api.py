"""
Graph API - FastAPI endpoints for LangGraph execution.

Provides:
- POST /api/graph/run: Start graph execution
- GET /api/graph/events/{task_id}: SSE stream of events
- GET /api/graph/status/{task_id}: Task status
- GET /api/graph/structure: Graph structure (Mermaid)
"""

import asyncio
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.registry import AgentRegistry
from storage.memory import MemoryStorage
from agents.graph.runner import GraphRunner


# ============================================
# Pydantic Models
# ============================================


class GraphTaskRequest(BaseModel):
    """Request to run a task through the graph."""
    task: str = Field(..., description="The task to process")
    task_id: Optional[str] = Field(None, description="Optional task ID")


class GraphTaskResponse(BaseModel):
    """Response from graph execution."""
    task_id: str
    status: str
    final_output: str
    duration_ms: int
    executions_count: int
    synthesis_used: bool


class GraphStatusResponse(BaseModel):
    """Status of a graph task."""
    task_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class GraphStructureResponse(BaseModel):
    """Graph structure for visualization."""
    mermaid: str
    nodes: list[dict]
    edges: list[dict]


# ============================================
# Router
# ============================================


router = APIRouter(prefix="/api/graph", tags=["graph"])


# Module-level runner (lazy initialization)
_graph_runner: Optional[GraphRunner] = None


def get_graph_runner() -> GraphRunner:
    """Get or create the graph runner."""
    global _graph_runner
    if _graph_runner is None:
        # Create shared instances
        storage = MemoryStorage()
        registry = AgentRegistry()

        # Register specialist agents
        from agents.router.specialist_agents import (
            ResearchAgent,
            EstimationAgent,
            AnalysisAgent,
            TranslationAgent,
            SummaryAgent,
        )
        from agents.simple_agent import CalculatorAgent, EchoAgent

        # Create and register agents
        calc = CalculatorAgent("calculator", storage)
        echo = EchoAgent("echo", storage)
        research = ResearchAgent(storage)
        estimation = EstimationAgent(storage)
        analysis = AnalysisAgent(storage)
        translation = TranslationAgent(storage)
        summary = SummaryAgent(storage)

        registry.register(calc)
        registry.register(echo)
        registry.register(research)
        registry.register(estimation)
        registry.register(analysis)
        registry.register(translation)
        registry.register(summary)

        _graph_runner = GraphRunner(
            registry=registry,
            storage=storage
        )

    return _graph_runner


# ============================================
# Endpoints
# ============================================


@router.post("/run", response_model=GraphTaskResponse)
async def run_graph(request: GraphTaskRequest):
    """
    Run a task through the LangGraph execution graph.

    The graph:
    1. Analyzes the task to detect capabilities
    2. Discovers agents for each capability
    3. Executes subtasks on matched agents
    4. Synthesizes results if multiple agents responded

    Returns the final output and execution metadata.
    """
    runner = get_graph_runner()

    result = await runner.run(
        task=request.task,
        task_id=request.task_id
    )

    return GraphTaskResponse(
        task_id=result["task_id"],
        status=result["status"],
        final_output=result.get("final_output", ""),
        duration_ms=runner.get_task_status(result["task_id"]).get("duration_ms", 0),
        executions_count=len(result.get("executions", [])),
        synthesis_used=result.get("synthesis") is not None
    )


@router.get("/events/{task_id}")
async def stream_events(task_id: str):
    """
    Stream SSE events for a task execution.

    Events include:
    - graph_update: vis.js graph updates
    - execution_started: Task began
    - execution_completed: Task finished
    - execution_failed: Task failed

    Use this endpoint with EventSource for real-time updates.
    """
    runner = get_graph_runner()

    async def event_generator():
        """Generate SSE events."""
        async for event in runner.get_events(task_id):
            event_type = event.get("type", "message")
            data = event

            yield f"event: {event_type}\n"
            yield f"data: {data}\n\n"

        # Send done event
        yield "event: done\n"
        yield "data: {\"status\": \"completed\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/stream")
async def run_and_stream(request: GraphTaskRequest):
    """
    Run a task and stream events as SSE.

    Combines run and events endpoints - starts execution
    and immediately streams all events.
    """
    runner = get_graph_runner()

    async def event_generator():
        """Generate SSE events during execution."""
        import json

        async for event in runner.stream(
            task=request.task,
            task_id=request.task_id
        ):
            event_type = event.get("type", "message")
            data_str = json.dumps(event)

            yield f"event: {event_type}\n"
            yield f"data: {data_str}\n\n"

        # Send done event
        yield "event: done\n"
        yield "data: {\"status\": \"completed\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/status/{task_id}", response_model=GraphStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a task.

    Returns current status, timing, and any errors.
    """
    runner = get_graph_runner()
    status = runner.get_task_status(task_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found"
        )

    return GraphStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
        duration_ms=status.get("duration_ms"),
        error=status.get("error")
    )


@router.get("/structure", response_model=GraphStructureResponse)
async def get_graph_structure():
    """
    Get the graph structure for visualization.

    Returns:
    - mermaid: Mermaid diagram string
    - nodes: List of nodes with IDs and names
    - edges: List of edges with source/target
    """
    runner = get_graph_runner()

    from agents.graph.graph import get_graph_structure as get_structure
    structure = get_structure(runner.graph)

    return GraphStructureResponse(
        mermaid=structure["mermaid"],
        nodes=structure["nodes"],
        edges=structure["edges"]
    )


@router.get("/registry")
async def get_registry_info():
    """
    Get information about registered agents.

    Returns list of agents with their capabilities.
    """
    runner = get_graph_runner()

    agents = []
    for agent in runner.registry.list_all():
        agents.append({
            "id": agent.id,
            "name": agent.name,
            "capabilities": agent.config.capabilities if hasattr(agent, 'config') else []
        })

    return {"agents": agents}
