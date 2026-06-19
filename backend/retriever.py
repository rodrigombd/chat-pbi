from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_neo4j import Neo4jGraph
from langchain_openai import OpenAIEmbeddings

from config import Settings, get_settings


SEED_QUERY = """
CALL db.index.vector.queryNodes($index, $k, $vector)
YIELD node, score
RETURN elementId(node) AS eid, score
"""

SUBGRAPH_QUERY = """
MATCH (seed) WHERE elementId(seed) IN $seedIds
CALL apoc.path.subgraphAll(seed, {
  maxLevel: $depth,
  relationshipFilter:
    "PERTENECE_A|SE_CALCULA_CON|DERIVA_DE|APLICA_A|VERSION_CORREGIDA_DE|GEOLOCALIZA_CON|TIENE_VALOR|SE_UNE_POR"
}) YIELD nodes, relationships
UNWIND nodes AS n
WITH collect(DISTINCT n) AS allNodes, relationships
UNWIND relationships AS r
WITH allNodes, collect(DISTINCT {
  start: elementId(startNode(r)), type: type(r), end: elementId(endNode(r))
}) AS rels
RETURN
  [n IN allNodes | {
    eid: elementId(n), labels: labels(n), props: properties(n)
  }] AS nodes,
  rels AS relationships
"""


@dataclass(frozen=True)
class Subgraph:
    nodes: list[dict[str, Any]]
    relationships: list[dict[str, str]]
    seed_scores: dict[str, float]

    def is_empty(self) -> bool:
        return not self.nodes


class SemanticRetriever:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._graph = Neo4jGraph(
            url=self._settings.neo4j_uri,
            username=self._settings.neo4j_user,
            password=self._settings.neo4j_password,
            database=self._settings.neo4j_database,
        )
        self._embeddings = OpenAIEmbeddings(
            model=self._settings.embedding_model,
            api_key=self._settings.openai_api_key,
        )

    def retrieve(self, question: str, *, top_k: int = 6, depth: int | None = None) -> Subgraph:
        depth = depth if depth is not None else self._settings.default_depth
        vector = self._embeddings.embed_query(question)

        seeds = self._graph.query(
            SEED_QUERY,
            {"index": self._settings.vector_index, "k": top_k, "vector": vector},
        )
        if not seeds:
            return Subgraph(nodes=[], relationships=[], seed_scores={})

        seed_ids = [s["eid"] for s in seeds]
        scores = {s["eid"]: float(s["score"]) for s in seeds}

        result = self._graph.query(SUBGRAPH_QUERY, {"seedIds": seed_ids, "depth": depth})
        if not result:
            return Subgraph(nodes=[], relationships=[], seed_scores=scores)

        payload = result[0]
        return Subgraph(
            nodes=payload["nodes"],
            relationships=payload["relationships"],
            seed_scores=scores,
        )
