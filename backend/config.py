from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    embedding_model: str
    orchestrator_model: str
    vector_index: str
    default_depth: int

    @staticmethod
    def _require(key: str) -> str:
        value = os.environ.get(key, "").strip()
        if not value:
            raise RuntimeError(f"Falta la variable de entorno requerida: {key}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        openai_api_key=Settings._require("OPENAI_API_KEY"),
        neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
        neo4j_password=Settings._require("NEO4J_PASSWORD"),
        neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        orchestrator_model=os.environ.get("ORCHESTRATOR_MODEL", "gpt-4o"),
        vector_index=os.environ.get("NEO4J_VECTOR_INDEX", "resa_concept_embeddings"),
        default_depth=int(os.environ.get("SUBGRAPH_DEPTH", "2")),
    )
