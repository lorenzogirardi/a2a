"""Models for research results."""
from typing import Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Single search result from any source."""
    source: str           # "web" | "docs" | "code"
    title: str
    content: str
    url: Optional[str] = None
    relevance: float      # 0.0 - 1.0
    metadata: dict = {}


class AggregatedResult(BaseModel):
    """Aggregated results from multiple sources."""
    query: str
    results: list[SearchResult]
    summary: str
    search_time_ms: int
    sources_searched: list[str]
    total_results: int
