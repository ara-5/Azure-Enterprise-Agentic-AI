"""Semantic Kernel agent: the platform's agentic entry point.

Wraps the same Azure OpenAI deployment used by the plain-RAG pipeline
(app/rag/pipeline.py) but gives the model tools (KnowledgeBasePlugin,
CostLookupPlugin) and lets it decide, per turn, whether to call them --
this is the "agentic" in Agentic RAG, as opposed to the always-retrieve
pipeline used by /api/chat/completions.
"""
import logging
from functools import lru_cache

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from app.agents.plugins.cost_lookup import CostLookupPlugin
from app.agents.plugins.knowledge_base import KnowledgeBasePlugin
from app.config import get_settings
from app.core.azure_credential import COGNITIVE_SERVICES_SCOPE, get_credential
from app.core.cost_tracking import record_usage
from app.core.telemetry import tracer

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an enterprise agentic assistant. You have tools to search the
company knowledge base and to check this platform's own AI spend. Use tools when they would help
answer the question; do not use them for generic questions unrelated to internal knowledge. Always
cite the `source` field when you use retrieved knowledge-base content. Be concise."""


@lru_cache
def get_kernel() -> Kernel:
    settings = get_settings()
    kernel = Kernel()

    from azure.identity import get_bearer_token_provider

    if settings.azure_openai_api_key:
        service = AzureChatCompletion(
            deployment_name=settings.azure_openai_chat_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    else:
        token_provider = get_bearer_token_provider(get_credential(), COGNITIVE_SERVICES_SCOPE)
        service = AzureChatCompletion(
            deployment_name=settings.azure_openai_chat_deployment,
            endpoint=settings.azure_openai_endpoint,
            ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )

    kernel.add_service(service)
    kernel.add_plugin(KnowledgeBasePlugin(), plugin_name="KnowledgeBase")
    kernel.add_plugin(CostLookupPlugin(), plugin_name="CostLookup")
    return kernel


async def run_agent_turn(question: str, *, user_id: str | None = None, route: str = "/agents/chat") -> str:
    kernel = get_kernel()
    chat_service: AzureChatCompletion = kernel.get_service(type=AzureChatCompletion)

    history = ChatHistory(system_message=AGENT_SYSTEM_PROMPT)
    history.add_user_message(question)

    settings = AzureChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
        temperature=0.2,
    )

    with tracer.start_as_current_span("agent.run_turn"):
        response: ChatMessageContent | None = await chat_service.get_chat_message_content(
            chat_history=history, settings=settings, kernel=kernel
        )

    if response is None:
        return "The agent did not return a response."

    usage = response.metadata.get("usage")
    if usage:
        await record_usage(
            operation="chat",
            model=get_settings().azure_openai_chat_deployment,
            route=route,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            user_id=user_id,
        )

    return str(response)
