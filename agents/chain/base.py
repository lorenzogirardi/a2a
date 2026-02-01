"""
ChainStepAgent - Base class for chain pipeline steps.

Each step in the chain extends this class and implements transform().
"""

from abc import abstractmethod
from typing import Any, Optional
from datetime import datetime
from dataclasses import dataclass

from storage.base import StorageBase, Message
from agents.llm_agent import LLMAgent
from agents.base import AgentConfig


@dataclass
class TransformResult:
    """Result from a transform operation including metadata."""
    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class ChainStepAgent(LLMAgent):
    """
    Base class for chain pipeline step agents.

    Each step has:
    - step_name: identifier for this step in the pipeline
    - transform(): processes input text and returns output text
    - transform_with_metadata(): same but returns full metadata

    Extends LLMAgent to leverage Claude API for text transformation.
    """

    step_name: str = "base"  # Override in subclasses
    _last_result: Optional[TransformResult] = None

    def __init__(
        self,
        agent_id: str,
        storage: StorageBase,
        system_prompt: str,
        model: str = "claude-sonnet-4-5"
    ):
        super().__init__(
            agent_id=agent_id,
            storage=storage,
            system_prompt=system_prompt,
            model=model
        )
        self._last_result = None

    @abstractmethod
    async def transform(self, text: str) -> str:
        """
        Transform input text to output text.

        This is the main processing method for the step.
        Subclasses must implement this method.

        Args:
            text: Input text to transform

        Returns:
            Transformed text
        """
        pass

    async def transform_with_metadata(self, text: str) -> TransformResult:
        """
        Transform input text and return result with metadata.

        Args:
            text: Input text to transform

        Returns:
            TransformResult with text and metadata
        """
        response_text = await self.transform(text)
        return self._last_result or TransformResult(text=response_text)

    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM API with the given prompt.

        Uses the inherited LLMAgent.think() method internally.
        Stores metadata in _last_result for retrieval.

        Args:
            prompt: User prompt to send to LLM

        Returns:
            LLM's response text
        """
        message = Message(
            id=f"chain-{self.step_name}",
            sender="pipeline",
            receiver=self.id,
            content=prompt,
            timestamp=datetime.now(),
            metadata={"step": self.step_name}
        )

        result = await self.think(message)

        # Extract metadata
        response_text = result.get("response", "")
        metadata = result.get("metadata", {})
        usage = metadata.get("usage", {})

        self._last_result = TransformResult(
            text=response_text,
            model=metadata.get("model", self.model),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0)
        )

        return response_text
