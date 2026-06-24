from __future__ import annotations

from typing import Any

from retriever import Subgraph


_LABEL_ORDER = ["Regla", "Medida", "Tabla", "Campo", "Valor"]

_REL_PHRASING = {
    "SE_CALCULA_CON": "se calcula con el campo",
    "DERIVA_DE": "deriva de la medida",
    "APLICA_A": "aplica a",
    "PERTENECE_A": "pertenece a la tabla",
    "VERSION_CORREGIDA_DE": "es la versión corregida de",
    "GEOLOCALIZA_CON": "se geolocaliza únicamente con",
    "TIENE_VALOR": "admite el valor",
    "SE_UNE_POR": "se une con la tabla por",
}


def _primary_label(labels: list[str]) -> str:
    for label in _LABEL_ORDER:
        if label in labels:
            return label
    return labels[0] if labels else "Nodo"


def _node_name(node: dict[str, Any]) -> str:
    props = node["props"]
    return props.get("nombre") or props.get("titulo") or props.get("valor") or node["eid"]


def _render_node(node: dict[str, Any]) -> str:
    props = node["props"]
    label = _primary_label(node["labels"])
    name = _node_name(node)
    if label == "Regla":
        return f"- [REGLA] {props.get('titulo', name)}: {props.get('texto', '')}"
    if label == "Medida":
        line = f"- [MEDIDA] {name}: {props.get('descripcion', '')}"
        if props.get("formula"):
            line += f" Fórmula: {props['formula']}."
        return line
    if label == "Tabla":
        line = f"- [TABLA] {name}: {props.get('descripcion', '')}"
        if props.get("grano"):
            line += f" GRANO: {props['grano']}"
        return line
    if label == "Campo":
        flags = []
        if props.get("corregido"):
            flags.append("versión corregida")
        if props.get("pii"):
            flags.append("PII")
        if props.get("clave_union"):
            flags.append("clave de unión")
        suffix = f" ({', '.join(flags)})" if flags else ""
        return f"- [CAMPO] `{name}`{suffix}: {props.get('descripcion', '')}"
    if label == "Valor":
        return f"- [VALOR] `{props.get('campo', '')}` = \"{props.get('valor', name)}\""
    return f"- {name}"


def serialize(subgraph: Subgraph) -> str:
    if subgraph.is_empty():
        return ""

    by_id = {n["eid"]: n for n in subgraph.nodes}
    grouped: dict[str, list[dict[str, Any]]] = {label: [] for label in _LABEL_ORDER}
    for node in subgraph.nodes:
        grouped.setdefault(_primary_label(node["labels"]), []).append(node)

    blocks: list[str] = []
    for label in _LABEL_ORDER:
        items = grouped.get(label) or []
        if not items:
            continue
        rendered = sorted(_render_node(n) for n in items)
        blocks.append("\n".join(rendered))

    rel_lines: list[str] = []
    for rel in subgraph.relationships:
        start, end = by_id.get(rel["start"]), by_id.get(rel["end"])
        if not start or not end:
            continue
        phrasing = _REL_PHRASING.get(rel["type"], rel["type"])
        rel_lines.append(f"- `{_node_name(start)}` {phrasing} `{_node_name(end)}`.")

    sections = ["## Contexto semántico relevante (fuente de la verdad)"]
    sections.extend(blocks)
    if rel_lines:
        sections.append("### Relaciones entre conceptos")
        sections.append("\n".join(sorted(set(rel_lines))))
    return "\n\n".join(sections)
