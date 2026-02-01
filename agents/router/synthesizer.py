"""
SynthesizerAgent - Synthesizes multiple agent outputs into coherent response.

Phase 2 of Two-Phase Execution: receives all parallel execution results
and integrates them into a unified, coherent answer.
"""

import time
from datetime import datetime
from typing import Optional

from storage.base import StorageBase, Message
from agents.llm_agent import LLMAgent
from agents.base import AgentConfig
from .models import ExecutionResult


class SynthesizerAgent(LLMAgent):
    """
    Synthesizes multiple agent outputs into a coherent response.

    This agent receives the original task and all execution results
    from parallel agents, then creates a unified response that:
    - Integrates complementary information
    - Resolves contradictions
    - Provides a coherent narrative
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="synthesizer",
            storage=storage,
            system_prompt="""Sei un sintetizzatore esperto.

Ricevi il task originale e i risultati di più agenti specializzati.
Il tuo compito è:
1. Integrare le informazioni complementari
2. Risolvere eventuali contraddizioni
3. Creare una risposta coerente e completa
4. Mantenere le informazioni chiave di ogni fonte

Formato risposta:
- Sintesi principale (risposta diretta alla domanda)
- Dettagli integrati (informazioni complementari)
- Fonti utilizzate (quali agenti hanno contribuito)

Scrivi in modo chiaro e strutturato.""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Synthesizer Agent",
            description="Sintetizza output multipli in risposta coerente",
            capabilities=["synthesis", "integration"]
        )

    async def synthesize(
        self,
        original_task: str,
        executions: list[ExecutionResult],
        task_id: str
    ) -> dict:
        """
        Synthesize multiple execution results into coherent output.

        Args:
            original_task: The original user task
            executions: Results from parallel agent executions
            task_id: Task identifier

        Returns:
            dict with synthesized output and metadata
        """
        start_time = time.time()

        # Build context from all executions
        context_parts = [f"**Task originale**: {original_task}\n"]
        context_parts.append("**Risultati degli agenti:**\n")

        for exec_result in executions:
            if exec_result.success:
                context_parts.append(
                    f"\n### {exec_result.agent_name} ({exec_result.capability}):\n"
                    f"{exec_result.output_text}\n"
                )

        synthesis_prompt = "\n".join(context_parts)
        synthesis_prompt += "\n---\nSintetizza questi risultati in una risposta coerente e completa."

        # Call LLM for synthesis
        message = Message(
            id=f"synthesize-{task_id}",
            sender="router",
            receiver=self.id,
            content=synthesis_prompt,
            timestamp=datetime.now(),
            metadata={"task_id": task_id}
        )

        result = await self.think(message)
        response_text = result.get("response", "")

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "synthesized_output": response_text,
            "duration_ms": duration_ms,
            "sources": [e.agent_id for e in executions if e.success],
            "tokens": result.get("tokens", {"input": 0, "output": 0})
        }
