"""
Smart Router Module - Intelligent task routing.

Provides capability-based routing of tasks to appropriate agents
using the AgentRegistry for dynamic discovery.
"""

from .models import (
    TaskInput,
    CapabilityMatch,
    ExecutionResult,
    AnalysisResult,
    SynthesisResult,
    RouterResult
)
from .analyzer import AnalyzerAgent, AVAILABLE_CAPABILITIES
from .synthesizer import SynthesizerAgent
from .executor import TaskExecutor
from .router import SmartRouter

__all__ = [
    # Models
    "TaskInput",
    "CapabilityMatch",
    "ExecutionResult",
    "AnalysisResult",
    "SynthesisResult",
    "RouterResult",
    # Agents
    "AnalyzerAgent",
    "SynthesizerAgent",
    "AVAILABLE_CAPABILITIES",
    # Components
    "TaskExecutor",
    "SmartRouter",
]
