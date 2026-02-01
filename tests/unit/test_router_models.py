"""Unit tests for router models."""

import pytest
from datetime import datetime

from agents.router.models import (
    TaskInput,
    CapabilityMatch,
    ExecutionResult,
    AnalysisResult,
    RouterResult,
    generate_task_id
)


class TestTaskInput:
    """Tests for TaskInput model."""

    def test_create_with_task(self):
        """TaskInput should accept a task string."""
        task_input = TaskInput(task="calculate 5 + 3")
        assert task_input.task == "calculate 5 + 3"

    def test_auto_generates_task_id(self):
        """TaskInput should auto-generate a task_id."""
        task_input = TaskInput(task="test")
        assert task_input.task_id is not None
        assert len(task_input.task_id) == 8

    def test_auto_generates_timestamp(self):
        """TaskInput should auto-generate a timestamp."""
        task_input = TaskInput(task="test")
        assert task_input.timestamp is not None
        assert isinstance(task_input.timestamp, datetime)

    def test_unique_task_ids(self):
        """Each TaskInput should have a unique task_id."""
        t1 = TaskInput(task="test1")
        t2 = TaskInput(task="test2")
        assert t1.task_id != t2.task_id


class TestCapabilityMatch:
    """Tests for CapabilityMatch model."""

    def test_create_capability_match(self):
        """CapabilityMatch should store capability and agents."""
        match = CapabilityMatch(
            capability="calculation",
            agent_ids=["calc-1", "calc-2"],
            matched=True
        )
        assert match.capability == "calculation"
        assert len(match.agent_ids) == 2
        assert match.matched is True

    def test_default_empty_agents(self):
        """CapabilityMatch should default to empty agent list."""
        match = CapabilityMatch(capability="test")
        assert match.agent_ids == []
        assert match.matched is False


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_create_execution_result(self):
        """ExecutionResult should store execution details."""
        result = ExecutionResult(
            agent_id="calc-1",
            agent_name="Calculator",
            capability="calculation",
            input_text="5 + 3",
            output_text="8",
            duration_ms=150,
            success=True
        )
        assert result.agent_id == "calc-1"
        assert result.output_text == "8"
        assert result.duration_ms == 150

    def test_default_success_true(self):
        """ExecutionResult should default success to True."""
        result = ExecutionResult(
            agent_id="test",
            agent_name="Test",
            capability="test",
            input_text="in",
            output_text="out",
            duration_ms=100
        )
        assert result.success is True

    def test_with_error(self):
        """ExecutionResult should handle error state."""
        result = ExecutionResult(
            agent_id="test",
            agent_name="Test",
            capability="test",
            input_text="in",
            output_text="",
            duration_ms=50,
            success=False,
            error="Agent not available"
        )
        assert result.success is False
        assert result.error == "Agent not available"


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_create_analysis_result(self):
        """AnalysisResult should store analysis details."""
        result = AnalysisResult(
            task_id="abc123",
            original_task="calculate 5 + 3 and write a poem",
            detected_capabilities=["calculation", "creative_writing"],
            subtasks={
                "calculation": "calculate 5 + 3",
                "creative_writing": "write a poem"
            },
            duration_ms=500
        )
        assert len(result.detected_capabilities) == 2
        assert "calculation" in result.detected_capabilities
        assert result.subtasks["calculation"] == "calculate 5 + 3"

    def test_default_empty_capabilities(self):
        """AnalysisResult should default to empty capabilities."""
        result = AnalysisResult(
            task_id="test",
            original_task="test task"
        )
        assert result.detected_capabilities == []
        assert result.subtasks == {}


class TestRouterResult:
    """Tests for RouterResult model."""

    def test_create_router_result(self):
        """RouterResult should combine all results."""
        analysis = AnalysisResult(
            task_id="abc123",
            original_task="test task",
            detected_capabilities=["calculation"]
        )
        result = RouterResult(
            task_id="abc123",
            original_task="test task",
            analysis=analysis,
            status="completed"
        )
        assert result.task_id == "abc123"
        assert result.status == "completed"

    def test_total_tokens_property(self):
        """RouterResult should calculate total tokens."""
        analysis = AnalysisResult(
            task_id="test",
            original_task="test"
        )
        result = RouterResult(
            task_id="test",
            original_task="test",
            analysis=analysis,
            executions=[
                ExecutionResult(
                    agent_id="a1",
                    agent_name="Agent1",
                    capability="cap1",
                    input_text="in",
                    output_text="out",
                    duration_ms=100,
                    tokens={"input": 50, "output": 30}
                ),
                ExecutionResult(
                    agent_id="a2",
                    agent_name="Agent2",
                    capability="cap2",
                    input_text="in",
                    output_text="out",
                    duration_ms=100,
                    tokens={"input": 40, "output": 20}
                )
            ]
        )
        tokens = result.total_tokens
        assert tokens["input"] == 90
        assert tokens["output"] == 50
        assert tokens["total"] == 140

    def test_default_status_pending(self):
        """RouterResult should default to pending status."""
        analysis = AnalysisResult(task_id="test", original_task="test")
        result = RouterResult(
            task_id="test",
            original_task="test",
            analysis=analysis
        )
        assert result.status == "pending"


class TestGenerateTaskId:
    """Tests for task ID generation."""

    def test_generates_8_char_id(self):
        """generate_task_id should return 8 character string."""
        task_id = generate_task_id()
        assert len(task_id) == 8

    def test_generates_unique_ids(self):
        """generate_task_id should return unique IDs."""
        ids = [generate_task_id() for _ in range(100)]
        assert len(set(ids)) == 100
