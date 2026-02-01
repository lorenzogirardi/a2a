"""
AnalyzerAgent - LLM-based task analyzer.

Analyzes user tasks and extracts required capabilities using Claude.
"""

import json
import time
from typing import Optional
from datetime import datetime

from storage.base import StorageBase, Message
from agents.llm_agent import LLMAgent
from .models import AnalysisResult


# Available capabilities in the system
AVAILABLE_CAPABILITIES = [
    ("calculation", "operazioni matematiche, calcoli, formule"),
    ("echo", "ripetizione di messaggi, eco"),
    ("creative_writing", "scrittura creativa, poesie, storie, haiku"),
    ("text_editing", "modifica, correzione e miglioramento testi"),
    ("formatting", "formattazione documenti, markdown, struttura"),
    ("research", "ricerca informazioni, domande di conoscenza, fatti"),
    ("estimation", "stime di costi, quantità, dimensioni, valutazioni"),
    ("analysis", "analisi problemi complessi, ragionamento, pro/contro"),
    ("translation", "traduzione tra lingue diverse"),
    ("summarization", "riassunti, sintesi di testi o concetti"),
]


class AnalyzerAgent(LLMAgent):
    """
    Analyzes user tasks to extract required capabilities.

    Uses Claude to understand the task and identify which
    capabilities are needed to complete it.
    """

    def __init__(
        self,
        storage: StorageBase,
        model: str = "claude-sonnet-4-5"
    ):
        # Build capability list for prompt
        cap_list = "\n".join(
            f"    - {cap}: {desc}" for cap, desc in AVAILABLE_CAPABILITIES
        )

        system_prompt = f"""Sei un analizzatore di task intelligente.

Il tuo compito è analizzare la richiesta dell'utente e identificare:
1. Quali capability sono necessarie per completare il task
2. Come suddividere il task in sotto-task per ogni capability

Capability disponibili:
{cap_list}

IMPORTANTE: Rispondi SOLO con un JSON valido nel seguente formato:
{{
    "capabilities": ["capability1", "capability2"],
    "subtasks": {{
        "capability1": "descrizione del sotto-task per questa capability",
        "capability2": "descrizione del sotto-task per questa capability"
    }}
}}

Non aggiungere spiegazioni, solo il JSON."""

        super().__init__(
            agent_id="router-analyzer",
            storage=storage,
            system_prompt=system_prompt,
            model=model
        )

    async def analyze(self, task: str, task_id: str) -> AnalysisResult:
        """
        Analyze a task and extract required capabilities.

        Args:
            task: The user's task description
            task_id: Unique identifier for this task

        Returns:
            AnalysisResult with detected capabilities and subtasks
        """
        start_time = time.time()

        try:
            # Create message for LLM
            message = Message(
                id=f"analyze-{task_id}",
                sender="router",
                receiver=self.id,
                content=task,
                timestamp=datetime.now(),
                metadata={"task_id": task_id}
            )

            # Call LLM
            result = await self.think(message)
            response_text = result.get("response", "")

            # Parse JSON response
            # Handle potential markdown code blocks
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            parsed = json.loads(json_text.strip())

            capabilities = parsed.get("capabilities", [])
            subtasks = parsed.get("subtasks", {})

            duration_ms = int((time.time() - start_time) * 1000)

            return AnalysisResult(
                task_id=task_id,
                original_task=task,
                detected_capabilities=capabilities,
                subtasks=subtasks,
                duration_ms=duration_ms
            )

        except json.JSONDecodeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            # Return empty result on parse error
            return AnalysisResult(
                task_id=task_id,
                original_task=task,
                detected_capabilities=[],
                subtasks={},
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return AnalysisResult(
                task_id=task_id,
                original_task=task,
                detected_capabilities=[],
                subtasks={},
                duration_ms=duration_ms
            )

    def get_available_capabilities(self) -> list[tuple[str, str]]:
        """Return list of available capabilities with descriptions."""
        return AVAILABLE_CAPABILITIES
