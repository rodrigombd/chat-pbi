from __future__ import annotations
import logging
from neo4j import Driver
import config
from config import LabelConfig
from src.db import get_driver

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def create_vector_index(driver: Driver, label_cfg: LabelConfig) -> None:
    index_name = config.SCHEMA.index_name(label_cfg.label)
    embedding_prop = config.SCHEMA.embedding_property
    query = f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (n:{label_cfg.label}) ON (n.{embedding_prop})
        OPTIONS {{ indexConfig: {{
            `vector.dimensions`: {config.EMBEDDING_DIMENSIONS},
            `vector.similarity_function`: 'cosine'
        }} }}
    """
    with driver.session() as session:
        session.run(query)


def main() -> None:
    driver = get_driver()
    try:
        for label_cfg in config.SCHEMA.labels:
            create_vector_index(driver, label_cfg)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
