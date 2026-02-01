"""
Chain Pipeline - Document Processing Pipeline Demo.

Demonstrates agent-to-agent communication with:
- Writer: Generates initial text
- Editor: Improves and corrects text
- Publisher: Formats for publication
"""

from .models import PipelineInput, PipelineResult, StepResult
from .base import ChainStepAgent
from .writer import WriterAgent
from .editor import EditorAgent
from .publisher import PublisherAgent
from .pipeline import ChainPipeline

__all__ = [
    "PipelineInput",
    "PipelineResult",
    "StepResult",
    "ChainStepAgent",
    "WriterAgent",
    "EditorAgent",
    "PublisherAgent",
    "ChainPipeline",
]
