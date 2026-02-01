"""Web search agent (mock implementation)."""
import random
from storage.base import StorageBase
from .base import SearchAgentBase
from .models import SearchResult


# Mock web search results database
MOCK_WEB_RESULTS = {
    "python": [
        SearchResult(
            source="web",
            title="Python.org - Official Python Website",
            content="Python is a programming language that lets you work quickly and integrate systems more effectively.",
            url="https://www.python.org",
            relevance=0.95
        ),
        SearchResult(
            source="web",
            title="Python Tutorial - W3Schools",
            content="Learn Python programming with our comprehensive tutorial. Python is easy to learn and powerful.",
            url="https://www.w3schools.com/python/",
            relevance=0.85
        ),
        SearchResult(
            source="web",
            title="Real Python - Python Tutorials",
            content="Real Python offers tutorials and articles on Python programming, web development, and more.",
            url="https://realpython.com",
            relevance=0.80
        ),
    ],
    "async": [
        SearchResult(
            source="web",
            title="Asyncio - Python Documentation",
            content="asyncio is a library to write concurrent code using the async/await syntax.",
            url="https://docs.python.org/3/library/asyncio.html",
            relevance=0.95
        ),
        SearchResult(
            source="web",
            title="Async IO in Python: A Complete Walkthrough",
            content="A deep dive into async programming in Python using asyncio, aiohttp, and more.",
            url="https://realpython.com/async-io-python/",
            relevance=0.90
        ),
    ],
    "agent": [
        SearchResult(
            source="web",
            title="Building AI Agents - Anthropic",
            content="Learn how to build AI agents that can reason, plan, and take actions autonomously.",
            url="https://anthropic.com/agents",
            relevance=0.92
        ),
        SearchResult(
            source="web",
            title="LangChain Agents Documentation",
            content="Agents use LLMs to determine which actions to take and in what order.",
            url="https://python.langchain.com/docs/modules/agents/",
            relevance=0.88
        ),
    ],
}


class WebSearchAgent(SearchAgentBase):
    """Search agent for web results (mock)."""

    source_name = "web"

    def __init__(self, storage: StorageBase):
        super().__init__("web-search", storage)

    async def search(self, query: str) -> list[SearchResult]:
        """Search web for query (mock implementation)."""
        results = []
        query_lower = query.lower()

        # Find matching results from mock database
        for keyword, keyword_results in MOCK_WEB_RESULTS.items():
            if keyword in query_lower:
                results.extend(keyword_results)

        # If no specific matches, return generic results
        if not results:
            results = [
                SearchResult(
                    source="web",
                    title=f"Search results for: {query}",
                    content=f"General web search results for '{query}'",
                    url=f"https://search.example.com?q={query.replace(' ', '+')}",
                    relevance=0.5 + random.random() * 0.3
                )
            ]

        # Add some randomness to relevance for realism
        for r in results:
            r.relevance = min(1.0, r.relevance + random.uniform(-0.05, 0.05))

        return sorted(results, key=lambda x: x.relevance, reverse=True)
