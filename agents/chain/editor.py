"""
EditorAgent - Improves and refines text.

Second step in the chain pipeline. Takes draft text and improves
style, clarity, and correctness using Claude API.
"""

from storage.base import StorageBase
from .base import ChainStepAgent


class EditorAgent(ChainStepAgent):
    """
    Improves text using Claude API.

    System prompt instructs Claude to act as a professional editor
    and improve the received text.
    """

    step_name = "editor"

    def __init__(
        self,
        storage: StorageBase,
        model: str = "claude-sonnet-4-5"
    ):
        super().__init__(
            agent_id="chain-editor",
            storage=storage,
            system_prompt="""Sei un editor professionista.
Quando ricevi un testo, miglioralo:
- Correggi errori grammaticali e ortografici
- Migliora lo stile e la fluidità
- Rendi il testo più chiaro e conciso
- Mantieni il significato originale
Restituisci solo il testo migliorato, senza commenti aggiuntivi.""",
            model=model
        )

    async def transform(self, text: str) -> str:
        """
        Improve and edit the given text.

        Args:
            text: Draft text to improve

        Returns:
            Edited and improved text
        """
        return await self._call_llm(text)
