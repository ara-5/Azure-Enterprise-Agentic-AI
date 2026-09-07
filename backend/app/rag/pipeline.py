"""Retrieval-augmented generation: embed -> hybrid search -> grounded answer.

This module is deliberately framework-free (no Semantic Kernel) so it can be
called directly by the /chat/completions route for plain RAG, and also
wrapped as a Semantic Kernel plugin (app/agents/plugins/knowledge_base.py)
for the agentic path -- one retrieval implementation, two callers.
"""
import logging
from dataclasses import dataclass

from app.core.cost_tracking import record_usage
from app.core.telemetry import tracer
from app.services import ai_search, azure_openai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an enterprise assistant answering questions strictly from the provided
context. Cite sources inline as [source]. If the context does not contain the answer, say so
plainly instead of guessing. Be concise and precise."""


@dataclass
class RagAnswer:
    answer: str
    citations: list[dict]
    retrieval_score: float


async def _embed(text: str, *, route: str, user_id: str | None) -> list[float]:
    client = azure_openai.get_client()
    with tracer.start_as_current_span("rag.embed_query"):
        response = await client.embeddings.create(model=azure_openai.embedding_deployment(), input=text)
    await record_usage(
        operation="embedding",
        model=azure_openai.embedding_deployment(),
        route=route,
        prompt_tokens=response.usage.prompt_tokens,
        user_id=user_id,
    )
    return response.data[0].embedding


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        label = c.get("source") or c.get("document_id") or c["id"]
        parts.append(f"[{label}]\n{c['content']}")
    return "\n\n---\n\n".join(parts)


async def answer_question(
    question: str,
    *,
    route: str = "/chat",
    user_id: str | None = None,
    top_k: int = 5,
    filter_expr: str | None = None,
) -> RagAnswer:
    query_vector = await _embed(question, route=route, user_id=user_id)

    with tracer.start_as_current_span("rag.hybrid_search"):
        chunks = await ai_search.hybrid_search(question, query_vector, top_k=top_k, filter_expr=filter_expr)

    if not chunks:
        return RagAnswer(
            answer="I couldn't find anything relevant in the knowledge base to answer that.",
            citations=[],
            retrieval_score=0.0,
        )

    context = _build_context(chunks)
    client = azure_openai.get_client()

    with tracer.start_as_current_span("rag.generate_answer"):
        response = await client.chat.completions.create(
            model=azure_openai.chat_deployment(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
            temperature=0.1,
        )

    await record_usage(
        operation="chat",
        model=azure_openai.chat_deployment(),
        route=route,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        user_id=user_id,
    )

    avg_reranker = sum(c.get("reranker_score") or 0 for c in chunks) / len(chunks)

    return RagAnswer(
        answer=response.choices[0].message.content or "",
        citations=[{"source": c.get("source"), "document_id": c.get("document_id"), "score": c["score"]} for c in chunks],
        retrieval_score=round(avg_reranker, 4),
    )
