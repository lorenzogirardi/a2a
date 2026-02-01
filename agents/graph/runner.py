"""
GraphRunner - Executes the LangGraph with SSE event streaming.

Wraps graph execution and emits events for real-time visualization.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Optional

from langgraph.graph.state import CompiledStateGraph

from .state import GraphState, create_initial_state
from .graph import build_router_graph
from .nodes import set_analyzer, set_registry, set_executor, set_synthesizer


class GraphRunner:
    """
    Runs LangGraph execution with SSE event streaming.

    Manages:
    - Graph building with dependencies
    - Execution with event streaming
    - Task tracking
    """

    def __init__(
        self,
        registry: Any,
        storage: Any,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the runner.

        Args:
            registry: AgentRegistry for agent discovery
            storage: StorageBase for agent state
            model: LLM model for analyzer/synthesizer
        """
        self.registry = registry
        self.storage = storage
        self.model = model

        # Build the graph
        self.graph = build_router_graph(
            registry=registry,
            storage=storage,
            model=model
        )

        # Track running tasks
        self._tasks: dict[str, dict] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        return uuid.uuid4().hex[:8]

    async def run(
        self,
        task: str,
        task_id: Optional[str] = None,
        event_handler: Optional[Callable[[dict], None]] = None
    ) -> GraphState:
        """
        Run the graph on a task.

        Args:
            task: The task to process
            task_id: Optional task ID (generated if not provided)
            event_handler: Optional callback for events

        Returns:
            Final GraphState after execution
        """
        if task_id is None:
            task_id = self._generate_task_id()

        # Create initial state
        initial_state = create_initial_state(task_id=task_id, task=task)

        # Track task
        self._tasks[task_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "task": task
        }

        # Create event queue for SSE
        event_queue: asyncio.Queue = asyncio.Queue()
        self._event_queues[task_id] = event_queue

        # Create stream writer that pushes to queue
        def stream_writer(event: dict) -> None:
            event["task_id"] = task_id
            event["timestamp"] = datetime.now().isoformat()
            asyncio.create_task(event_queue.put(event))
            if event_handler:
                event_handler(event)

        # Emit start event
        stream_writer({
            "type": "execution_started",
            "task": task
        })

        start_time = time.time()

        try:
            # Run graph with config
            config = {
                "configurable": {
                    "stream_writer": stream_writer
                }
            }

            result = await self.graph.ainvoke(initial_state, config=config)

            # Update status
            result["status"] = "completed"
            total_duration_ms = int((time.time() - start_time) * 1000)

            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self._tasks[task_id]["duration_ms"] = total_duration_ms

            # Emit completion event
            stream_writer({
                "type": "execution_completed",
                "status": "completed",
                "duration_ms": total_duration_ms,
                "final_output": result.get("final_output", "")
            })

            return result

        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = str(e)

            # Emit error event
            stream_writer({
                "type": "execution_failed",
                "error": str(e)
            })

            # Return failed state
            initial_state["status"] = "failed"
            initial_state["final_output"] = f"Error: {str(e)}"
            return initial_state

    async def stream(
        self,
        task: str,
        task_id: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        Stream events during graph execution.

        Yields events as they occur during execution.

        Args:
            task: The task to process
            task_id: Optional task ID

        Yields:
            Event dicts for SSE streaming
        """
        if task_id is None:
            task_id = self._generate_task_id()

        # Create initial state
        initial_state = create_initial_state(task_id=task_id, task=task)

        # Track task
        self._tasks[task_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "task": task
        }

        # Create event queue
        event_queue: asyncio.Queue = asyncio.Queue()
        self._event_queues[task_id] = event_queue

        # Stream writer pushes to queue
        async def stream_writer(event: dict) -> None:
            event["task_id"] = task_id
            event["timestamp"] = datetime.now().isoformat()
            await event_queue.put(event)

        # Start event
        await stream_writer({
            "type": "execution_started",
            "task": task
        })

        start_time = time.time()

        # Run graph in background
        async def run_graph():
            try:
                config = {
                    "configurable": {
                        "stream_writer": lambda e: asyncio.create_task(stream_writer(e))
                    }
                }
                result = await self.graph.ainvoke(initial_state, config=config)

                duration_ms = int((time.time() - start_time) * 1000)

                await stream_writer({
                    "type": "execution_completed",
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "final_output": result.get("final_output", ""),
                    "result": result
                })

            except Exception as e:
                await stream_writer({
                    "type": "execution_failed",
                    "error": str(e)
                })

            finally:
                # Signal end of stream
                await event_queue.put(None)

        # Start graph execution
        graph_task = asyncio.create_task(run_graph())

        # Yield events as they arrive
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            # Cleanup
            if task_id in self._event_queues:
                del self._event_queues[task_id]

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        Get the status of a task.

        Args:
            task_id: The task ID

        Returns:
            Task status dict or None if not found
        """
        return self._tasks.get(task_id)

    async def get_events(self, task_id: str) -> AsyncIterator[dict]:
        """
        Get SSE events for a running task.

        Args:
            task_id: The task ID

        Yields:
            Events from the task's queue
        """
        queue = self._event_queues.get(task_id)
        if not queue:
            return

        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    def get_graph_mermaid(self) -> str:
        """
        Get Mermaid diagram of the graph structure.

        Returns:
            Mermaid diagram string
        """
        return self.graph.get_graph().draw_mermaid()
