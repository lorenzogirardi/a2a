"""Unit tests for LLM agents."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from agents.llm_agent import LLMAgent, ToolUsingLLMAgent
from storage import MemoryStorage
from storage.base import Message


@pytest.fixture
def storage():
    """Fresh storage for each test."""
    return MemoryStorage()


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic response."""
    def _create(text="Test response", input_tokens=10, output_tokens=20, stop_reason="end_turn"):
        response = Mock()
        content_block = Mock()
        content_block.text = text
        content_block.type = "text"
        response.content = [content_block]
        response.stop_reason = stop_reason
        response.usage = Mock()
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        return response
    return _create


@pytest.fixture
def mock_tool_use_response():
    """Create a mock Anthropic tool_use response."""
    def _create(tool_name, tool_input, tool_id="tool-123"):
        response = Mock()
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = tool_name
        tool_block.input = tool_input
        tool_block.id = tool_id
        response.content = [tool_block]
        response.stop_reason = "tool_use"
        response.usage = Mock()
        response.usage.input_tokens = 10
        response.usage.output_tokens = 20
        return response
    return _create


class TestLLMAgent:
    """Tests for LLMAgent."""

    def test_init(self, storage):
        """Should initialize with correct config."""
        agent = LLMAgent("test-llm", storage, system_prompt="Custom prompt")

        assert agent.id == "test-llm"
        assert agent.system_prompt == "Custom prompt"
        assert agent.model == "claude-sonnet-4-20250514"

    def test_custom_model(self, storage):
        """Should accept custom model."""
        agent = LLMAgent("test", storage, model="claude-3-opus-20240229")
        assert agent.model == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_think_calls_claude(self, storage, mock_anthropic_response):
        """Should call Claude API with correct parameters."""
        agent = LLMAgent("test-llm", storage)

        # Mock the client
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response("Hello!")

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="test-llm",
                content="Hi there",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert result["response"] == "Hello!"
            mock_client.messages.create.assert_called_once()

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"
            assert call_kwargs["system"] == "Sei un assistente utile."
            assert {"role": "user", "content": "Hi there"} in call_kwargs["messages"]

    @pytest.mark.asyncio
    async def test_think_includes_history(self, storage, mock_anthropic_response):
        """Should include conversation history in messages."""
        agent = LLMAgent("test-llm", storage)

        # Add some history
        conv_id = await storage.create_conversation(["user", "test-llm"])

        await storage.save_message(Message(
            id="old-1",
            sender="user",
            receiver="test-llm",
            content="Previous message",
            timestamp=datetime.now(),
            metadata={"conversation_id": conv_id}
        ))

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response("Response")

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-new",
                sender="user",
                receiver="test-llm",
                content="New message",
                timestamp=datetime.now(),
                metadata={"conversation_id": conv_id}
            )

            await agent.think(msg)

            call_kwargs = mock_client.messages.create.call_args[1]
            messages = call_kwargs["messages"]

            # Should have both old and new message
            assert len(messages) >= 2

    @pytest.mark.asyncio
    async def test_think_returns_metadata(self, storage, mock_anthropic_response):
        """Should return token usage in metadata."""
        agent = LLMAgent("test-llm", storage)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Test", input_tokens=50, output_tokens=100
        )

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="test-llm",
                content="Test",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert result["metadata"]["usage"]["input_tokens"] == 50
            assert result["metadata"]["usage"]["output_tokens"] == 100

    @pytest.mark.asyncio
    async def test_think_handles_error(self, storage):
        """Should handle API errors gracefully."""
        agent = LLMAgent("test-llm", storage)

        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="test-llm",
                content="Test",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert "Errore" in result["response"]
            assert "API Error" in result["response"]


class TestToolUsingLLMAgent:
    """Tests for ToolUsingLLMAgent."""

    def test_add_tool(self, storage):
        """Should register tools correctly."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        agent.add_tool(
            name="calculator",
            description="Perform calculations",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            },
            handler=lambda x: eval(x["expression"])
        )

        schemas = agent._get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "calculator"

    @pytest.mark.asyncio
    async def test_execute_tool_sync(self, storage):
        """Should execute sync tool handlers."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        agent.add_tool(
            name="greet",
            description="Greet someone",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=lambda x: f"Hello, {x['name']}!"
        )

        result = await agent._execute_tool("greet", {"name": "World"})
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_tool_async(self, storage):
        """Should execute async tool handlers."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        async def async_handler(x):
            return f"Async hello, {x['name']}!"

        agent.add_tool(
            name="async_greet",
            description="Async greet",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=async_handler
        )

        result = await agent._execute_tool("async_greet", {"name": "Async"})
        assert result == "Async hello, Async!"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, storage):
        """Should handle missing tools gracefully."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        result = await agent._execute_tool("nonexistent", {})
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_execute_tool_error(self, storage):
        """Should handle tool execution errors."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        agent.add_tool(
            name="failing",
            description="Always fails",
            input_schema={"type": "object"},
            handler=lambda x: 1/0  # Division by zero
        )

        result = await agent._execute_tool("failing", {})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_think_with_tool_use(
        self, storage, mock_tool_use_response, mock_anthropic_response
    ):
        """Should execute tools when Claude requests them."""
        agent = ToolUsingLLMAgent("tool-agent", storage)

        # Add a simple tool
        agent.add_tool(
            name="add",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                }
            },
            handler=lambda x: x["a"] + x["b"]
        )

        mock_client = Mock()
        # First call: tool_use, second call: end_turn
        mock_client.messages.create.side_effect = [
            mock_tool_use_response("add", {"a": 2, "b": 3}),
            mock_anthropic_response("The sum is 5")
        ]

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="tool-agent",
                content="What is 2 + 3?",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert result["response"] == "The sum is 5"
            assert len(result["metadata"]["tool_calls"]) == 1
            assert result["metadata"]["tool_calls"][0]["tool"] == "add"
            assert result["metadata"]["tool_calls"][0]["result"] == "5"

    @pytest.mark.asyncio
    async def test_think_no_tools_falls_back(self, storage, mock_anthropic_response):
        """Should use base behavior when no tools registered."""
        agent = ToolUsingLLMAgent("tool-agent", storage)
        # No tools added

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response("Direct response")

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="tool-agent",
                content="Hello",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert result["response"] == "Direct response"
            # Should not have tool-specific metadata
            assert "tool_calls" not in result.get("metadata", {})

    @pytest.mark.asyncio
    async def test_max_tool_rounds(self, storage, mock_tool_use_response):
        """Should stop after max_tool_rounds."""
        agent = ToolUsingLLMAgent("tool-agent", storage, max_tool_rounds=2)

        agent.add_tool(
            name="loop",
            description="Loops forever",
            input_schema={"type": "object"},
            handler=lambda x: "loop"
        )

        mock_client = Mock()
        # Always returns tool_use
        mock_client.messages.create.return_value = mock_tool_use_response("loop", {})

        with patch.object(agent, "_get_client", return_value=mock_client):
            msg = Message(
                id="msg-1",
                sender="user",
                receiver="tool-agent",
                content="Loop forever",
                timestamp=datetime.now()
            )

            result = await agent.think(msg)

            assert "maximum tool rounds" in result["response"]
            assert result["metadata"]["tool_rounds"] == 2
