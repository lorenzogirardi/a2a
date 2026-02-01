"""Integration tests for SSE transport."""

import pytest
from httpx import AsyncClient, ASGITransport

from protocol.api import app
from protocol.mcp_server import setup_default_agents
from protocol.sse import SSEEvent, broadcast_event


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    # Ensure agents are set up
    setup_default_agents()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestSSEStatus:
    """Tests for SSE status endpoint."""

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client):
        """Should return SSE status."""
        response = await client.get("/sse/status")

        assert response.status_code == 200
        data = response.json()
        assert "connected_clients" in data
        assert "client_ids" in data


class TestSSEToolCall:
    """Tests for SSE tool calling."""

    @pytest.mark.asyncio
    async def test_call_list_agents(self, client):
        """Should list agents via SSE call."""
        response = await client.post(
            "/sse/call",
            json={"tool": "list_agents", "params": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "echo" in data["result"]

    @pytest.mark.asyncio
    async def test_call_research(self, client):
        """Should perform research via SSE call."""
        response = await client.post(
            "/sse/call",
            json={"tool": "research", "params": {"query": "python"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["query"] == "python"
        assert data["result"]["total_results"] > 0

    @pytest.mark.asyncio
    async def test_call_send_message(self, client):
        """Should send message to agent via SSE."""
        response = await client.post(
            "/sse/call",
            json={
                "tool": "send_message",
                "params": {
                    "agent_id": "echo",
                    "message": "Hello SSE!"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Hello SSE!" in data["result"]["response"]

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, client):
        """Should return error for unknown tool."""
        response = await client.post(
            "/sse/call",
            json={"tool": "nonexistent", "params": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["error"] == "tool_not_found"
        assert "available_tools" in data

    @pytest.mark.asyncio
    async def test_call_get_agent_state(self, client):
        """Should get agent state via SSE."""
        # First send a message to create some state
        await client.post(
            "/sse/call",
            json={
                "tool": "send_message",
                "params": {"agent_id": "counter", "message": "test"}
            }
        )

        # Then get state
        response = await client.post(
            "/sse/call",
            json={
                "tool": "get_agent_state",
                "params": {"agent_id": "counter"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSSEEvent:
    """Tests for SSE event formatting."""

    def test_event_format(self):
        """Should format SSE event correctly."""
        event = SSEEvent(
            event="test",
            data={"message": "hello"},
            id="123"
        )

        formatted = event.format()

        assert "id: 123" in formatted
        assert "event: test" in formatted
        assert 'data: {"message": "hello"}' in formatted

    def test_event_format_no_id(self):
        """Should format without id."""
        event = SSEEvent(
            event="test",
            data={"value": 42}
        )

        formatted = event.format()

        assert "id:" not in formatted
        assert "event: test" in formatted
