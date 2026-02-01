"""Unit tests for AnalyzerAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from agents.router.analyzer import AnalyzerAgent, AVAILABLE_CAPABILITIES
from storage.memory import MemoryStorage


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def analyzer(storage):
    return AnalyzerAgent(storage=storage)


class TestAnalyzerAgent:
    """Tests for AnalyzerAgent."""

    def test_init(self, analyzer):
        """AnalyzerAgent should initialize correctly."""
        assert analyzer.id == "router-analyzer"
        assert "capability" in analyzer.system_prompt.lower()

    def test_available_capabilities(self, analyzer):
        """AnalyzerAgent should list available capabilities."""
        caps = analyzer.get_available_capabilities()
        assert len(caps) > 0
        assert any(c[0] == "calculation" for c in caps)
        assert any(c[0] == "creative_writing" for c in caps)

    @pytest.mark.asyncio
    async def test_analyze_calculation_task(self, analyzer):
        """AnalyzerAgent should detect calculation capability."""
        mock_response = {
            "response": '{"capabilities": ["calculation"], "subtasks": {"calculation": "calculate 5 + 3"}}'
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("calcola 5 + 3", "test-123")

            assert "calculation" in result.detected_capabilities
            assert result.task_id == "test-123"
            assert result.original_task == "calcola 5 + 3"

    @pytest.mark.asyncio
    async def test_analyze_multiple_capabilities(self, analyzer):
        """AnalyzerAgent should detect multiple capabilities."""
        mock_response = {
            "response": '''{
                "capabilities": ["calculation", "creative_writing"],
                "subtasks": {
                    "calculation": "calculate 15 * 3",
                    "creative_writing": "write a haiku about the result"
                }
            }'''
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze(
                "calcola 15 * 3 e scrivi un haiku sul risultato",
                "test-456"
            )

            assert len(result.detected_capabilities) == 2
            assert "calculation" in result.detected_capabilities
            assert "creative_writing" in result.detected_capabilities
            assert "calculation" in result.subtasks
            assert "creative_writing" in result.subtasks

    @pytest.mark.asyncio
    async def test_analyze_with_markdown_code_block(self, analyzer):
        """AnalyzerAgent should handle markdown code blocks in response."""
        mock_response = {
            "response": '''```json
{"capabilities": ["echo"], "subtasks": {"echo": "repeat the message"}}
```'''
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("ripeti ciao", "test-789")

            assert "echo" in result.detected_capabilities

    @pytest.mark.asyncio
    async def test_analyze_invalid_json(self, analyzer):
        """AnalyzerAgent should handle invalid JSON gracefully."""
        mock_response = {
            "response": "This is not valid JSON"
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("test task", "test-err")

            # Should return empty result, not raise exception
            assert result.detected_capabilities == []
            assert result.task_id == "test-err"

    @pytest.mark.asyncio
    async def test_analyze_records_duration(self, analyzer):
        """AnalyzerAgent should record analysis duration."""
        mock_response = {
            "response": '{"capabilities": ["echo"], "subtasks": {}}'
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("test", "test-dur")

            assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_analyze_text_editing(self, analyzer):
        """AnalyzerAgent should detect text_editing capability."""
        mock_response = {
            "response": '{"capabilities": ["text_editing"], "subtasks": {"text_editing": "correct grammar"}}'
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("correggi questo testo", "test-edit")

            assert "text_editing" in result.detected_capabilities

    @pytest.mark.asyncio
    async def test_analyze_formatting(self, analyzer):
        """AnalyzerAgent should detect formatting capability."""
        mock_response = {
            "response": '{"capabilities": ["formatting"], "subtasks": {"formatting": "format as markdown"}}'
        }

        with patch.object(analyzer, 'think', new_callable=AsyncMock) as mock_think:
            mock_think.return_value = mock_response

            result = await analyzer.analyze("formatta come markdown", "test-fmt")

            assert "formatting" in result.detected_capabilities


class TestAvailableCapabilities:
    """Tests for capability definitions."""

    def test_capabilities_defined(self):
        """AVAILABLE_CAPABILITIES should be defined."""
        assert len(AVAILABLE_CAPABILITIES) > 0

    def test_capabilities_have_descriptions(self):
        """Each capability should have a description."""
        for cap, desc in AVAILABLE_CAPABILITIES:
            assert len(cap) > 0
            assert len(desc) > 0

    def test_required_capabilities_exist(self):
        """Required capabilities should be defined."""
        cap_names = [c[0] for c in AVAILABLE_CAPABILITIES]
        assert "calculation" in cap_names
        assert "echo" in cap_names
        assert "creative_writing" in cap_names
