"""
Pydantic models for Chain Pipeline.

Defines data structures for pipeline input, output, and step results.
"""

from typing import Literal, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage statistics from LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class StepResult(BaseModel):
    """Result from a single pipeline step execution."""

    step_name: str
    step_index: int
    input_text: str
    output_text: str
    duration_ms: int
    model: str = ""
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class PipelineInput(BaseModel):
    """Input configuration for starting a pipeline."""

    prompt: str
    pipeline_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    steps: list[str] = Field(default_factory=lambda: ["writer", "editor", "publisher"])
    metadata: dict = Field(default_factory=dict)


class PipelineResult(BaseModel):
    """Final result from pipeline execution."""

    pipeline_id: str
    prompt: str
    steps: list[StepResult]
    final_output: str
    total_duration_ms: int
    status: Literal["pending", "running", "completed", "failed"]
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def total_input_tokens(self) -> int:
        return sum(s.tokens.input_tokens for s in self.steps)

    @property
    def total_output_tokens(self) -> int:
        return sum(s.tokens.output_tokens for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def model_dump(self, **kwargs) -> dict:
        """Override to include computed properties."""
        data = super().model_dump(**kwargs)
        data["total_input_tokens"] = self.total_input_tokens
        data["total_output_tokens"] = self.total_output_tokens
        data["total_tokens"] = self.total_tokens
        return data
