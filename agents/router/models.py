"""
Smart Router Models - Data structures for task routing.

Defines:
- TaskInput: User's task to route
- CapabilityMatch: Agent matched to a capability
- ExecutionResult: Result from executing on an agent
- RouterResult: Complete routing result
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def generate_task_id() -> str:
    """Generate a short unique task ID."""
    return uuid.uuid4().hex[:8]


class TaskInput(BaseModel):
    """Input for the router."""
    task: str
    task_id: str = Field(default_factory=generate_task_id)
    timestamp: datetime = Field(default_factory=datetime.now)


class CapabilityMatch(BaseModel):
    """A capability matched to agents."""
    capability: str
    agent_ids: list[str] = Field(default_factory=list)
    matched: bool = False


class ExecutionResult(BaseModel):
    """Result from executing a task on an agent."""
    agent_id: str
    agent_name: str
    capability: str
    input_text: str
    output_text: str
    duration_ms: int
    success: bool = True
    error: Optional[str] = None
    tokens: dict = Field(default_factory=lambda: {"input": 0, "output": 0})


class AnalysisResult(BaseModel):
    """Result from analyzing a task."""
    task_id: str
    original_task: str
    detected_capabilities: list[str] = Field(default_factory=list)
    subtasks: dict[str, str] = Field(default_factory=dict)  # capability -> subtask
    duration_ms: int = 0


class SynthesisResult(BaseModel):
    """Result from synthesizing multiple execution outputs."""
    synthesized_output: str = ""
    duration_ms: int = 0
    sources: list[str] = Field(default_factory=list)  # agent IDs that contributed
    tokens: dict = Field(default_factory=lambda: {"input": 0, "output": 0})


class RouterResult(BaseModel):
    """Complete result from routing a task."""
    task_id: str
    original_task: str
    analysis: AnalysisResult
    matches: list[CapabilityMatch] = Field(default_factory=list)
    executions: list[ExecutionResult] = Field(default_factory=list)
    synthesis: Optional[SynthesisResult] = None  # Phase 2 synthesis
    final_output: str = ""
    total_duration_ms: int = 0
    status: str = "pending"  # pending, analyzing, discovering, executing, synthesizing, completed, failed
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> dict:
        """Sum of all token usage including synthesis."""
        total_input = sum(e.tokens.get("input", 0) for e in self.executions)
        total_output = sum(e.tokens.get("output", 0) for e in self.executions)
        # Add synthesis tokens if present
        if self.synthesis:
            total_input += self.synthesis.tokens.get("input", 0)
            total_output += self.synthesis.tokens.get("output", 0)
        return {"input": total_input, "output": total_output, "total": total_input + total_output}
