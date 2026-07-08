from __future__ import annotations
import logging
from openai import OpenAI, OpenAIError
import config
logger = logging.getLogger(__name__)
_client = OpenAI(api_key=config.OPENAI_API_KEY)

def embed_text(text: str) -> list[float]:

    cleaned = text.strip()
    if not cleaned:
        logger.warning("Texto vacío recibido en embed_text.")
        return [0.0] * config.EMBEDDING_DIMENSIONS
    try:
        response = _client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=cleaned,
        )
        return response.data[0].embedding
    except OpenAIError:
        logger.exception("Fallo al generar el embedding para: %r...", cleaned[:60])
        raise
