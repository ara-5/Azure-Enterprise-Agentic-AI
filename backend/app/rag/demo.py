"""Zero-Azure-cost stand-in for the RAG pipeline (app/rag/pipeline.py).

Retrieval here is a pure-Python TF-IDF cosine similarity over the bundled
sample docs (backend/app/data/sample_docs) instead of Azure AI Search +
embeddings, and "generation" is an extractive template instead of an Azure
OpenAI completion. No network calls, no dependencies beyond the standard
library, no API keys required.

This exists purely so the project is runnable end-to-end (`docker compose
up`, ask a question, get a grounded answer with citations) by anyone who
clones the repo, without them needing an Azure subscription -- see
DEMO_MODE in app/config.py. The retrieval/generation quality is intentionally
modest; app/rag/pipeline.py is the real implementation this is standing in for.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.ingestion.chunking import chunk_text
from app.rag.pipeline import RagAnswer

SAMPLE_DOCS_DIR = Path(__file__).resolve().parents[1] / "data" / "sample_docs"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "of", "to", "in", "on", "for",
    "and", "or", "but", "with", "as", "at", "by", "from", "that", "this", "it", "its", "what", "which",
    "who", "how", "do", "does", "did", "can", "could", "should", "would", "will", "must", "not", "no",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class _IndexedChunk:
    id: str
    content: str
    source: str
    term_freqs: Counter


@lru_cache
def _load_corpus() -> tuple[list[_IndexedChunk], dict[str, float]]:
    chunks: list[_IndexedChunk] = []
    for path in sorted(SAMPLE_DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(text, chunk_size_tokens=200, overlap_tokens=0)):
            chunks.append(_IndexedChunk(id=f"{path.stem}-{i}", content=chunk, source=path.name, term_freqs=Counter(_tokenize(chunk))))

    doc_count = len(chunks) or 1
    doc_freq: Counter = Counter()
    for c in chunks:
        doc_freq.update(c.term_freqs.keys())

    idf = {term: math.log(1 + doc_count / df) for term, df in doc_freq.items()}
    return chunks, idf


def _cosine_score(query_terms: Counter, chunk: _IndexedChunk, idf: dict[str, float]) -> float:
    dot = sum(query_terms[t] * chunk.term_freqs[t] * idf.get(t, 0.0) ** 2 for t in query_terms if t in chunk.term_freqs)
    if dot == 0:
        return 0.0
    query_norm = math.sqrt(sum((c * idf.get(t, 0.0)) ** 2 for t, c in query_terms.items()))
    chunk_norm = math.sqrt(sum((c * idf.get(t, 0.0)) ** 2 for t, c in chunk.term_freqs.items()))
    if query_norm == 0 or chunk_norm == 0:
        return 0.0
    return dot / (query_norm * chunk_norm)


def _extractive_summary(question_terms: set[str], content: str, max_sentences: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", content.strip())
    scored = sorted(sentences, key=lambda s: len(question_terms & set(_tokenize(s))), reverse=True)
    best = [s for s in scored[:max_sentences] if s]
    return " ".join(best) if best else content[:300]


def search_demo(question: str, top_k: int = 5) -> list[dict]:
    chunks, idf = _load_corpus()
    query_terms = Counter(_tokenize(question))

    scored = [(c, _cosine_score(query_terms, c, idf)) for c in chunks]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [
        {"id": c.id, "content": c.content, "source": c.source, "document_id": c.source, "score": round(score, 4)}
        for c, score in scored[:top_k]
    ]


def answer_question_demo(question: str, *, top_k: int = 5) -> RagAnswer:
    """Same return shape as app.rag.pipeline.answer_question, so the API
    routes and frontend don't need to know which mode produced the answer."""
    hits = search_demo(question, top_k=top_k)

    if not hits:
        return RagAnswer(
            answer=(
                "[Demo mode - local keyword retrieval, no Azure OpenAI configured] "
                "I couldn't find anything in the sample knowledge base relevant to that question. "
                "Try asking about remote work, PTO, incident response SLAs, expense approvals, or data classification."
            ),
            citations=[],
            retrieval_score=0.0,
        )

    question_terms = set(_tokenize(question))
    top_hit = hits[0]
    extract = _extractive_summary(question_terms, top_hit["content"])

    answer = (
        f"[Demo mode - local keyword retrieval, no Azure OpenAI configured]\n\n"
        f"Based on {top_hit['source']}: {extract}\n\n"
        f"(In live mode, this same retrieved context is passed to Azure OpenAI for a real grounded answer "
        f"-- see app/rag/pipeline.py. Set DEMO_MODE=false with real Azure OpenAI/AI Search credentials to try it.)"
    )

    avg_score = sum(h["score"] for h in hits) / len(hits)
    return RagAnswer(
        answer=answer,
        citations=[{"source": h["source"], "document_id": h["document_id"], "score": h["score"]} for h in hits],
        retrieval_score=round(avg_score, 4),
    )
