"""
ChainPipeline - Orchestrates the document processing pipeline.

Manages the sequential execution of chain steps (Writer -> Editor -> Publisher)
and broadcasts SSE events for real-time visualization.
"""

import time
from typing import Callable, Optional
from datetime import datetime

from storage.base import StorageBase
from .base import ChainStepAgent
from .models import PipelineInput, PipelineResult, StepResult, TokenUsage


class ChainPipeline:
    """
    Orchestrates a chain of agents for document processing.

    Executes agents sequentially, passing output from one step
    as input to the next. Broadcasts SSE events for live visualization.
    """

    def __init__(
        self,
        storage: StorageBase,
        agents: list[ChainStepAgent],
        event_handler: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize the pipeline.

        Args:
            storage: Storage backend for agents
            agents: List of agents to execute in order
            event_handler: Optional callback for SSE events
        """
        self.storage = storage
        self.agents = agents
        self.event_handler = event_handler

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an SSE event if handler is configured."""
        if self.event_handler:
            self.event_handler({
                "event": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def run(self, input_data: PipelineInput) -> PipelineResult:
        """
        Execute the pipeline with the given input.

        Args:
            input_data: Pipeline input configuration

        Returns:
            PipelineResult with all step results
        """
        pipeline_start = time.time()
        step_results: list[StepResult] = []
        current_text = input_data.prompt
        error_message: Optional[str] = None

        # Emit pipeline started event
        self._emit_event("pipeline_started", {
            "pipeline_id": input_data.pipeline_id,
            "prompt": input_data.prompt,
            "steps": [agent.step_name for agent in self.agents]
        })

        try:
            for index, agent in enumerate(self.agents):
                step_start = time.time()

                # Emit step started event
                self._emit_event("step_started", {
                    "pipeline_id": input_data.pipeline_id,
                    "step_index": index,
                    "step_name": agent.step_name,
                    "model": agent.model,
                    "input_preview": current_text[:200] + "..." if len(current_text) > 200 else current_text,
                    "input_length": len(current_text)
                })

                try:
                    # Execute the step with metadata
                    transform_result = await agent.transform_with_metadata(current_text)
                    output_text = transform_result.text
                    step_duration = int((time.time() - step_start) * 1000)

                    # Create token usage
                    tokens = TokenUsage(
                        input_tokens=transform_result.input_tokens,
                        output_tokens=transform_result.output_tokens
                    )

                    # Record step result
                    step_result = StepResult(
                        step_name=agent.step_name,
                        step_index=index,
                        input_text=current_text,
                        output_text=output_text,
                        duration_ms=step_duration,
                        model=transform_result.model,
                        tokens=tokens
                    )
                    step_results.append(step_result)

                    # Emit step completed event with full metadata
                    self._emit_event("step_completed", {
                        "pipeline_id": input_data.pipeline_id,
                        "step_index": index,
                        "step_name": agent.step_name,
                        "model": transform_result.model,
                        "output": output_text,
                        "output_length": len(output_text),
                        "duration_ms": step_duration,
                        "input_tokens": transform_result.input_tokens,
                        "output_tokens": transform_result.output_tokens,
                        "total_tokens": transform_result.input_tokens + transform_result.output_tokens
                    })

                    # Emit message passed event (if not last step)
                    if index < len(self.agents) - 1:
                        self._emit_event("message_passed", {
                            "pipeline_id": input_data.pipeline_id,
                            "from_step": agent.step_name,
                            "to_step": self.agents[index + 1].step_name,
                            "content": output_text,
                            "content_length": len(output_text)
                        })

                    # Pass output to next step
                    current_text = output_text

                except Exception as e:
                    error_message = f"Step '{agent.step_name}' failed: {str(e)}"
                    break

            total_duration = int((time.time() - pipeline_start) * 1000)
            status = "failed" if error_message else "completed"

            # Emit pipeline completed event
            self._emit_event("pipeline_completed", {
                "pipeline_id": input_data.pipeline_id,
                "status": status,
                "final_output": current_text if not error_message else "",
                "total_duration_ms": total_duration,
                "error": error_message
            })

            return PipelineResult(
                pipeline_id=input_data.pipeline_id,
                prompt=input_data.prompt,
                steps=step_results,
                final_output=current_text if not error_message else f"Error: {error_message}",
                total_duration_ms=total_duration,
                status=status,
                error=error_message
            )

        except Exception as e:
            total_duration = int((time.time() - pipeline_start) * 1000)
            error_message = f"Pipeline failed: {str(e)}"

            self._emit_event("pipeline_completed", {
                "pipeline_id": input_data.pipeline_id,
                "status": "failed",
                "error": error_message,
                "total_duration_ms": total_duration
            })

            return PipelineResult(
                pipeline_id=input_data.pipeline_id,
                prompt=input_data.prompt,
                steps=step_results,
                final_output=f"Error: {error_message}",
                total_duration_ms=total_duration,
                status="failed",
                error=error_message
            )
