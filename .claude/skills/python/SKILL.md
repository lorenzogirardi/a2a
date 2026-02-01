---
name: python
description: >-
  Python conventions for A2A multi-agent project. Covers async patterns, Pydantic,
  type hints, and testing. Triggers on "python", "type error", "py", "pydantic",
  "async", "pytest", "typing".
  PROACTIVE: MUST invoke when writing or editing .py files.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Python Skill (A2A Multi-Agent)

## Quick Reference

| Rule | Convention |
|------|------------|
| Python version | 3.11+ |
| Type hints | Always, use typing module |
| Async | All agent methods are async |
| Validation | Pydantic BaseModel |
| Formatting | Black + isort |
| Testing | pytest + pytest-asyncio |

---

## Project Structure

```
a2a/
├── agents/
│   ├── base.py          # AgentBase, AgentConfig, AgentResponse
│   ├── simple_agent.py  # Concrete agent implementations
│   └── llm_agent.py     # LLM-based agents
├── storage/
│   ├── base.py          # StorageBase, Message, ConversationLog
│   └── memory.py        # MemoryStorage
├── auth/
│   └── permissions.py   # Role, Permission, CallerContext
├── protocol/
│   └── mcp_server.py    # MCP server
└── tests/
```

---

## Type Patterns

### Pydantic Models

```python
from pydantic import BaseModel
from datetime import datetime

class Message(BaseModel):
    id: str
    sender: str
    receiver: str
    content: str
    timestamp: datetime
    metadata: dict = {}

# Validation is automatic
msg = Message(id="1", sender="a", receiver="b", content="hi", timestamp=datetime.now())
```

### Type Hints

```python
from typing import Any, Optional

# Function signatures
async def process(data: dict[str, Any]) -> Optional[str]:
    ...

# Class attributes
class Agent:
    config: AgentConfig
    storage: StorageBase
    _internal_state: dict[str, Any]
```

### Abstract Base Classes

```python
from abc import ABC, abstractmethod

class StorageBase(ABC):
    @abstractmethod
    async def save_message(self, message: Message) -> None:
        pass

    @abstractmethod
    async def get_messages(self, conversation_id: str) -> list[Message]:
        pass
```

---

## Async Patterns

### Agent Methods

```python
class AgentBase(ABC):
    @abstractmethod
    async def think(self, message: Message) -> dict[str, Any]:
        """Must be async - may call storage or other agents."""
        pass

    async def receive_message(self, ctx: CallerContext, content: str, ...) -> AgentResponse:
        # Await storage operations
        await self.storage.save_message(message)

        # Await think/act
        thought = await self.think(message)
        await self.act(thought.get("actions", []))

        return response
```

### Agent-to-Agent Communication

```python
async def send_to_agent(self, target: AgentBase, content: str) -> AgentResponse:
    ctx = agent_context(self.id)
    return await target.receive_message(ctx=ctx, content=content, sender_id=self.id)
```

### Running Async Code

```python
import asyncio

async def main():
    storage = MemoryStorage()
    agent = EchoAgent("echo", storage)
    # ...

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Permission Decorator Pattern

```python
from functools import wraps
from typing import Callable

def requires_permission(permission: Permission):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find CallerContext in args
            ctx = _find_context(args, kwargs)
            if not ctx.has_permission(permission):
                raise PermissionDenied(ctx.caller_id, permission, func.__name__)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@requires_permission(Permission.SEND_MESSAGES)
async def receive_message(self, ctx: CallerContext, content: str, ...) -> AgentResponse:
    ...
```

---

## Testing Patterns (Test Pyramid)

```
tests/
├── unit/                 # 70% - Fast, isolated
│   ├── test_agents.py
│   ├── test_storage.py
│   └── test_permissions.py
├── integration/          # 20% - Components together
│   ├── test_agent_storage.py
│   └── test_agent_to_agent.py
└── e2e/                  # 10% - Full system
    ├── test_fastmcp.py
    └── test_fastapi.py
```

### Unit Tests (Many, Fast)

```python
# tests/unit/test_agents.py
import pytest
from agents import EchoAgent
from storage import MemoryStorage
from auth import user_context, guest_context, PermissionDenied

@pytest.fixture
def storage():
    return MemoryStorage()

