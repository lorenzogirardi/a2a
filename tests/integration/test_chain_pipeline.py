"""
Integration tests for Chain Pipeline.

Tests the full flow with real agents (mocked LLM calls).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from storage.memory import MemoryStorage
from agents.chain import (
    ChainPipeline,
    WriterAgent,
    EditorAgent,
    PublisherAgent,
    PipelineInput,
    PipelineResult,
)


class TestChainPipelineIntegration:
    """Integration tests for the chain pipeline flow."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.fixture
    def pipeline_agents(self, storage):
        """Create real agents with mocked LLM."""
        return [
            WriterAgent(storage),
            EditorAgent(storage),
            PublisherAgent(storage)
        ]

    @pytest.mark.asyncio
    async def test_full_pipeline_flow_with_mocked_llm(self, storage, pipeline_agents):
        """Test complete pipeline flow with mocked LLM responses."""
        writer, editor, publisher = pipeline_agents

        # Mock _call_llm for each agent
        with patch.object(writer, '_call_llm', new_callable=AsyncMock) as mock_writer_llm, \
             patch.object(editor, '_call_llm', new_callable=AsyncMock) as mock_editor_llm, \
             patch.object(publisher, '_call_llm', new_callable=AsyncMock) as mock_publisher_llm:

            mock_writer_llm.return_value = "L'intelligenza artificiale sta trasformando il mondo."
            mock_editor_llm.return_value = "L'intelligenza artificiale sta rivoluzionando il mondo moderno."
            mock_publisher_llm.return_value = "# L'IA nel Mondo Moderno\n\nL'intelligenza artificiale sta rivoluzionando il mondo moderno.\n\n## Conclusione\n\nIl futuro è promettente."

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer, editor, publisher]
            )

            input_data = PipelineInput(prompt="Scrivi dell'intelligenza artificiale")
            result = await pipeline.run(input_data)

            # Verify pipeline completed successfully
            assert result.status == "completed"
            assert len(result.steps) == 3
            assert result.steps[0].step_name == "writer"
            assert result.steps[1].step_name == "editor"
            assert result.steps[2].step_name == "publisher"

            # Verify final output is from publisher
            assert "# L'IA nel Mondo Moderno" in result.final_output

            # Verify LLM was called for each step
            mock_writer_llm.assert_called_once()
            mock_editor_llm.assert_called_once()
            mock_publisher_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_passes_output_between_steps(self, storage, pipeline_agents):
        """Verify that each step receives output from previous step."""
        writer, editor, publisher = pipeline_agents

        captured_inputs = []

        async def capture_writer(text):
            captured_inputs.append(("writer", text))
            return "Writer output"

        async def capture_editor(text):
            captured_inputs.append(("editor", text))
            return "Editor output"

        async def capture_publisher(text):
            captured_inputs.append(("publisher", text))
            return "Publisher output"

        with patch.object(writer, '_call_llm', side_effect=capture_writer), \
             patch.object(editor, '_call_llm', side_effect=capture_editor), \
             patch.object(publisher, '_call_llm', side_effect=capture_publisher):

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer, editor, publisher]
            )

            input_data = PipelineInput(prompt="Initial prompt")
            await pipeline.run(input_data)

            # Writer receives original prompt
            assert captured_inputs[0] == ("writer", "Initial prompt")
            # Editor receives writer's output
            assert captured_inputs[1] == ("editor", "Writer output")
            # Publisher receives editor's output
            assert captured_inputs[2] == ("publisher", "Editor output")

    @pytest.mark.asyncio
    async def test_pipeline_sse_events_sequence(self, storage, pipeline_agents):
        """Verify SSE events are emitted in correct order."""
        writer, editor, publisher = pipeline_agents
        events = []

        def event_handler(event):
            events.append(event)

        with patch.object(writer, '_call_llm', new_callable=AsyncMock) as m1, \
             patch.object(editor, '_call_llm', new_callable=AsyncMock) as m2, \
             patch.object(publisher, '_call_llm', new_callable=AsyncMock) as m3:

            m1.return_value = "Writer out"
            m2.return_value = "Editor out"
            m3.return_value = "Publisher out"

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer, editor, publisher],
                event_handler=event_handler
            )

            input_data = PipelineInput(prompt="Test", pipeline_id="test-123")
            await pipeline.run(input_data)

        # Extract event types
        event_types = [e["event"] for e in events]

        # Verify event sequence
        expected_sequence = [
            "pipeline_started",
            "step_started",    # writer
            "step_completed",  # writer
            "message_passed",  # writer -> editor
            "step_started",    # editor
            "step_completed",  # editor
            "message_passed",  # editor -> publisher
            "step_started",    # publisher
            "step_completed",  # publisher
            "pipeline_completed"
        ]

        assert event_types == expected_sequence

        # Verify pipeline_id is in all events
        for event in events:
            assert event["data"]["pipeline_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_pipeline_handles_llm_failure(self, storage, pipeline_agents):
        """Pipeline should handle LLM failures gracefully."""
        writer, editor, publisher = pipeline_agents

        with patch.object(writer, '_call_llm', new_callable=AsyncMock) as m1, \
             patch.object(editor, '_call_llm', new_callable=AsyncMock) as m2:

            m1.return_value = "Writer output"
            m2.side_effect = RuntimeError("LLM API failed")

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer, editor, publisher]
            )

            input_data = PipelineInput(prompt="Test")
            result = await pipeline.run(input_data)

            assert result.status == "failed"
            assert "editor" in result.error.lower()
            assert len(result.steps) == 1  # Only writer completed

    @pytest.mark.asyncio
    async def test_pipeline_with_single_agent(self, storage):
        """Pipeline should work with just one agent."""
        writer = WriterAgent(storage)

        with patch.object(writer, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Generated text"

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer]
            )

            input_data = PipelineInput(prompt="Topic")
            result = await pipeline.run(input_data)

            assert result.status == "completed"
            assert len(result.steps) == 1
            assert result.final_output == "Generated text"

    @pytest.mark.asyncio
    async def test_pipeline_measures_duration_per_step(self, storage, pipeline_agents):
        """Each step should record its execution duration."""
        writer, editor, publisher = pipeline_agents

        import asyncio

        async def slow_writer(text):
            await asyncio.sleep(0.05)  # 50ms
            return "Output"

        async def fast_editor(text):
            return "Output"

        with patch.object(writer, '_call_llm', side_effect=slow_writer), \
             patch.object(editor, '_call_llm', side_effect=fast_editor), \
             patch.object(publisher, '_call_llm', new_callable=AsyncMock) as m3:
            m3.return_value = "Final"

            pipeline = ChainPipeline(
                storage=storage,
                agents=[writer, editor, publisher]
            )

            input_data = PipelineInput(prompt="Test")
            result = await pipeline.run(input_data)

            # Writer should be slower than editor
            assert result.steps[0].duration_ms >= 40  # Allow some margin
            assert result.total_duration_ms >= result.steps[0].duration_ms


class TestChainAgentIntegration:
    """Integration tests for individual chain agents."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.mark.asyncio
    async def test_writer_agent_uses_storage(self, storage):
        """WriterAgent should use storage for conversation context."""
        writer = WriterAgent(storage)

        # Mock LiteLLM response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Generated"
        mock_message.tool_calls = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            result = await writer._call_llm("Test prompt")

            assert result == "Generated"
            mock_acompletion.assert_called_once()

    @pytest.mark.asyncio
    async def test_agents_have_correct_capabilities(self, storage):
        """Chain agents should have appropriate capabilities."""
        writer = WriterAgent(storage)
        editor = EditorAgent(storage)
        publisher = PublisherAgent(storage)

        # All should have conversation capability (from LLMAgent)
        assert "conversation" in writer.config.capabilities
        assert "conversation" in editor.config.capabilities
        assert "conversation" in publisher.config.capabilities
