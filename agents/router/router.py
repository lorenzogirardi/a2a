"""
SmartRouter - Intelligent task routing orchestrator.

Coordinates analysis, discovery, and execution of tasks
by finding appropriate agents based on capabilities.
"""

import time
from typing import Optional, Callable
from datetime import datetime

from agents.registry import AgentRegistry
from storage.base import StorageBase
from .analyzer import AnalyzerAgent
from .executor import TaskExecutor
from .models import (
    TaskInput,
    RouterResult,
    CapabilityMatch,
    AnalysisResult,
    SynthesisResult
)
from .synthesizer import SynthesizerAgent


class SmartRouter:
    """
    Routes tasks to appropriate agents based on capabilities.

    Workflow:
    1. Analyze task to detect required capabilities
    2. Discover agents in registry that match capabilities
    3. Execute subtasks on matched agents
    4. Aggregate results
    """

    def __init__(
        self,
        registry: AgentRegistry,
        storage: StorageBase,
        event_handler: Optional[Callable[[dict], None]] = None,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the router.

        Args:
            registry: Agent registry for discovery
            storage: Storage for agents
            event_handler: Optional callback for SSE events
            model: LLM model for analyzer
        """
        self.registry = registry
        self.storage = storage
        self.event_handler = event_handler

        # Create analyzer, executor, and synthesizer
        self.analyzer = AnalyzerAgent(storage=storage, model=model)
        self.executor = TaskExecutor(registry=registry, event_handler=event_handler)
        self.synthesizer = SynthesizerAgent(storage=storage, model=model)

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an SSE event if handler is configured."""
        if self.event_handler:
            self.event_handler({
                "event": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def route(self, task_input: TaskInput) -> RouterResult:
        """
        Route a task to appropriate agents.

        Args:
            task_input: The task to route

        Returns:
            RouterResult with complete routing outcome
        """
        start_time = time.time()
        task_id = task_input.task_id
        task = task_input.task

        # Initialize result
        result = RouterResult(
            task_id=task_id,
            original_task=task,
            analysis=AnalysisResult(task_id=task_id, original_task=task),
            status="analyzing"
        )

        self._emit_event("routing_started", {
            "task_id": task_id,
            "task": task
        })

        try:
            # Step 1: Analyze task
            self._emit_event("analysis_started", {"task_id": task_id})

            analysis = await self.analyzer.analyze(task, task_id)
            result.analysis = analysis

            self._emit_event("analysis_completed", {
                "task_id": task_id,
                "capabilities": analysis.detected_capabilities,
                "subtasks": analysis.subtasks,
                "duration_ms": analysis.duration_ms
            })

            if not analysis.detected_capabilities:
                result.status = "completed"
                result.final_output = "No capabilities detected for this task."
                result.total_duration_ms = int((time.time() - start_time) * 1000)
                self._emit_event("routing_completed", {
                    "task_id": task_id,
                    "status": "completed",
                    "message": "No capabilities detected"
                })
                return result

            # Step 2: Discover agents
            result.status = "discovering"
            matches = []

            for capability in analysis.detected_capabilities:
                self._emit_event("discovery_started", {
                    "task_id": task_id,
                    "capability": capability
                })

                agents = self.registry.find_by_capability(capability)
                agent_ids = [a.id for a in agents]

                match = CapabilityMatch(
                    capability=capability,
                    agent_ids=agent_ids,
                    matched=len(agent_ids) > 0
                )
                matches.append(match)

                self._emit_event("discovery_completed", {
                    "task_id": task_id,
                    "capability": capability,
                    "agents": [{"id": a.id, "name": a.name} for a in agents],
                    "matched": match.matched
                })

            result.matches = matches

            # Check if any capabilities matched
            if not any(m.matched for m in matches):
                result.status = "completed"
                result.final_output = "No agents found for required capabilities."
                result.total_duration_ms = int((time.time() - start_time) * 1000)
                self._emit_event("routing_completed", {
                    "task_id": task_id,
                    "status": "completed",
                    "message": "No matching agents"
                })
                return result

            # Step 3: Execute subtasks
            result.status = "executing"

            executions = await self.executor.execute_all(
                matches=matches,
                subtasks=analysis.subtasks,
                task_id=task_id
            )
            result.executions = executions

            # Step 4: Synthesize results (Phase 2)
            successful = [e for e in executions if e.success]
            if successful:
                # If multiple successful executions, synthesize them
                if len(successful) > 1:
                    result.status = "synthesizing"
                    self._emit_event("synthesis_started", {
                        "task_id": task_id,
                        "sources": [e.agent_id for e in successful]
                    })

                    synthesis_result = await self.synthesizer.synthesize(
                        original_task=task,
                        executions=successful,
                        task_id=task_id
                    )

                    result.synthesis = SynthesisResult(
                        synthesized_output=synthesis_result["synthesized_output"],
                        duration_ms=synthesis_result["duration_ms"],
                        sources=synthesis_result["sources"],
                        tokens=synthesis_result["tokens"]
                    )
                    result.final_output = synthesis_result["synthesized_output"]

                    self._emit_event("synthesis_completed", {
                        "task_id": task_id,
                        "duration_ms": synthesis_result["duration_ms"],
                        "sources": synthesis_result["sources"]
                    })
                else:
                    # Single execution, use directly
                    result.final_output = successful[0].output_text
            else:
                result.final_output = "All executions failed."

            result.status = "completed"
            result.total_duration_ms = int((time.time() - start_time) * 1000)

            self._emit_event("routing_completed", {
                "task_id": task_id,
                "status": "completed",
                "total_duration_ms": result.total_duration_ms,
                "executions_count": len(executions),
                "successful_count": len(successful)
            })

            return result

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.total_duration_ms = int((time.time() - start_time) * 1000)

            self._emit_event("routing_completed", {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            })

            return result

    def get_registry_info(self) -> dict:
        """Get information about registered agents."""
        return self.registry.get_all_info()
