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
    RouterResult
)
from .analyzer import AnalyzerAgent, AVAILABLE_CAPABILITIES
from .executor import TaskExecutor
from .router import SmartRouter

__all__ = [
    # Models
    "TaskInput",
    "CapabilityMatch",
    "ExecutionResult",
    "AnalysisResult",
    "RouterResult",
    # Agents
    "AnalyzerAgent",
    "AVAILABLE_CAPABILITIES",
    # Components
    "TaskExecutor",
    "SmartRouter",
]
