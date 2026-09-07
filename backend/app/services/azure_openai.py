"""Azure OpenAI client factory.

Auth priority: Managed Identity (production) via a bearer-token provider,
falling back to an API key only when explicitly set (local dev convenience).
This mirrors the pattern Microsoft's own reference RAG architectures use so
the same code runs unchanged from a laptop to a Container App.
"""
from functools import lru_cache

from azure.identity import get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import get_settings
from app.core.azure_credential import COGNITIVE_SERVICES_SCOPE, get_credential


@lru_cache
def get_client() -> AsyncAzureOpenAI:
    settings = get_settings()
    if settings.azure_openai_api_key:
        return AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    token_provider = get_bearer_token_provider(get_credential(), COGNITIVE_SERVICES_SCOPE)
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=settings.azure_openai_api_version,
    )


def chat_deployment() -> str:
    return get_settings().azure_openai_chat_deployment


def embedding_deployment() -> str:
    return get_settings().azure_openai_embedding_deployment
