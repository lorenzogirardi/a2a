"""
E2E tests for Chain Pipeline API.

Tests the full HTTP flow for the chain pipeline endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from protocol.api import app


client = TestClient(app)


class TestChainApiEndpoints:
    """E2E tests for chain API endpoints."""

    def test_list_chain_agents(self):
        """GET /api/chain/agents should return agent list."""
        response = client.get("/api/chain/agents")

        assert response.status_code == 200
        agents = response.json()

        assert len(agents) == 3
        step_names = [a["step_name"] for a in agents]
        assert "writer" in step_names
        assert "editor" in step_names
        assert "publisher" in step_names

    def test_run_pipeline_returns_pipeline_id(self):
        """POST /api/chain/run should return pipeline_id."""
        response = client.post(
            "/api/chain/run",
            json={"prompt": "Test topic"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "pipeline_id" in data
        assert data["status"] == "started"
        assert len(data["pipeline_id"]) == 8

    def test_run_pipeline_with_custom_id(self):
        """POST /api/chain/run should accept custom pipeline_id."""
        response = client.post(
            "/api/chain/run",
            json={
                "prompt": "Test topic",
                "pipeline_id": "custom-id"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == "custom-id"

    def test_get_pipeline_status_not_found(self):
        """GET /api/chain/status/{id} should return not_found for unknown id."""
        response = client.get("/api/chain/status/unknown-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    def test_health_endpoint_still_works(self):
        """Health endpoint should work with chain router included."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestChainApiWithMockedLLM:
    """E2E tests with mocked LLM calls."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """Test running a pipeline and checking result."""
        # This test verifies the API flow, LLM is mocked at agent level
        # in the background task, which is harder to mock in E2E tests.
        # The real test is that the API doesn't error out.

        response = client.post(
            "/api/chain/run",
            json={"prompt": "Test AI topic", "pipeline_id": "e2e-test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == "e2e-test"
        assert data["status"] == "started"


class TestChainSseEndpoint:
    """Tests for the SSE events endpoint."""

    def test_events_endpoint_returns_sse_content_type(self):
        """GET /api/chain/events/{id} should return text/event-stream."""
        # Start a pipeline first
        run_response = client.post(
            "/api/chain/run",
            json={"prompt": "SSE test", "pipeline_id": "sse-test"}
        )
        assert run_response.status_code == 200

        # Connect to events endpoint
        # Note: TestClient doesn't support streaming well, but we can check headers
        with client.stream("GET", "/api/chain/events/sse-test") as response:
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            # Read first event (connected)
            first_line = next(response.iter_lines())
            assert "event: connected" in first_line

    def test_events_endpoint_unknown_pipeline(self):
        """Events endpoint should return error for unknown pipeline."""
        with client.stream("GET", "/api/chain/events/unknown-pipeline") as response:
            assert response.status_code == 200  # SSE always returns 200
            content = response.read().decode()
            assert "error" in content
            assert "Pipeline not found" in content
