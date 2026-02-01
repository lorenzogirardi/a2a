"""
Specialist Agents - LLM-based agents with specific capabilities.

These agents extend the router's capabilities for complex tasks.
"""

from storage.base import StorageBase
from agents.llm_agent import LLMAgent
from agents.base import AgentConfig


class ResearchAgent(LLMAgent):
    """
    Agent specialized in research and knowledge questions.

    Handles questions about facts, history, science, etc.
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="researcher",
            storage=storage,
            system_prompt="""Sei un ricercatore esperto con vasta conoscenza.

Quando ricevi una domanda:
- Fornisci informazioni accurate e dettagliate
- Cita fonti o riferimenti quando possibile
- Spiega concetti complessi in modo chiaro
- Ammetti se non sei sicuro di qualcosa

Rispondi in modo informativo ma conciso.""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Research Agent",
            description="Ricerca e risponde a domande di conoscenza",
            capabilities=["research", "knowledge"]
        )


class EstimationAgent(LLMAgent):
    """
    Agent specialized in cost and quantity estimations.

    Handles questions about costs, sizes, quantities, etc.
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="estimator",
            storage=storage,
            system_prompt="""Sei un esperto in stime e valutazioni.

Quando ricevi una richiesta di stima:
- Fornisci range realistici (minimo - massimo)
- Spiega i fattori che influenzano la stima
- Usa dati e riferimenti quando disponibili
- Indica il livello di incertezza

Formato risposta:
1. Stima: [range]
2. Fattori chiave: [lista]
3. Note: [considerazioni]""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Estimation Agent",
            description="Fornisce stime di costi, quantità e dimensioni",
            capabilities=["estimation", "cost_analysis"]
        )


class AnalysisAgent(LLMAgent):
    """
    Agent specialized in analysis and reasoning.

    Handles complex questions requiring breakdown and analysis.
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="analyst",
            storage=storage,
            system_prompt="""Sei un analista esperto in problem solving.

Quando ricevi un problema complesso:
- Scomponi il problema in parti
- Analizza ogni aspetto sistematicamente
- Identifica pro e contro
- Fornisci una conclusione ragionata

Usa un approccio strutturato e logico.""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Analysis Agent",
            description="Analizza problemi complessi e fornisce ragionamenti",
            capabilities=["analysis", "reasoning"]
        )


class TranslationAgent(LLMAgent):
    """
    Agent specialized in translations.

    Handles translation requests between languages.
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="translator",
            storage=storage,
            system_prompt="""Sei un traduttore professionista multilingue.

Quando ricevi un testo da tradurre:
- Identifica la lingua di origine
- Traduci mantenendo il significato e il tono
- Preserva formattazione e struttura
- Segnala eventuali ambiguità

Fornisci solo la traduzione, senza spiegazioni aggiuntive.""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Translation Agent",
            description="Traduce testi tra diverse lingue",
            capabilities=["translation"]
        )


class SummaryAgent(LLMAgent):
    """
    Agent specialized in summarization.

    Handles requests to summarize texts or concepts.
    """

    def __init__(self, storage: StorageBase, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_id="summarizer",
            storage=storage,
            system_prompt="""Sei un esperto in sintesi e riassunti.

Quando ricevi un testo o argomento:
- Identifica i punti chiave
- Crea un riassunto conciso ma completo
- Mantieni le informazioni essenziali
- Usa bullet points quando appropriato

Sii breve ma informativo.""",
            model=model
        )
        self.config = AgentConfig(
            id=self.id,
            name="Summary Agent",
            description="Riassume testi e concetti",
            capabilities=["summarization"]
        )