@pytest.fixture
def echo_agent(storage):
    return EchoAgent("test-echo", storage)

@pytest.mark.asyncio
async def test_echo_responds(echo_agent):
    ctx = user_context("tester")
    response = await echo_agent.receive_message(
        ctx=ctx,
        content="Hello",
        sender_id="tester"
    )
    assert "Hello" in response.content

@pytest.mark.asyncio
async def test_permission_denied():
    storage = MemoryStorage()
    agent = EchoAgent("echo", storage)
    ctx = guest_context("guest")  # Guest can't send messages

    with pytest.raises(PermissionDenied):
        await agent.receive_message(ctx=ctx, content="hi", sender_id="guest")
```

### Integration Tests (Some, Medium)

```python
# tests/integration/test_agent_to_agent.py
import pytest
from agents import RouterAgent, EchoAgent, CalculatorAgent
from storage import MemoryStorage
from auth import user_context

@pytest.fixture
def agent_system():
    storage = MemoryStorage()
    echo = EchoAgent("echo", storage)
    calc = CalculatorAgent("calc", storage)
    router = RouterAgent("router", storage)
    router.add_route("echo", echo)
    router.add_route("calc", calc)
    return {"router": router, "storage": storage}

@pytest.mark.asyncio
async def test_router_forwards_to_echo(agent_system):
    ctx = user_context("tester")
    response = await agent_system["router"].receive_message(
        ctx=ctx,
        content="echo hello",
        sender_id="tester"
    )
    # Verify routing happened via storage
    messages = await agent_system["storage"].get_messages("default")
    assert len(messages) > 0
```

### E2E Tests (Few, Slow)

```python
# tests/e2e/test_fastapi.py
from fastapi.testclient import TestClient
from protocol.api import app

client = TestClient(app)

def test_full_conversation_flow():
    # Create conversation
    r1 = client.post("/api/agents/echo/message", json={"message": "hi"})
    assert r1.status_code == 200

    # Continue conversation
    r2 = client.post("/api/agents/echo/message", json={"message": "hello"})
    assert r2.status_code == 200

    # Verify state
    r3 = client.get("/api/agents/echo/state")
    assert r3.status_code == 200
```

### Test Configuration

```python
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (components together)",
    "e2e: End-to-end tests (full system)",
]
```

### Running Tests by Layer

```bash
# All tests
pytest

# Only unit tests (fast feedback)
pytest tests/unit/ -v

# Only integration
pytest tests/integration/ -v

# Only e2e
pytest tests/e2e/ -v

# With markers
pytest -m unit
pytest -m "not e2e"  # Skip slow tests
```

---

## Import Organization

```python
# Standard library
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from functools import wraps

# Third-party
from pydantic import BaseModel
from mcp.server import Server

# Local
from storage.base import StorageBase, Message
from auth.permissions import CallerContext, requires_permission
```

---

## Error Handling

```python
# Custom exceptions
class PermissionDenied(Exception):
    def __init__(self, caller_id: str, permission: Permission, operation: str):
        self.caller_id = caller_id
        self.permission = permission
        super().__init__(f"Caller '{caller_id}' lacks '{permission.value}' for '{operation}'")

# Usage in agents
async def receive_message(self, ctx: CallerContext, ...):
    try:
        thought = await self.think(message)
    except Exception as e:
        return AgentResponse(
            content=f"Error: {str(e)}",
            agent_id=self.id,
            timestamp=datetime.now()
        )
```

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python main.py

# Run MCP server
python run_mcp_server.py

# Run tests
pytest

# Run with verbose
pytest -v

# Type checking
mypy .

# Formatting
black .
isort .
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Sync in async | Blocks event loop | Use async/await everywhere |
| `Any` overuse | No type safety | Use specific types |
| Missing ctx | No permission check | Always pass CallerContext |
| Bare except | Hides bugs | Catch specific exceptions |
| Global state | Race conditions | Inject dependencies |

---

## Checklist

Before committing Python changes:

- [ ] Type hints on all functions
- [ ] Pydantic models for data structures
- [ ] async/await for I/O operations
- [ ] CallerContext passed to protected methods
- [ ] Tests cover new functionality
- [ ] `pytest` passes
- [ ] No bare `except:` clauses
