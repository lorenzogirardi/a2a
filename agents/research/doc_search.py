"""Documentation search agent (mock implementation)."""
import random
from storage.base import StorageBase
from .base import SearchAgentBase
from .models import SearchResult


# Mock documentation results
MOCK_DOC_RESULTS = {
    "python": [
        SearchResult(
            source="docs",
            title="Python Language Reference",
            content="This reference manual describes the syntax and core semantics of the Python language.",
            url="https://docs.python.org/3/reference/",
            relevance=0.95
        ),
        SearchResult(
            source="docs",
            title="Python Standard Library",
            content="The Python Standard Library contains built-in modules for file I/O, system calls, and more.",
            url="https://docs.python.org/3/library/",
            relevance=0.90
        ),
    ],
    "async": [
        SearchResult(
            source="docs",
            title="asyncio — Asynchronous I/O",
            content="asyncio is used as a foundation for multiple Python async frameworks including aiohttp.",
            url="https://docs.python.org/3/library/asyncio.html",
            relevance=0.98
        ),
        SearchResult(
            source="docs",
            title="Coroutines and Tasks",
            content="Coroutines declared with async/await syntax are the preferred way of writing asyncio apps.",
            url="https://docs.python.org/3/library/asyncio-task.html",
            relevance=0.92
        ),
    ],
    "pydantic": [
        SearchResult(
            source="docs",
            title="Pydantic Documentation",
            content="Data validation using Python type annotations. Fast and extensible.",
            url="https://docs.pydantic.dev/",
            relevance=0.96
        ),
        SearchResult(
            source="docs",
            title="Pydantic Models",
            content="The primary means of defining objects in Pydantic is via models (classes that inherit BaseModel).",
            url="https://docs.pydantic.dev/latest/concepts/models/",
            relevance=0.90
        ),
    ],
    "fastapi": [
        SearchResult(
            source="docs",
            title="FastAPI Documentation",
            content="FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
            url="https://fastapi.tiangolo.com/",
            relevance=0.97
        ),
    ],
}


class DocSearchAgent(SearchAgentBase):
    """Search agent for documentation (mock)."""

    source_name = "docs"

    def __init__(self, storage: StorageBase):
        super().__init__("doc-search", storage)

    async def search(self, query: str) -> list[SearchResult]:
        """Search documentation for query (mock implementation)."""
        results = []
        query_lower = query.lower()

        # Find matching results from mock database
        for keyword, keyword_results in MOCK_DOC_RESULTS.items():
            if keyword in query_lower:
                results.extend(keyword_results)

        # If no specific matches, return generic results
        if not results:
            results = [
                SearchResult(
                    source="docs",
                    title=f"Documentation for: {query}",
                    content=f"Technical documentation related to '{query}'",
                    url=f"https://docs.example.com/search?q={query.replace(' ', '+')}",
                    relevance=0.4 + random.random() * 0.3
                )
            ]

        # Add some randomness
        for r in results:
            r.relevance = min(1.0, r.relevance + random.uniform(-0.03, 0.03))

        return sorted(results, key=lambda x: x.relevance, reverse=True)
