"""
WriterAgent - Generates initial text content.

First step in the chain pipeline. Takes a topic/prompt and generates
initial draft text using Claude API.
"""

from storage.base import StorageBase
from .base import ChainStepAgent


class WriterAgent(ChainStepAgent):
    """
    Generates initial text using Claude API.

    System prompt instructs Claude to act as a professional writer
    and generate 2-3 paragraphs on the given topic.
    """

    step_name = "writer"

    def __init__(
        self,
        storage: StorageBase,
        model: str = "claude-sonnet-4-20250514"
    ):
        super().__init__(
            agent_id="chain-writer",
            storage=storage,
            system_prompt="""Sei uno scrittore professionista.
Quando ricevi un topic, genera un testo iniziale di 2-3 paragrafi.
Sii creativo ma informativo. Scrivi in modo chiaro e coinvolgente.
Non aggiungere meta-commenti, scrivi solo il contenuto.""",
            model=model
        )

    async def transform(self, text: str) -> str:
        """
        Generate initial text from the given prompt/topic.

        Args:
            text: Topic or prompt to write about

        Returns:
            Generated text (2-3 paragraphs)
        """
        return await self._call_llm(text)
