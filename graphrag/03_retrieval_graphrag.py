from __future__ import annotations
import argparse
import logging
import neo4j
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.types import RetrieverResultItem
import config
from src.db import get_driver
from src.graph_parser import build_retrieval_query, serialize_subgraph

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def _format_record(record: neo4j.Record) -> RetrieverResultItem:
    return RetrieverResultItem(
        content=str(record.get("entry")),
        metadata={
            "entry": record.get("entry"),
            "properties": record.get("properties"),
            "score": record.get("score"),
            "context": record.get("context") or [],
        },
    )


def build_retriever(driver: neo4j.Driver, label: str) -> VectorCypherRetriever:
    label_cfg = config.SCHEMA.get_label(label)
    retrieval_query = build_retrieval_query(label_cfg, config.SCHEMA)
    embedder = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
    return VectorCypherRetriever(
        driver=driver,
        index_name=config.SCHEMA.index_name(label),
        embedder=embedder,
        retrieval_query=retrieval_query,
        result_formatter=_format_record,
    )

def retrieve_context(question: str, label: str = "Medida") -> str:
    driver = get_driver()
    try:
        retriever = build_retriever(driver, label)
        result = retriever.search(query_text=question, top_k=config.SCHEMA.top_k)
        records = [item.metadata for item in result.items]
        return serialize_subgraph(records)
    finally:
        driver.close()


def retrieve_context_all(question: str) -> str:
    driver = get_driver()
    try:
        all_records: list[dict] = []
        for label_cfg in config.SCHEMA.labels:
            retriever = build_retriever(driver, label_cfg.label)
            result = retriever.search(query_text=question, top_k=config.SCHEMA.top_k)
            all_records.extend(item.metadata for item in result.items)

        all_records.sort(key=lambda r: r.get("score", 0.0), reverse=True)
        all_records = all_records[: config.SCHEMA.top_k]
        return serialize_subgraph(all_records)
    finally:
        driver.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="GraphRAG retrieval PoC")
    parser.add_argument("question", help="Pregunta del usuario en lenguaje natural")
    parser.add_argument(
        "--label",
        default=None,
        help="Restringe la búsqueda a un label (Tabla/Medida/Columna). Por defecto busca en todos.",
    )
    args = parser.parse_args()

    logger.info("Pregunta: %s", args.question)
    if args.label is None:
        context = retrieve_context_all(args.question)
    else:
        context = retrieve_context(args.question, label=args.label)
    print("\n" + "=" * 72)
    print(context)
    print("=" * 72)


if __name__ == "__main__":
    main()