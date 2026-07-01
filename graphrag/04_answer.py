from __future__ import annotations
import argparse
import logging
from openai import OpenAI, OpenAIError
import config
from importlib import import_module
_retrieval = import_module("03_retrieval_graphrag")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
_client = OpenAI(api_key=config.OPENAI_API_KEY)

ANSWER_MODEL: str = "gpt-4o-mini"

SYSTEM_PROMPT: str = (
    "Eres un asistente analítico para empleados de RESA (residencias de "
    "estudiantes). Respondes preguntas sobre el modelo de datos y sus métricas.\n"
    "\n"
    "Usa EXCLUSIVAMENTE el contexto del modelo que se te proporciona (el "
    "subgrafo relevante). Si el contexto no contiene la información necesaria, "
    "dilo claramente en lugar de inventar medidas o columnas.\n"
    "\n"
    "Cuando menciones una medida, usa su nombre exacto tal y como aparece en el "
    "contexto. Si una medida deriva de otras, explícalo. Sé conciso y concreto."
)


def build_prompt(question: str, subgraph_text: str) -> list[dict[str, str]]:
    user_content = (
        f"{subgraph_text}\n\n"
        f"### PREGUNTA DEL USUARIO ###\n{question}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

def answer_question(question: str, label: str | None = None) -> str:
    if label is None:
        subgraph_text = _retrieval.retrieve_context_all(question)
    else:
        subgraph_text = _retrieval.retrieve_context(question, label=label)
    logger.info("Subgrafo recuperado.")

    messages = build_prompt(question, subgraph_text)

    try:
        response = _client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except OpenAIError:
        logger.exception("Fallo en la llamada al LLM para generar la respuesta.")
        raise

def answer_question(question: str, label: str | None = None, context: str | None = None) -> str:
    if context is None:
        if label is None:
            subgraph_text = _retrieval.retrieve_context_all(question)
        else:
            subgraph_text = _retrieval.retrieve_context(question, label=label)
        logger.info("Subgrafo recuperado.")
    else:
        subgraph_text = context
        logger.info("Usando subgrafo proporcionado previamente.")

    messages = build_prompt(question, subgraph_text)

    try:
        response = _client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except OpenAIError:
        logger.exception("Fallo en la llamada al LLM para generar la respuesta.")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphRAG end-to-end: pregunta -> respuesta")
    parser.add_argument("question", help="Pregunta del usuario en lenguaje natural")
    parser.add_argument(
        "--label",
        default=None,
        help="Restringe la búsqueda a un label (Tabla/Medida/Columna). Por defecto busca en todos.",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Imprime también el subgrafo inyectado (para depurar)",
    )
    args = parser.parse_args()

    if args.show_context:
        if args.label is None:
            context = _retrieval.retrieve_context_all(args.question)
        else:
            context = _retrieval.retrieve_context(args.question, label=args.label)
        print("\n" + "=" * 72)
        print("SUBGRAFO INYECTADO")
        print("=" * 72)
        print(context)
        answer = answer_question(args.question, label=args.label, context=context)
    else:
        answer = answer_question(args.question, label=args.label)
    
    print("\n" + "=" * 72)
    print("RESPUESTA")
    print("=" * 72)
    print(answer)
    print("=" * 72)


if __name__ == "__main__":
    main()
