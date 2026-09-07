"""Document ingestion: Blob Storage -> chunk -> embed -> Azure AI Search.

Triggered either via POST /api/documents/ingest (single doc, synchronous,
good for demos) or scripts/ingest_container.py (batch, walks an entire
Blob container -- what you'd point at a real document library).
"""
import logging
from datetime import UTC, datetime

from app.ingestion.chunking import to_index_documents
from app.services import ai_search, azure_openai

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 16


async def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = azure_openai.get_client()
    response = await client.embeddings.create(model=azure_openai.embedding_deployment(), input=texts)
    return [d.embedding for d in response.data]


async def ingest_document(*, document_id: str, source: str, text: str) -> int:
    """Chunk, embed and upload one document. Returns the number of chunks indexed."""
    await ai_search.ensure_index_exists()

    docs = to_index_documents(
        document_id=document_id,
        source=source,
        text=text,
        last_updated_iso=datetime.now(UTC).isoformat(),
    )
    if not docs:
        logger.warning("Document %s produced no chunks; skipping.", document_id)
        return 0

    for i in range(0, len(docs), _EMBED_BATCH_SIZE):
        batch = docs[i : i + _EMBED_BATCH_SIZE]
        vectors = await _embed_batch([d["content"] for d in batch])
        for doc, vector in zip(batch, vectors, strict=False):
            doc["content_vector"] = vector

    await ai_search.upload_chunks(docs)
    logger.info("Indexed %d chunks for document '%s'.", len(docs), document_id)
    return len(docs)
