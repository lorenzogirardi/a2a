"""
Unit tests for chain pipeline agents.

Tests the chain pattern: Writer -> Editor -> Publisher
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from storage.memory import MemoryStorage


# ============================================
# Phase 1: Models Tests
# ============================================

class TestChainModels:
    """Test Pydantic models for chain pipeline."""

    def test_step_result_creation(self):
        """StepResult should capture step execution details."""
        from agents.chain.models import StepResult

        result = StepResult(
            step_name="writer",
            step_index=0,
            input_text="Write about AI",
            output_text="AI is transforming...",
            duration_ms=150
        )

        assert result.step_name == "writer"
        assert result.step_index == 0
        assert result.input_text == "Write about AI"
        assert result.output_text == "AI is transforming..."
        assert result.duration_ms == 150

    def test_pipeline_input_creation(self):
        """PipelineInput should capture initial prompt and config."""
        from agents.chain.models import PipelineInput

        input_data = PipelineInput(
            prompt="Write about climate change",
            steps=["writer", "editor", "publisher"]
        )

        assert input_data.prompt == "Write about climate change"
        assert input_data.steps == ["writer", "editor", "publisher"]
        assert input_data.pipeline_id is not None  # Auto-generated

    def test_pipeline_input_custom_id(self):
        """PipelineInput should accept custom pipeline_id."""
        from agents.chain.models import PipelineInput

        input_data = PipelineInput(
            prompt="Test",
            pipeline_id="custom-123"
        )

        assert input_data.pipeline_id == "custom-123"

    def test_pipeline_result_creation(self):
        """PipelineResult should aggregate all step results."""
        from agents.chain.models import PipelineResult, StepResult

        steps = [
            StepResult(
                step_name="writer",
                step_index=0,
                input_text="Topic",
                output_text="Draft",
                duration_ms=100
            ),
            StepResult(
                step_name="editor",
                step_index=1,
                input_text="Draft",
                output_text="Edited",
                duration_ms=120
            )
        ]

        result = PipelineResult(
            pipeline_id="test-123",
            prompt="Topic",
            steps=steps,
            final_output="Edited",
            total_duration_ms=220,
            status="completed"
        )

        assert result.pipeline_id == "test-123"
        assert len(result.steps) == 2
        assert result.final_output == "Edited"
        assert result.status == "completed"

    def test_pipeline_result_status_validation(self):
        """PipelineResult status should be one of: pending, running, completed, failed."""
        from agents.chain.models import PipelineResult
        from pydantic import ValidationError

        # Valid statuses
        for status in ["pending", "running", "completed", "failed"]:
            result = PipelineResult(
                pipeline_id="test",
                prompt="test",
                steps=[],
                final_output="",
                total_duration_ms=0,
                status=status
            )
            assert result.status == status

        # Invalid status
        with pytest.raises(ValidationError):
            PipelineResult(
                pipeline_id="test",
                prompt="test",
                steps=[],
                final_output="",
                total_duration_ms=0,
                status="invalid"
            )


# ============================================
# Phase 2: ChainStepAgent Base Tests
# ============================================

class TestChainStepAgent:
    """Test base class for chain step agents."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    def test_chain_step_agent_has_step_name(self, storage):
        """ChainStepAgent must have step_name attribute."""
        from agents.chain.base import ChainStepAgent

        class TestStep(ChainStepAgent):
            step_name = "test_step"

            async def transform(self, text: str) -> str:
                return text

        agent = TestStep(
            agent_id="test-agent",
            storage=storage,
            system_prompt="Test prompt"
        )

        assert agent.step_name == "test_step"

    @pytest.mark.asyncio
    async def test_transform_method_must_be_implemented(self, storage):
        """Subclasses must implement transform method."""
        from agents.chain.base import ChainStepAgent

        class IncompleteStep(ChainStepAgent):
            step_name = "incomplete"
            # Missing transform method

        with pytest.raises(TypeError):
            IncompleteStep(
                agent_id="test",
                storage=storage,
                system_prompt="Test"
            )


# ============================================
# Phase 3: Individual Agent Tests (Mocked LLM)
# ============================================

