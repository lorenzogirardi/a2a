"""
TaskExecutor - Executes tasks on matched agents.

Handles running subtasks on appropriate agents from the registry.
"""

import time
from typing import Optional, Callable
from datetime import datetime

from agents.base import AgentBase
from agents.registry import AgentRegistry
from auth.permissions import agent_context
from storage.base import Message
from .models import ExecutionResult, CapabilityMatch


class TaskExecutor:
    """
    Executes subtasks on matched agents.

    Takes a list of capability matches and executes the corresponding
    subtasks on the matched agents.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        event_handler: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize the executor.

        Args:
            registry: Agent registry for finding agents
            event_handler: Optional callback for events
        """
        self.registry = registry
        self.event_handler = event_handler

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an event if handler is configured."""
        if self.event_handler:
            self.event_handler({
                "event": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def execute_on_agent(
        self,
        agent: AgentBase,
        capability: str,
        subtask: str,
        task_id: str
    ) -> ExecutionResult:
        """
        Execute a subtask on a specific agent.

        Args:
            agent: The agent to execute on
            capability: The capability being used
            subtask: The subtask description
            task_id: ID of the parent task

        Returns:
            ExecutionResult with the outcome
        """
        start_time = time.time()

        self._emit_event("execution_started", {
            "task_id": task_id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "capability": capability,
            "subtask": subtask
        })

        try:
            # Create context for agent communication
            ctx = agent_context(f"router-{task_id}")

            # Send message to agent
            response = await agent.receive_message(
                ctx=ctx,
                content=subtask,
                sender_id="router"
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Extract token info if available
            tokens = {"input": 0, "output": 0}
            if hasattr(response, 'metadata') and response.metadata:
                usage = response.metadata.get("usage", {})
                tokens = {
                    "input": usage.get("input_tokens", 0),
                    "output": usage.get("output_tokens", 0)
                }

            result = ExecutionResult(
                agent_id=agent.id,
                agent_name=agent.name,
                capability=capability,
                input_text=subtask,
                output_text=response.content,
                duration_ms=duration_ms,
                success=True,
                tokens=tokens
            )

            self._emit_event("execution_completed", {
                "task_id": task_id,
                "agent_id": agent.id,
                "capability": capability,
                "output": response.content,
                "duration_ms": duration_ms,
                "success": True
            })

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            result = ExecutionResult(
                agent_id=agent.id,
                agent_name=agent.name,
                capability=capability,
                input_text=subtask,
                output_text="",
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )

            self._emit_event("execution_completed", {
                "task_id": task_id,
                "agent_id": agent.id,
                "capability": capability,
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e)
            })

            return result

    async def execute_all(
        self,
        matches: list[CapabilityMatch],
        subtasks: dict[str, str],
        task_id: str
    ) -> list[ExecutionResult]:
        """
        Execute all subtasks on matched agents.

        Args:
            matches: List of capability matches with agent IDs
            subtasks: Dict mapping capability -> subtask description
            task_id: ID of the parent task

        Returns:
            List of ExecutionResults
        """
        results = []

        for match in matches:
            if not match.matched or not match.agent_ids:
                continue

            capability = match.capability
            subtask = subtasks.get(capability, "")

            if not subtask:
                continue

            # Use first matched agent for each capability
            agent_id = match.agent_ids[0]
            agent = self.registry.get(agent_id)

            if agent:
                result = await self.execute_on_agent(
                    agent=agent,
                    capability=capability,
                    subtask=subtask,
                    task_id=task_id
                )
                results.append(result)

        return results
