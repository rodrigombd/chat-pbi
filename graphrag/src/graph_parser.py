from __future__ import annotations
from typing import Any
from config import LabelConfig, SchemaConfig

_DIRECTION_LABEL: dict[str, str] = {
    "out": "-->",
    "in": "<--",
    "both": "<->",
}


def _direction_pattern(rel_type: str, direction: str, hops: int, alias: str) -> str:
    depth = "" if hops <= 1 else f"*1..{hops}"
    body = f"[:{rel_type}{depth}]"
    if direction == "out":
        return f"-{body}->({alias})"
    if direction == "in":
        return f"<-{body}-({alias})"
    return f"-{body}-({alias})"


def _props_reducer(alias: str, emb_prop: str, name_prop: str) -> str:
    return (
        f"reduce(acc = '', k IN [x IN keys({alias}) "
        f"WHERE x <> '{emb_prop}' AND x <> '{name_prop}'] | "
        f"acc + k + ': ' + toString({alias}[k]) + ' | ')"
    )


def build_retrieval_query(label_cfg: LabelConfig, schema: SchemaConfig) -> str:
    name_prop = label_cfg.name_property
    emb_prop = schema.embedding_property
    exp_threshold = schema.expansion_score_threshold
    optional_matches: list[str] = []
    collect_clauses: list[str] = []

    for idx, rel in enumerate(label_cfg.expansion_relationships):
        rel_type, direction, hops = rel
        alias = f"n{idx}"
        arrow = _DIRECTION_LABEL.get(direction, "--")
        pattern = _direction_pattern(rel_type, direction, hops, alias)
        optional_matches.append(
            f"OPTIONAL MATCH (node){pattern}\n"
            f"WHERE {alias}.{emb_prop} IS NULL\n"
            f"   OR vector.similarity.cosine({alias}.{emb_prop}, $query_vector) >= {exp_threshold}"
        )
        props_cypher = _props_reducer(alias, emb_prop, name_prop)
        rel_score = (
            f"CASE WHEN {alias}.{emb_prop} IS NULL THEN -1.0 "
            f"ELSE vector.similarity.cosine({alias}.{emb_prop}, $query_vector) END"
        )
        collect_clauses.append(
            f"collect(DISTINCT CASE WHEN {alias} IS NOT NULL "
            f"THEN coalesce(node.{name_prop}, node.valor, elementId(node)) + "
            f"' {arrow} {rel_type}: ' + "
            f"coalesce({alias}.{name_prop}, {alias}.nombre, {alias}.valor, elementId({alias})) + "
            f"' [score=' + toString(round({rel_score}, 3)) + ']' + "
            f"' (' + {props_cypher} + ')' "
            f"END) AS ctx{idx}"
        )

    matches_block = "\n".join(optional_matches) if optional_matches else ""
    collect_block = ",\n     ".join(collect_clauses) if collect_clauses else "[] AS ctx_empty"
    ctx_vars = " + ".join(f"ctx{idx}" for idx in range(len(label_cfg.expansion_relationships)))
    ctx_expr = ctx_vars if ctx_vars else "[]"
    node_props = _props_reducer("node", emb_prop, name_prop)

    return f"""
WITH node, score
WHERE score >= {schema.score_threshold}
{matches_block}
WITH node, score,
     {collect_block}
RETURN
    node.{name_prop} AS entry,
    {node_props} AS properties,
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
        properties = (record.get("properties") or "").strip().rstrip("|").strip()
        if properties:
            lines.append(f"  · propiedades: {properties}")

        context = record.get("context") or []
        if context:
            for ctx_line in context:
                lines.append(f"  - {ctx_line}")
        else:
            lines.append("  - (sin dependencias directas)")
    return "\n".join(lines)
