"""
PublisherAgent - Formats text for publication.

Third step in the chain pipeline. Takes edited text and formats it
for publication with title, sections, and proper structure.
"""

from storage.base import StorageBase
from .base import ChainStepAgent


class PublisherAgent(ChainStepAgent):
    """
    Formats text for publication using Claude API.

    System prompt instructs Claude to act as a publisher
    and format the text with title, sections, and conclusion.
    """

    step_name = "publisher"

    def __init__(
        self,
        storage: StorageBase,
        model: str = "claude-sonnet-4-20250514"
    ):
        super().__init__(
            agent_id="chain-publisher",
            storage=storage,
            system_prompt="""Sei un publisher professionista.
Quando ricevi un testo, formattalo per la pubblicazione:
- Aggiungi un titolo appropriato (usa # per il titolo)
- Organizza in sezioni se necessario
- Aggiungi una breve conclusione
- Usa markdown per la formattazione
Restituisci solo il testo formattato, senza meta-commenti.""",
            model=model
        )

    async def transform(self, text: str) -> str:
        """
        Format the given text for publication.

        Args:
            text: Edited text to format

        Returns:
            Formatted text ready for publication (with title, sections)
        """
        return await self._call_llm(text)
