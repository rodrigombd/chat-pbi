from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import get_settings
from retriever import SemanticRetriever
from serializer import serialize


class Intent(str, Enum):
    SALUDO = "saludo"
    TEORIA = "teoria"
    ANALITICA = "analitica"


_INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Clasifica la intención del usuario en una sola palabra: 'saludo' (cortesía o charla), "
     "'teoria' (pregunta sobre el modelo de datos, columnas, KPIs sin pedir un cálculo) o "
     "'analitica' (pide un cálculo, agregación, ranking, mapa o gráfico sobre los datos). "
     "Responde EXCLUSIVAMENTE con una de esas tres palabras."),
    ("human", "{question}"),
])

_ANALYTICS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Eres un analista de datos senior de RESA. Generas código Python (pandas) sobre el "
     "DataFrame `df` (tabla `leads_contacts`). Te basas ÚNICAMENTE en el contexto semántico "
     "inyectado abajo, que es la fuente de la verdad gobernada: no inventes columnas, valores "
     "ni reglas que no aparezcan en él. Respeta literalmente cada REGLA listada.\n\n"
     "{semantic_context}"),
    ("human", "{question}"),
])


@dataclass(frozen=True)
class AgentResult:
    intent: Intent
    semantic_context: str
    answer: str


class ResaAgent:
    def __init__(self) -> None:
        settings = get_settings()
        self._retriever = SemanticRetriever(settings)
        self._classifier = ChatOpenAI(
            model=settings.orchestrator_model, temperature=0, api_key=settings.openai_api_key
        )
        self._generator = ChatOpenAI(
            model=settings.orchestrator_model, temperature=0, api_key=settings.openai_api_key
        )

    def _classify(self, question: str) -> Intent:
        raw = (self._classifier.invoke(_INTENT_PROMPT.format_messages(question=question))
               .content.strip().lower())
        try:
            return Intent(raw)
        except ValueError:
            return Intent.ANALITICA

    def run(self, question: str, *, top_k: int = 6, depth: int | None = None) -> AgentResult:
        intent = self._classify(question)
        if intent == Intent.SALUDO:
            return AgentResult(intent, "", "¡Hola! Pregúntame sobre los leads, contactos o la conversión de RESA.")

        subgraph = self._retriever.retrieve(question, top_k=top_k, depth=depth)
        context = serialize(subgraph)

        if intent == Intent.TEORIA:
            messages = [
                ("system", "Explica el modelo de datos al usuario en español, breve y claro, "
                           "basándote solo en el contexto siguiente. No ejecutas código.\n\n" + context),
                ("human", question),
            ]
            answer = self._generator.invoke(messages).content
            return AgentResult(intent, context, answer)

        answer = self._generator.invoke(
            _ANALYTICS_PROMPT.format_messages(semantic_context=context, question=question)
        ).content
        return AgentResult(intent, context, answer)
