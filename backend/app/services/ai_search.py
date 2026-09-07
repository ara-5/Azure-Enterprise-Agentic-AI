"""Azure AI Search client + index schema for the RAG knowledge base.

Uses hybrid search (BM25 + vector, via a single query) with semantic
ranking so retrieval quality doesn't depend on embeddings alone -- this
is the retrieval half of the RAG pipeline; app/rag/pipeline.py is the
half that turns results into a grounded answer.
"""
import logging
from functools import lru_cache

from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from app.config import get_settings
from app.core.azure_credential import get_credential

logger = logging.getLogger(__name__)

VECTOR_DIMENSIONS = 3072  # text-embedding-3-large; change if using a different embedding model
VECTOR_PROFILE = "hnsw-profile"
SEMANTIC_CONFIG = "semantic-config"


@lru_cache
def _index_client() -> SearchIndexClient:
    settings = get_settings()
    return SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=get_credential())


@lru_cache
def _search_client() -> SearchClient:
    settings = get_settings()
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=get_credential(),
    )


def build_index_definition(index_name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="last_updated", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[VectorSearchProfile(name=VECTOR_PROFILE, algorithm_configuration_name="hnsw-config")],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=None,
                    content_fields=[SemanticField(field_name="content")],
                ),
            )
        ]
    )

    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search, semantic_search=semantic_search)


async def ensure_index_exists() -> None:
    settings = get_settings()
    client = _index_client()
    try:
        await client.get_index(settings.azure_search_index_name)
        logger.info("Search index '%s' already exists.", settings.azure_search_index_name)
    except Exception:
        logger.info("Creating search index '%s'.", settings.azure_search_index_name)
        await client.create_index(build_index_definition(settings.azure_search_index_name))


async def upload_chunks(documents: list[dict]) -> None:
    client = _search_client()
    await client.upload_documents(documents=documents)


async def hybrid_search(
    query_text: str,
    query_vector: list[float],
    top_k: int = 5,
    filter_expr: str | None = None,
) -> list[dict]:
    client = _search_client()
    vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")

    results = await client.search(
        search_text=query_text,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name=SEMANTIC_CONFIG,
        filter=filter_expr,
        top=top_k,
        select=["id", "content", "source", "document_id", "page_number"],
    )

    hits = []
    async for r in results:
        hits.append(
            {
                "id": r["id"],
                "content": r["content"],
                "source": r.get("source"),
                "document_id": r.get("document_id"),
                "page_number": r.get("page_number"),
                "score": r["@search.score"],
                "reranker_score": r.get("@search.reranker_score"),
            }
        )
    return hits
