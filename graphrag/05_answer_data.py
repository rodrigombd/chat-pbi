from __future__ import annotations

import argparse
import logging
from pathlib import Path

from openai import OpenAI, OpenAIError

import config
from importlib import import_module

_retrieval = import_module("03_retrieval_graphrag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
_client = OpenAI(api_key=config.OPENAI_API_KEY)
ANSWER_MODEL: str = "gpt-4o"
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


def answer_data(question: str,label: str | None = None,context: str | None = None,) -> tuple[list[dict[str, str]], str]:
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
    except OpenAIError:
        logger.exception("Fallo en la llamada al LLM (agente único).")
        raise

    output = response.choices[0].message.content or ""
    return messages, output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agente único: pregunta -> system prompt + código generado (no se ejecuta)"
    )
    parser.add_argument("question", help="Pregunta del usuario en lenguaje natural")
    parser.add_argument(
        "--label",
        default=None,
        help="Restringe la búsqueda a un label (Tabla/Medida/Columna). Por defecto, todos.",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Imprime TODO lo que se manda al LLM (system prompt + user message completo).",
    )
    args = parser.parse_args()

    messages, output = answer_data(args.question, label=args.label)

    if args.show_context:
        print("\n" + "=" * 72)
        print("MENSAJES ENVIADOS AL LLM")
        print("=" * 72)
        for msg in messages:
            print("-" * 72)
            print(f"[role: {msg['role']}]")
            print("-" * 72)
            print(msg["content"])
            print()

    print("\n" + "=" * 72)
    print("CÓDIGO GENERADO (no ejecutado)")
    print("=" * 72)
    print(output)
    print("=" * 72)


if __name__ == "__main__":
    main()
