"""Semantic Kernel plugin exposing the RAG retriever as a callable tool.

This is deliberately a *retrieval* tool, not an *answering* tool: the agent
calls it to fetch grounded context, then synthesizes the final answer itself
in the same turn (with function-calling enabled) -- so citations stay
attached to what was actually retrieved rather than a black-box summary.
"""
import json

from semantic_kernel.functions import kernel_function

from app.services import ai_search, azure_openai


class KnowledgeBasePlugin:
    """Search the enterprise knowledge base indexed in Azure AI Search."""

    @kernel_function(
        name="search_knowledge_base",
        description=(
            "Search the enterprise knowledge base for passages relevant to a query. "
            "Use this whenever the user asks about internal documents, policies, or "
            "company-specific facts you are not certain about."
        ),
    )
    async def search_knowledge_base(self, query: str, top_k: int = 5) -> str:
        client = azure_openai.get_client()
        embedding = await client.embeddings.create(model=azure_openai.embedding_deployment(), input=query)
        chunks = await ai_search.hybrid_search(query, embedding.data[0].embedding, top_k=top_k)

        if not chunks:
            return json.dumps({"results": [], "note": "No relevant documents found."})

        return json.dumps(
            {
                "results": [
                    {"source": c.get("source"), "content": c["content"], "score": c["score"]}
                    for c in chunks
                ]
            }
        )
