"""Naive but dependency-light text chunking.

Splits on paragraph boundaries first, then packs paragraphs into
~chunk_size-token windows with overlap, so retrieval chunks stay
semantically coherent instead of cutting mid-sentence.
"""
import re
import uuid
from datetime import UTC

_WORD_RE = re.compile(r"\S+")


def _approx_tokens(text: str) -> int:
    # ~0.75 tokens per word is a reasonable approximation for English text
    # without pulling in tiktoken as a hard dependency for the ingestion path.
    return int(len(_WORD_RE.findall(text)) / 0.75)


def chunk_text(text: str, *, chunk_size_tokens: int = 400, overlap_tokens: int = 60) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approx_tokens(para)
        if current and current_tokens + para_tokens > chunk_size_tokens:
            chunks.append("\n\n".join(current))
            # keep the tail of the previous chunk for overlap/context continuity
            overlap: list[str] = []
            overlap_count = 0
            for p in reversed(current):
                overlap.insert(0, p)
                overlap_count += _approx_tokens(p)
                if overlap_count >= overlap_tokens:
                    break
            current = overlap
            current_tokens = overlap_count
        current.append(para)
        current_tokens += para_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def to_index_documents(*, document_id: str, source: str, text: str, last_updated_iso: str) -> list[dict]:
    from datetime import datetime

    chunks = chunk_text(text)
    return [
        {
            "id": f"{document_id}-{i}-{uuid.uuid4().hex[:8]}",
            "content": chunk,
            "source": source,
            "document_id": document_id,
            "page_number": i,
            "last_updated": last_updated_iso or datetime.now(UTC).isoformat(),
        }
        for i, chunk in enumerate(chunks)
    ]
