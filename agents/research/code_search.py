"""Code search agent (mock implementation)."""
import random
from storage.base import StorageBase
from .base import SearchAgentBase
from .models import SearchResult


# Mock code search results
MOCK_CODE_RESULTS = {
    "async": [
        SearchResult(
            source="code",
            title="asyncio.gather example",
            content="""async def main():
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3")
    )
    return results""",
            url="https://github.com/example/async-patterns/blob/main/gather.py",
            relevance=0.93,
            metadata={"language": "python", "lines": 7}
        ),
        SearchResult(
            source="code",
            title="async/await basic pattern",
            content="""async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()""",
            url="https://github.com/example/async-patterns/blob/main/fetch.py",
            relevance=0.88,
            metadata={"language": "python", "lines": 5}
        ),
    ],
    "agent": [
        SearchResult(
            source="code",
            title="Agent base class implementation",
            content="""class AgentBase(ABC):
    @abstractmethod
    async def think(self, message: Message) -> dict:
        pass

    @abstractmethod
    async def act(self, actions: list) -> list:
        pass""",
            url="https://github.com/example/agents/blob/main/base.py",
            relevance=0.95,
            metadata={"language": "python", "lines": 8}
        ),
    ],
    "pydantic": [
        SearchResult(
            source="code",
            title="Pydantic model example",
            content="""class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.now)""",
            url="https://github.com/example/models/blob/main/user.py",
            relevance=0.90,
            metadata={"language": "python", "lines": 5}
        ),
    ],
    "fastapi": [
        SearchResult(
            source="code",
            title="FastAPI endpoint example",
            content="""@app.post("/users/", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.create_user(db, user)
    return db_user""",
            url="https://github.com/example/api/blob/main/routes.py",
            relevance=0.92,
            metadata={"language": "python", "lines": 4}
        ),
    ],
}


class CodeSearchAgent(SearchAgentBase):
    """Search agent for code examples (mock)."""

    source_name = "code"

    def __init__(self, storage: StorageBase):
        super().__init__("code-search", storage)

    async def search(self, query: str) -> list[SearchResult]:
        """Search code repositories for query (mock implementation)."""
        results = []
        query_lower = query.lower()

        # Find matching results from mock database
        for keyword, keyword_results in MOCK_CODE_RESULTS.items():
            if keyword in query_lower:
                results.extend(keyword_results)

        # If no specific matches, return generic results
        if not results:
            results = [
                SearchResult(
                    source="code",
                    title=f"Code examples for: {query}",
                    content=f"# Example code for {query}\n# TODO: implementation",
                    url=f"https://github.com/search?q={query.replace(' ', '+')}",
                    relevance=0.3 + random.random() * 0.3,
                    metadata={"language": "python", "lines": 2}
                )
            ]

        # Add some randomness
        for r in results:
            r.relevance = min(1.0, r.relevance + random.uniform(-0.02, 0.02))

        return sorted(results, key=lambda x: x.relevance, reverse=True)
