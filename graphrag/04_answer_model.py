from __future__ import annotations
import argparse
import logging
from openai import OpenAI, OpenAIError
import config
from pathlib import Path
from importlib import import_module
_retrieval = import_module("03_retrieval_graphrag")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
_client = OpenAI(api_key=config.OPENAI_API_KEY)
ANSWER_MODEL: str = "gpt-4o-mini"
_CONTEXT_GENERAL_PATH = Path(__file__).parent.parent / "frontend" / "context_general.txt"


def _load_system_prompt() -> str:
    return _CONTEXT_GENERAL_PATH.read_text(encoding="utf-8")


def build_prompt(question: str, subgraph_text: str, system_prompt: str) -> list[dict[str, str]]:
    user_content = (
        "### CONTEXTO DEL MODELO DE DATOS (subgrafo recuperado) ###\n"
        f"{subgraph_text}\n\n"
        "### PREGUNTA DEL USUARIO ###\n"
        f"{question}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

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

    system_prompt = _load_system_prompt()
    messages = build_prompt(question, subgraph_text, system_prompt)

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