class TestWriterAgent:
    """Test WriterAgent with mocked LLM calls."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.mark.asyncio
    async def test_writer_agent_transform(self, storage):
        """WriterAgent.transform should generate text."""
        from agents.chain.writer import WriterAgent

        agent = WriterAgent(storage)

        # Mock the LLM call
        with patch.object(agent, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Generated text about AI..."

            result = await agent.transform("Write about AI")

            assert result == "Generated text about AI..."
            mock_llm.assert_called_once()

    def test_writer_agent_has_correct_step_name(self, storage):
        """WriterAgent should have step_name='writer'."""
        from agents.chain.writer import WriterAgent

        agent = WriterAgent(storage)
        assert agent.step_name == "writer"

    def test_writer_agent_has_system_prompt(self, storage):
        """WriterAgent should have appropriate system prompt."""
        from agents.chain.writer import WriterAgent

        agent = WriterAgent(storage)
        assert "scrittore" in agent.system_prompt.lower() or "writer" in agent.system_prompt.lower()


class TestEditorAgent:
    """Test EditorAgent with mocked LLM calls."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.mark.asyncio
    async def test_editor_agent_transform(self, storage):
        """EditorAgent.transform should improve text."""
        from agents.chain.editor import EditorAgent

        agent = EditorAgent(storage)

        with patch.object(agent, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Improved and edited text..."

            result = await agent.transform("Raw draft text")

            assert result == "Improved and edited text..."
            mock_llm.assert_called_once()

    def test_editor_agent_has_correct_step_name(self, storage):
        """EditorAgent should have step_name='editor'."""
        from agents.chain.editor import EditorAgent

        agent = EditorAgent(storage)
        assert agent.step_name == "editor"

    def test_editor_agent_has_system_prompt(self, storage):
        """EditorAgent should have appropriate system prompt."""
        from agents.chain.editor import EditorAgent

        agent = EditorAgent(storage)
        assert "editor" in agent.system_prompt.lower()


class TestPublisherAgent:
    """Test PublisherAgent with mocked LLM calls."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.mark.asyncio
    async def test_publisher_agent_transform(self, storage):
        """PublisherAgent.transform should format for publication."""
        from agents.chain.publisher import PublisherAgent

        agent = PublisherAgent(storage)

        with patch.object(agent, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "# Title\n\nFormatted content..."

            result = await agent.transform("Edited text")

            assert result == "# Title\n\nFormatted content..."
            mock_llm.assert_called_once()

    def test_publisher_agent_has_correct_step_name(self, storage):
        """PublisherAgent should have step_name='publisher'."""
        from agents.chain.publisher import PublisherAgent

        agent = PublisherAgent(storage)
        assert agent.step_name == "publisher"

    def test_publisher_agent_has_system_prompt(self, storage):
        """PublisherAgent should have appropriate system prompt."""
        from agents.chain.publisher import PublisherAgent

        agent = PublisherAgent(storage)
        assert "publisher" in agent.system_prompt.lower()


# ============================================
# Phase 4: Pipeline Orchestrator Tests
# ============================================

class TestChainPipeline:
    """Test ChainPipeline orchestrator."""

    @pytest.fixture
    def storage(self):
        return MemoryStorage()

    @pytest.fixture
    def mock_agents(self, storage):
        """Create mock agents for testing."""
        from agents.chain.base import ChainStepAgent

        class MockWriter(ChainStepAgent):
            step_name = "writer"

            async def transform(self, text: str) -> str:
                return f"Written: {text}"

        class MockEditor(ChainStepAgent):
            step_name = "editor"

            async def transform(self, text: str) -> str:
                return f"Edited: {text}"

        class MockPublisher(ChainStepAgent):
            step_name = "publisher"

            async def transform(self, text: str) -> str:
                return f"Published: {text}"

        return {
            "writer": MockWriter("mock-writer", storage, "Writer"),
            "editor": MockEditor("mock-editor", storage, "Editor"),
            "publisher": MockPublisher("mock-publisher", storage, "Publisher")
        }

    @pytest.mark.asyncio
    async def test_pipeline_executes_steps_in_order(self, storage, mock_agents):
        """Pipeline should execute steps sequentially."""
        from agents.chain.pipeline import ChainPipeline
        from agents.chain.models import PipelineInput

        pipeline = ChainPipeline(
            storage=storage,
            agents=[
                mock_agents["writer"],
                mock_agents["editor"],
                mock_agents["publisher"]
            ]
        )

        input_data = PipelineInput(prompt="AI topic")
        result = await pipeline.run(input_data)

        # Final output should reflect all transformations
        assert "Written" in result.final_output
        assert "Edited" in result.final_output
        assert "Published" in result.final_output
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_captures_step_results(self, storage, mock_agents):
        """Pipeline should capture results from each step."""
        from agents.chain.pipeline import ChainPipeline
        from agents.chain.models import PipelineInput

        pipeline = ChainPipeline(
            storage=storage,
            agents=[
                mock_agents["writer"],
                mock_agents["editor"]
            ]
        )

        input_data = PipelineInput(prompt="Test")
        result = await pipeline.run(input_data)

        assert len(result.steps) == 2
        assert result.steps[0].step_name == "writer"
        assert result.steps[1].step_name == "editor"
        assert result.steps[0].step_index == 0
        assert result.steps[1].step_index == 1

    @pytest.mark.asyncio
    async def test_pipeline_calculates_total_duration(self, storage, mock_agents):
        """Pipeline should calculate total duration."""
        from agents.chain.pipeline import ChainPipeline
        from agents.chain.models import PipelineInput

        pipeline = ChainPipeline(
            storage=storage,
            agents=[mock_agents["writer"]]
        )

        input_data = PipelineInput(prompt="Test")
        result = await pipeline.run(input_data)

        assert result.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_pipeline_broadcasts_events(self, storage, mock_agents):
        """Pipeline should emit SSE events during execution."""
        from agents.chain.pipeline import ChainPipeline
        from agents.chain.models import PipelineInput

        events = []

        def event_handler(event):
            events.append(event)

        pipeline = ChainPipeline(
            storage=storage,
            agents=[mock_agents["writer"], mock_agents["editor"]],
            event_handler=event_handler
        )

        input_data = PipelineInput(prompt="Test")
        await pipeline.run(input_data)

        # Should have: pipeline_started, step_started x2, step_completed x2, pipeline_completed
        event_types = [e["event"] for e in events]
        assert "pipeline_started" in event_types
        assert "step_started" in event_types
        assert "step_completed" in event_types
        assert "pipeline_completed" in event_types

    @pytest.mark.asyncio
    async def test_pipeline_handles_step_failure(self, storage):
        """Pipeline should handle step failures gracefully."""
        from agents.chain.pipeline import ChainPipeline
        from agents.chain.models import PipelineInput
        from agents.chain.base import ChainStepAgent

        class FailingAgent(ChainStepAgent):
            step_name = "failing"

            async def transform(self, text: str) -> str:
                raise ValueError("Simulated failure")

        pipeline = ChainPipeline(
            storage=storage,
            agents=[FailingAgent("fail", storage, "Fail")]
        )

        input_data = PipelineInput(prompt="Test")
        result = await pipeline.run(input_data)

        assert result.status == "failed"
        assert "error" in result.final_output.lower() or len(result.steps) == 0
