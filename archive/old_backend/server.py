from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from agent import ResaAgent
from retriever import SemanticRetriever
from serializer import serialize

app = FastAPI(title="RESA Semantic Backend")

_agent: ResaAgent | None = None
_retriever: SemanticRetriever | None = None


def _get_agent() -> ResaAgent:
    global _agent
    if _agent is None:
        _agent = ResaAgent()
    return _agent


def _get_retriever() -> SemanticRetriever:
    global _retriever
    if _retriever is None:
        _retriever = SemanticRetriever()
    return _retriever


class AskRequest(BaseModel):
    question: str
    top_k: int = 6
    depth: int | None = None


class ContextRequest(BaseModel):
    question: str
    top_k: int = 6
    depth: int | None = None


@app.post("/context")
def context(req: ContextRequest) -> dict:
    subgraph = _get_retriever().retrieve(req.question, top_k=req.top_k, depth=req.depth)
    return {"context": serialize(subgraph), "node_count": len(subgraph.nodes)}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    result = _get_agent().run(req.question, top_k=req.top_k, depth=req.depth)
    return {
        "intent": result.intent.value,
        "semantic_context": result.semantic_context,
        "answer": result.answer,
    }
