from __future__ import annotations
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()

def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno '{key}'. "
        )
    return value


NEO4J_URI: str = _require_env("NEO4J_URI")
NEO4J_USERNAME: str = _require_env("NEO4J_USERNAME")
NEO4J_PASSWORD: str = _require_env("NEO4J_PASSWORD")
OPENAI_API_KEY: str = _require_env("OPENAI_API_KEY")
EMBEDDING_MODEL: str = "text-embedding-3-small"
EMBEDDING_DIMENSIONS: int = 1536

@dataclass(frozen=True)
class LabelConfig:
    label: str
    name_property: str
    text_properties: tuple[str, ...]
    expansion_relationships: tuple[tuple[str, str, int], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SchemaConfig:
    embedding_property: str = "embedding"
    index_prefix: str = "entity_embeddings"
    top_k: int = 15
    score_threshold: float = 0.6
    expansion_score_threshold: float = 0.45
    # Si True, los nodos SIN embedding pasan la expansión sin filtrar por umbral
    # (útil para nodos Valor que no se embeben a propósito). Si False, un nodo
    # sin embedding NO entra por relación salvo que su similitud supere el umbral,
    # lo que es imposible sin embedding -> queda fuera. Ponlo a False para que el
    # umbral de expansión se aplique de verdad a todos los nodos embebibles.
    include_unembedded_expansion: bool = True

    labels: tuple[LabelConfig, ...] = (
        LabelConfig(
            label="Tabla",
            name_property="nombre",
            text_properties=("nombre", "descripcion", "rol"),
            expansion_relationships=(
                ("TIENE_COLUMNA", "out", 1),
                ("TIENE_MEDIDA", "out", 1),
            ),
        ),
        LabelConfig(
            label="Medida",
            name_property="nombre",
            text_properties=("nombre", "descripcion", "familia", "tipo"),
            expansion_relationships=(
                ("DERIVA_DE", "out", 1),
                ("USA_COLUMNA", "out", 1),
            ),
        ),
        LabelConfig(
            label="Columna",
            name_property="nombre",
            text_properties=("nombre", "descripcion"),
            expansion_relationships=(
                ("TIENE_VALOR", "out", 1),
                ("RELACIONA", "both", 1),
            ),
        ),
        LabelConfig(
            label="Valor",
            name_property="valor",
            text_properties=("columna", "tabla"),
            expansion_relationships=(),
        ),
    )

    def index_name(self, label: str) -> str:
        return f"{self.index_prefix}_{label.lower()}"

    def get_label(self, label: str) -> LabelConfig:
        for cfg in self.labels:
            if cfg.label == label:
                return cfg
        raise KeyError(f"Etiqueta '{label}' no está configurada en SchemaConfig.")


SCHEMA = SchemaConfig()
