from __future__ import annotations

from typing import Any

from langchain_neo4j import Neo4jGraph
from langchain_openai import OpenAIEmbeddings

from config import get_settings


SEARCHABLE_TEXT_QUERY = """
MATCH (n)
WHERE n:Tabla OR n:Campo OR n:Valor OR n:Medida OR n:Regla
WITH n,
  CASE
    WHEN n:Tabla  THEN n.nombre + ". " + coalesce(n.descripcion, "") + " " + coalesce(n.grano, "")
    WHEN n:Campo  THEN n.nombre + ". " + coalesce(n.descripcion, "") + " familia: " + coalesce(n.familia, "")
    WHEN n:Valor  THEN n.valor  + " (valor de " + coalesce(n.campo, "") + ")"
    WHEN n:Medida THEN n.nombre + ". " + coalesce(n.descripcion, "") + " " + coalesce(n.formula, "")
    WHEN n:Regla  THEN n.titulo + ". " + coalesce(n.texto, "")
  END AS texto
RETURN elementId(n) AS eid, texto
"""

WRITE_EMBEDDING_QUERY = """
UNWIND $rows AS row
MATCH (n) WHERE elementId(n) = row.eid
CALL db.create.setNodeVectorProperty(n, 'embedding', row.embedding)
"""


def _vector_dimension(model: str) -> int:
    return {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}.get(model, 1536)


def build_embeddings() -> None:
    settings = get_settings()
    graph = Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)

    nodes: list[dict[str, Any]] = graph.query(SEARCHABLE_TEXT_QUERY)
    if not nodes:
        raise RuntimeError("No hay nodos conceptuales. Ejecuta 01_build_graph.cypher primero.")

    vectors = embeddings.embed_documents([n["texto"] for n in nodes])
    rows = [{"eid": n["eid"], "embedding": v} for n, v in zip(nodes, vectors)]
    graph.query(WRITE_EMBEDDING_QUERY, {"rows": rows})

    graph.query(
        f"""
        CREATE VECTOR INDEX {settings.vector_index} IF NOT EXISTS
        FOR (n:__Concept__) ON (n.embedding)
        OPTIONS {{ indexConfig: {{
          `vector.dimensions`: {_vector_dimension(settings.embedding_model)},
          `vector.similarity_function`: 'cosine'
        }} }}
        """
    )
    graph.query(
        """
        MATCH (n) WHERE (n:Tabla OR n:Campo OR n:Valor OR n:Medida OR n:Regla)
          AND n.embedding IS NOT NULL
        SET n:__Concept__
        """
    )
    print(f"Embeddings generados para {len(rows)} nodos. Índice '{settings.vector_index}' listo.")


if __name__ == "__main__":
    build_embeddings()
