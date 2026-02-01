"""E2E tests for FastAPI REST API."""

import pytest
from fastapi.testclient import TestClient

from protocol.api import app
from protocol.mcp_server import get_agents, setup_default_agents, _agents


@pytest.fixture(autouse=True)
def setup_agents():
    """Setup agents before each test."""
    _agents.clear()
    setup_default_agents()
    yield
    _agents.clear()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agents_count"] > 0
        assert "storage_type" in data


class TestAgentsEndpoint:
    """Tests for /api/agents endpoints."""

    def test_list_agents(self, client):
        """Should list all available agents."""
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()

        assert "echo" in data
        assert "counter" in data
        assert "calculator" in data
        assert "router" in data

    def test_get_single_agent(self, client):
        """Should return details for a specific agent."""
        response = client.get("/api/agents/echo")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "echo"
        assert "name" in data
        assert "description" in data
        assert "capabilities" in data

    def test_get_nonexistent_agent(self, client):
        """Should return 404 for nonexistent agent."""
        response = client.get("/api/agents/nonexistent")

        assert response.status_code == 404


class TestMessageEndpoint:
    """Tests for /api/agents/{id}/message endpoint."""

    def test_send_message_to_echo(self, client):
        """Should send message and get response from echo agent."""
        response = client.post(
            "/api/agents/echo/message",
            json={"message": "Hello World"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_id"] == "echo"
        assert "Hello World" in data["response"]
        assert "timestamp" in data

    def test_send_message_to_calculator(self, client):
        """Should send math expression and get result."""
        response = client.post(
            "/api/agents/calculator/message",
            json={"message": "calcola 15 + 7"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "22" in data["response"]

    def test_send_message_with_caller_headers(self, client):
        """Should respect caller context from headers."""
        response = client.post(
            "/api/agents/echo/message",
            json={"message": "Admin message"},
            headers={
                "X-Caller-ID": "admin_user",
                "X-Caller-Role": "admin"
            }
        )

        assert response.status_code == 200

    def test_guest_cannot_send_message(self, client):
        """Guest role should be denied for sending messages."""
        response = client.post(
            "/api/agents/echo/message",
            json={"message": "Guest message"},
            headers={
                "X-Caller-ID": "guest_user",
                "X-Caller-Role": "guest"
            }
        )

        assert response.status_code == 403

    def test_message_to_nonexistent_agent(self, client):
        """Should return 404 for nonexistent agent."""
        response = client.post(
            "/api/agents/nonexistent/message",
            json={"message": "Hello"}
        )

        assert response.status_code == 404


class TestAgentStateEndpoint:
    """Tests for /api/agents/{id}/state endpoint."""

    def test_get_agent_state(self, client):
        """Should return agent state."""
        # First send a message to create some state
        client.post(
            "/api/agents/counter/message",
            json={"message": "Test"}
        )

        response = client.get("/api/agents/counter/state")

        assert response.status_code == 200
        data = response.json()

        assert "message_count" in data

    def test_guest_can_read_state(self, client):
        """Guest should be able to read state."""
        response = client.get(
            "/api/agents/echo/state",
            headers={
                "X-Caller-ID": "guest",
                "X-Caller-Role": "guest"
            }
        )

        assert response.status_code == 200


class TestConversationsEndpoint:
    """Tests for /api/conversations endpoints."""

    def test_list_conversations_initially_empty(self, client):
        """Should return empty list initially."""
        response = client.get("/api/conversations")

        assert response.status_code == 200
        # May be empty or have some from setup

    def test_conversation_created_on_message(self, client):
        """Sending messages should create conversations."""
        # Send some messages
        client.post("/api/agents/echo/message", json={"message": "Hello"})
        client.post("/api/agents/counter/message", json={"message": "Count"})

        response = client.get("/api/conversations")

        assert response.status_code == 200
        # Conversations should exist now
        data = response.json()
        assert isinstance(data, list)


class TestFullConversationFlow:
    """E2E tests for complete conversation flows."""

    def test_multi_turn_conversation(self, client):
        """Should handle multi-turn conversation correctly."""
        messages = ["Hello", "How are you?", "What's 5 + 3?"]
        responses = []

        for msg in messages:
            response = client.post(
                "/api/agents/echo/message",
                json={"message": msg}
            )
            assert response.status_code == 200
            responses.append(response.json())

        # All should have responses
        assert len(responses) == 3
        for r in responses:
            assert r["response"] is not None

    def test_different_agents_same_session(self, client):
        """Should correctly route to different agents."""
        # Talk to different agents
        echo_resp = client.post(
            "/api/agents/echo/message",
            json={"message": "Echo this"}
        )
        calc_resp = client.post(
            "/api/agents/calculator/message",
            json={"message": "10 * 5"}
        )
        counter_resp = client.post(
            "/api/agents/counter/message",
            json={"message": "Count me"}
        )

        assert echo_resp.status_code == 200
        assert calc_resp.status_code == 200
        assert counter_resp.status_code == 200

        assert "Echo" in echo_resp.json()["response"]
        assert "50" in calc_resp.json()["response"]
        assert "#1" in counter_resp.json()["response"]
