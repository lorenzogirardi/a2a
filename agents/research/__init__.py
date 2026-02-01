"""Research agents for multi-source search."""
from .models import SearchResult, AggregatedResult
from .base import SearchAgentBase
from .web_search import WebSearchAgent
from .doc_search import DocSearchAgent
from .code_search import CodeSearchAgent
from .merge import MergeAgent
from .orchestrator import OrchestratorAgent

__all__ = [
    "SearchResult",
    "AggregatedResult",
    "SearchAgentBase",
    "WebSearchAgent",
    "DocSearchAgent",
    "CodeSearchAgent",
    "MergeAgent",
    "OrchestratorAgent",
]
