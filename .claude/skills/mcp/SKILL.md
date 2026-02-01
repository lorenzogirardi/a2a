---
name: mcp
description: >-
  FastMCP and FastAPI patterns for A2A project. Covers FastMCP server setup,
  tool decorators, FastAPI integration, and agent exposure.
  Triggers on "mcp", "fastmcp", "fastapi", "tool definition", "mcp server",
  "api endpoint", "agent protocol".
  PROACTIVE: Invoke when working on protocol/ or agent communication.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# MCP Skill (FastMCP + FastAPI)

## Quick Reference

| Technology | Purpose |
|------------|---------|
| **FastMCP** | MCP server with decorators |
| **FastAPI** | REST API for non-MCP clients |
| **Pydantic** | Shared models |
| **uvicorn** | ASGI server |

---

## Architecture

```
┌─────────────────┐       ┌─────────────────────────────────┐
│  MCP Client     │       │         A2A Server              │
│  (Claude, etc.) │◄─────►│  ┌─────────────────────────┐   │
└─────────────────┘       │  │  FastMCP (stdio/SSE)    │   │
                          │  │  @mcp.tool() decorators │   │
┌─────────────────┐       │  └─────────────────────────┘   │
│  HTTP Client    │       │                                 │
│  (curl, etc.)   │◄─────►│  ┌─────────────────────────┐   │
└─────────────────┘       │  │  FastAPI (REST)         │   │
                          │  │  /api/agents, /health   │   │
                          │  └─────────────────────────┘   │
                          │              │                  │
                          │              ▼                  │
                          │  ┌─────────────────────────┐   │
                          │  │  Agents + Storage       │   │
                          │  └─────────────────────────┘   │
                          └─────────────────────────────────┘
```

---

## FastMCP Server Setup

### Basic Server

```python
from fastmcp import FastMCP

mcp = FastMCP("a2a-agents")

@mcp.tool()
def echo_message(message: str) -> str:
    """Echo a message back."""
    return f"Echo: {message}"

@mcp.tool()
async def send_to_agent(
    agent_id: str,
    message: str,
    caller_id: str = "anonymous"
) -> dict:
    """Send a message to a specific agent."""
    agent = agents.get(agent_id)
    if not agent:
        return {"error": f"Agent {agent_id} not found"}

    ctx = user_context(caller_id)
    response = await agent.receive_message(
        ctx=ctx,
        content=message,
        sender_id=caller_id
    )
    return {
        "agent": agent_id,
        "response": response.content
    }
```

### With Resources

```python
@mcp.resource("agents://list")
def list_agents() -> str:
    """List all available agents."""
    return json.dumps(list(agents.keys()))

@mcp.resource("agents://{agent_id}/state")
async def get_agent_state(agent_id: str) -> str:
    """Get the state of a specific agent."""
    agent = agents.get(agent_id)
    if not agent:
        return json.dumps({"error": "Not found"})
    state = await agent.get_state(admin_context())
    return json.dumps(state, default=str)
```

---

## FastAPI Integration

### REST API Setup

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="A2A Agent API")

class MessageRequest(BaseModel):
    message: str
    caller_id: str = "api_user"
    conversation_id: str | None = None

class MessageResponse(BaseModel):
    agent_id: str
    response: str
    timestamp: str

@app.get("/health")
async def health():
    return {"status": "ok", "agents": len(agents)}

@app.get("/api/agents")
async def list_agents():
    return {
        agent_id: {
            "name": agent.name,
            "description": agent.config.description
        }
        for agent_id, agent in agents.items()
    }

@app.post("/api/agents/{agent_id}/message")
async def send_message(agent_id: str, request: MessageRequest) -> MessageResponse:
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    ctx = user_context(request.caller_id)
    response = await agent.receive_message(
        ctx=ctx,
        content=request.message,
        sender_id=request.caller_id,
        conversation_id=request.conversation_id
    )

    return MessageResponse(
        agent_id=agent_id,
        response=response.content,
        timestamp=response.timestamp.isoformat()
    )
```

---

## Running Both Servers

### Option 1: Separate Processes

```bash
# Terminal 1: FastMCP (for Claude Desktop)
python -m protocol.mcp_server

# Terminal 2: FastAPI (for REST clients)
uvicorn protocol.api:app --reload --port 8000
```

### Option 2: Combined Entry Point

```python
# run_servers.py
import asyncio
import uvicorn
from protocol.mcp_server import mcp
from protocol.api import app

async def run_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import sys
    if "--mcp" in sys.argv:
        mcp.run()  # stdio mode for Claude
    else:
        asyncio.run(run_fastapi())  # HTTP mode
```

---

## Claude Desktop Integration

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "a2a-agents": {
      "command": "python",
      "args": ["-m", "protocol.mcp_server"],
      "cwd": "/path/to/a2a"
    }
  }
}
```

---

## Permission Handling

### In FastMCP Tools

```python
@mcp.tool()
async def admin_operation(
    action: str,
    caller_role: str = "user"  # Client must specify
) -> dict:
    """Perform admin operation (requires admin role)."""
    if caller_role != "admin":
        return {"error": "Permission denied", "required": "admin"}

    # ... perform action
```

### In FastAPI with Dependencies

```python
from fastapi import Depends, Header

async def get_caller_context(
    x_caller_id: str = Header(default="anonymous"),
    x_caller_role: str = Header(default="user")
) -> CallerContext:
    return CallerContext(
        caller_id=x_caller_id,
        role=Role(x_caller_role)
    )

@app.post("/api/agents/{agent_id}/message")
async def send_message(
    agent_id: str,
    request: MessageRequest,
    ctx: CallerContext = Depends(get_caller_context)
):
    # ctx is already validated
    ...
```

---

## Testing

### FastMCP Tools

```python
@pytest.mark.asyncio
async def test_echo_tool():
    result = echo_message("hello")
    assert "hello" in result

@pytest.mark.asyncio
async def test_agent_tool():
    result = await send_to_agent("echo", "test", "tester")
    assert result["response"] is not None
```

### FastAPI Endpoints

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_list_agents():
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert "echo" in response.json()

def test_send_message():
    response = client.post(
        "/api/agents/echo/message",
        json={"message": "hello", "caller_id": "tester"}
    )
    assert response.status_code == 200
    assert "hello" in response.json()["response"].lower()
```

---

## Checklist

Before committing MCP/API changes:

- [ ] FastMCP tools have docstrings (become descriptions)
- [ ] Pydantic models for request/response
- [ ] CallerContext properly extracted
- [ ] Errors return structured responses
- [ ] Both MCP and REST tested
- [ ] Claude Desktop config documented
