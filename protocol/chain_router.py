"""
Chain Pipeline Router - API endpoints for the document processing pipeline.

Provides:
- POST /api/chain/run - Start a pipeline
- GET /api/chain/status/{id} - Get pipeline status
- GET /api/chain/agents - List chain agents
- GET /api/chain/events - SSE endpoint for pipeline events
"""

import asyncio
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .mcp_server import get_storage
from .sse import SSEEvent
from agents.chain import (
    ChainPipeline,
    WriterAgent,
    EditorAgent,
    PublisherAgent,
    PipelineInput,
    PipelineResult,
)


router = APIRouter(prefix="/api/chain", tags=["Chain Pipeline"])

# Store for pipeline results and event queues
_pipeline_results: dict[str, PipelineResult] = {}
_pipeline_queues: dict[str, asyncio.Queue] = {}


class ChainRunRequest(BaseModel):
    """Request to run the chain pipeline."""
    prompt: str
    pipeline_id: Optional[str] = None


class ChainRunResponse(BaseModel):
    """Response after starting a pipeline."""
    pipeline_id: str
    status: str
    message: str


class ChainAgentInfo(BaseModel):
    """Information about a chain agent."""
    step_name: str
    agent_id: str
    description: str


def _create_pipeline_agents():
    """Create the chain pipeline agents."""
    storage = get_storage()
    return [
        WriterAgent(storage),
        EditorAgent(storage),
        PublisherAgent(storage)
    ]


def _create_event_handler(pipeline_id: str):
    """Create an event handler that broadcasts to SSE clients."""
    def handler(event: dict):
        if pipeline_id in _pipeline_queues:
            try:
                _pipeline_queues[pipeline_id].put_nowait(event)
            except asyncio.QueueFull:
                pass
    return handler


async def _run_pipeline_background(
    pipeline_id: str,
    prompt: str
):
    """Run the pipeline in the background."""
    storage = get_storage()
    agents = _create_pipeline_agents()

    event_handler = _create_event_handler(pipeline_id)

    pipeline = ChainPipeline(
        storage=storage,
        agents=agents,
        event_handler=event_handler
    )

    input_data = PipelineInput(
        prompt=prompt,
        pipeline_id=pipeline_id
    )

    result = await pipeline.run(input_data)
    _pipeline_results[pipeline_id] = result

    # Signal completion to SSE clients
    if pipeline_id in _pipeline_queues:
        await _pipeline_queues[pipeline_id].put({"event": "done", "data": {}})


@router.post("/run", response_model=ChainRunResponse)
async def run_pipeline(
    request: ChainRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Start the chain pipeline with a prompt.

    The pipeline runs Writer -> Editor -> Publisher sequentially.
    Use /api/chain/events/{pipeline_id} to receive real-time updates.

    Args:
        prompt: The topic/prompt to write about

    Returns:
        pipeline_id to track the execution
    """
    import uuid
    pipeline_id = request.pipeline_id or str(uuid.uuid4())[:8]

    # Create event queue for this pipeline
    _pipeline_queues[pipeline_id] = asyncio.Queue(maxsize=100)

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline_background,
        pipeline_id,
        request.prompt
    )

    return ChainRunResponse(
        pipeline_id=pipeline_id,
        status="started",
        message=f"Pipeline started. Connect to /api/chain/events/{pipeline_id} for updates."
    )


@router.get("/status/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """
    Get the status of a pipeline execution.

    Returns the full result if completed, or current status if running.
    """
    if pipeline_id in _pipeline_results:
        result = _pipeline_results[pipeline_id]
        return result.model_dump(mode='json')

    if pipeline_id in _pipeline_queues:
        return {
            "pipeline_id": pipeline_id,
            "status": "running",
            "message": "Pipeline is still executing"
        }

    return {
        "pipeline_id": pipeline_id,
        "status": "not_found",
        "message": "Pipeline not found"
    }


@router.get("/agents")
async def list_chain_agents():
    """
    List all agents in the chain pipeline.

    Returns information about Writer, Editor, and Publisher agents.
    """
    agents = _create_pipeline_agents()

    return [
        ChainAgentInfo(
            step_name=agent.step_name,
            agent_id=agent.id,
            description=agent.config.description
        ).model_dump()
        for agent in agents
    ]


async def _event_generator(pipeline_id: str):
    """Generate SSE events for a pipeline."""
    if pipeline_id not in _pipeline_queues:
        yield SSEEvent(
            event="error",
            data={"message": "Pipeline not found"}
        ).format()
        return

    queue = _pipeline_queues[pipeline_id]

    # Send connection event
    yield SSEEvent(
        event="connected",
        data={
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat()
        }
    ).format()

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)

                # Check for completion signal
                if event.get("event") == "done":
                    # Send final result
                    if pipeline_id in _pipeline_results:
                        result = _pipeline_results[pipeline_id]
                        yield SSEEvent(
                            event="result",
                            data=result.model_dump(mode='json')
                        ).format()
                    break

                # Forward pipeline events
                yield SSEEvent(
                    event=event.get("event", "update"),
                    data=event.get("data", {})
                ).format()

            except asyncio.TimeoutError:
                # Send keepalive
                yield SSEEvent(
                    event="ping",
                    data={"timestamp": datetime.now().isoformat()}
                ).format()

    finally:
        # Cleanup
        if pipeline_id in _pipeline_queues:
            del _pipeline_queues[pipeline_id]


@router.get("/events/{pipeline_id}")
async def pipeline_events(pipeline_id: str):
    """
    SSE endpoint for receiving real-time pipeline events.

    Events:
    - connected: Connection established
    - pipeline_started: Pipeline execution began
    - step_started: An agent started processing
    - step_completed: An agent finished processing
    - message_passed: Content passed between agents
    - pipeline_completed: Pipeline finished
    - result: Final result (sent last)
    - ping: Keepalive (every 60s)

    Example:
        curl -N http://localhost:8000/api/chain/events/{pipeline_id}
    """
    return StreamingResponse(
        _event_generator(pipeline_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
