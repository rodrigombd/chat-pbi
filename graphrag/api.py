from __future__ import annotations
import logging
from importlib import import_module
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import config
from src.db import get_driver
_retrieval = import_module("03_retrieval_graphrag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("graphrag-api")


app = FastAPI(
    title="RESA GraphRAG Retrieval API",
    version="1.0.0",
    description="Devuelve el subgrafo relevante del modelo de datos para una consulta.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Consulta enriquecida (texto + memoria de sesión).")
    label: Optional[str] = Field(
        None,
        description="Si se indica (Tabla/Medida/Columna) restringe la búsqueda a ese label. "
        "Por defecto busca en todos.",
    )

class RetrieveResponse(BaseModel):
    subgraph_text: str = Field(..., description="Subgrafo serializado, listo para inyectar como contexto.")
    ok: bool = True


@app.on_event("startup")
def _startup_check() -> None:
    try:
        driver = get_driver()
        driver.close()
        logger.info("Neo4j accesible. API lista.")
    except Exception:
        logger.exception(
            "No se pudo verificar la conexión con Neo4j al arrancar."
        )


@app.get("/health")
def health() -> dict:
    try:
        driver = get_driver()
        driver.close()
        return {"ok": True, "neo4j": True, "top_k": config.SCHEMA.top_k,
                "score_threshold": config.SCHEMA.score_threshold}
    except Exception as exc:
        return {"ok": False, "neo4j": False, "error": str(exc)}


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    question = (req.query or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="La consulta está vacía.")

    try:
        if req.label:
            subgraph = _retrieval.retrieve_context(question, label=req.label)
        else:
            subgraph = _retrieval.retrieve_context_all(question)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Label no válido: {exc}") from exc
    except Exception as exc:
        logger.exception("Fallo en el retrieval GraphRAG.")
        raise HTTPException(status_code=502, detail=f"Fallo en el retrieval: {exc}") from exc

    logger.info("Retrieve OK | label=%s | chars=%d | q=%r", req.label or "ALL", len(subgraph), question[:80])
    return RetrieveResponse(subgraph_text=subgraph, ok=True)
