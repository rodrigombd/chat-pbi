from __future__ import annotations
from typing import Any
from config import LabelConfig, SchemaConfig


def _direction_pattern(rel_type: str, direction: str, hops: int) -> str:
    depth = "" if hops <= 1 else f"*1..{hops}"
    body = f"[:{rel_type}{depth}]"
    if direction == "out":
        return f"-{body}->"
    if direction == "in":
        return f"<-{body}-"
    return f"-{body}-"


def build_retrieval_query(label_cfg: LabelConfig, schema: SchemaConfig) -> str:
    name_prop = label_cfg.name_property
    emb_prop = schema.embedding_property
    optional_matches: list[str] = []
    collect_clauses: list[str] = []

    for idx, rel in enumerate(label_cfg.expansion_relationships):
        rel_type, direction, hops = rel
        alias = f"n{idx}"
        pattern = _direction_pattern(rel_type, direction, hops)
        optional_matches.append(f"OPTIONAL MATCH (node){pattern}({alias})")
        props_cypher = (
            f"reduce(acc = '', k IN [x IN keys({alias}) "
            f"WHERE x <> '{emb_prop}' AND x <> '{name_prop}'] | "
            f"acc + k + ': ' + toString({alias}[k]) + ' | ')"
        )
        collect_clauses.append(
            f"collect(DISTINCT CASE WHEN {alias} IS NOT NULL "
            f"THEN '{rel_type}: ' + coalesce({alias}.{name_prop}, elementId({alias})) + "
            f"' (' + {props_cypher} + ')' "
            f"END) AS ctx{idx}"
        )

    matches_block = "\n".join(optional_matches) if optional_matches else ""
    collect_block = ",\n     ".join(collect_clauses) if collect_clauses else "[] AS ctx_empty"
    ctx_vars = " + ".join(f"ctx{idx}" for idx in range(len(label_cfg.expansion_relationships)))
    ctx_expr = ctx_vars if ctx_vars else "[]"

    return f"""
WITH node, score
WHERE score >= {schema.score_threshold}
{matches_block}
WITH node, score,
     {collect_block}
RETURN
    node.{name_prop} AS entry,
    score AS score,
    [x IN ({ctx_expr}) WHERE x IS NOT NULL] AS context
ORDER BY score DESC
"""


def serialize_subgraph(records: list[dict[str, Any]]) -> str:
    if not records:
        return "### CONTEXTO DEL MODELO ###\n(No se encontraron nodos relevantes.)"

    lines: list[str] = ["### CONTEXTO DEL MODELO (subgrafo relevante) ###"]
    for record in records:
        entry = record.get("entry", "?")
        score = record.get("score", 0.0)
        lines.append(f"\n## {entry}  (similitud={score:.3f})")
        context = record.get("context") or []
        if context:
            for ctx_line in context:
                lines.append(f"  - {ctx_line}")
        else:
            lines.append("  - (sin dependencias directas)")
    return "\n".join(lines)
