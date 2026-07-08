from __future__ import annotations
import logging
from neo4j import Driver
import config
from config import LabelConfig
from src.db import get_driver
from src.embeddings import embed_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def build_node_text(node: dict[str, str | None], label_cfg: LabelConfig) -> str:
    parts = [str(node.get(prop, "") or "") for prop in label_cfg.text_properties]
    return ". ".join(p for p in parts if p).strip()


def fetch_nodes_without_embedding(driver: Driver, label_cfg: LabelConfig) -> list[dict]:
    props = ", ".join(f"n.{p} AS {p}" for p in label_cfg.text_properties)
    query = f"""
        MATCH (n:{label_cfg.label})
        WHERE n.{config.SCHEMA.embedding_property} IS NULL
        RETURN elementId(n) AS id, {props}
    """
    with driver.session() as session:
        return [dict(record) for record in session.run(query)]


def store_embedding(driver: Driver, node_id: str, vector: list[float]) -> None:
    query = """
        MATCH (n) WHERE elementId(n) = $id
        CALL db.create.setNodeVectorProperty(n, $prop, $vector)
    """
    with driver.session() as session:
        session.run(
            query,
            id=node_id,
            prop=config.SCHEMA.embedding_property,
            vector=vector,
        )


def main() -> None:
    driver = get_driver()
    total = 0
    try:
        for label_cfg in config.SCHEMA.labels:
            nodes = fetch_nodes_without_embedding(driver, label_cfg)
            logger.info("Etiqueta :%s -> %d nodos pendientes.", label_cfg.label, len(nodes))
            for node in nodes:
                text = build_node_text(node, label_cfg)
                vector = embed_text(text)
                store_embedding(driver, node["id"], vector)
                total += 1
                logger.info("  embebido: %s", node.get(label_cfg.name_property))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
