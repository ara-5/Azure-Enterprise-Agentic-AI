"""RAG quality evaluators.

Uses Microsoft's `azure-ai-evaluation` SDK for the standard AI-assisted
metrics (groundedness, relevance, coherence) so scoring methodology matches
what Azure AI Foundry's own evaluation UI reports -- plus one custom,
deterministic metric (retrieval precision) that the SDK doesn't cover,
since it's specific to how this platform's retriever is judged.
"""
from dataclasses import dataclass

from app.config import get_settings


@dataclass
class EvalResult:
    question: str
    answer: str
    ground_truth: str
    groundedness: float
    relevance: float
    coherence: float
    retrieval_precision: float


def _model_config() -> dict:
    settings = get_settings()
    config = {
        "azure_endpoint": settings.azure_openai_endpoint,
        "azure_deployment": settings.azure_openai_chat_deployment,
        "api_version": settings.azure_openai_api_version,
    }
    if settings.azure_openai_api_key:
        config["api_key"] = settings.azure_openai_api_key
    return config


def retrieval_precision(expected_sources: list[str], actual_citations: list[dict]) -> float:
    if not expected_sources:
        return 1.0
    actual = {c.get("source") or c.get("document_id") for c in actual_citations}
    hits = sum(1 for s in expected_sources if s in actual)
    return round(hits / len(expected_sources), 4)


def build_evaluators():
    """Lazily imported: azure-ai-evaluation pulls in a fair amount of
    tooling, and CI's lint/unit-test job shouldn't need it installed."""
    from azure.ai.evaluation import CoherenceEvaluator, GroundednessEvaluator, RelevanceEvaluator

    model_config = _model_config()
    return {
        "groundedness": GroundednessEvaluator(model_config),
        "relevance": RelevanceEvaluator(model_config),
        "coherence": CoherenceEvaluator(model_config),
    }


def evaluate_one(evaluators: dict, *, question: str, answer: str, context: str, ground_truth: str) -> dict:
    groundedness = evaluators["groundedness"](query=question, response=answer, context=context)
    relevance = evaluators["relevance"](query=question, response=answer)
    coherence = evaluators["coherence"](query=question, response=answer)
    return {
        "groundedness": groundedness.get("groundedness", groundedness.get("gpt_groundedness", 0)),
        "relevance": relevance.get("relevance", relevance.get("gpt_relevance", 0)),
        "coherence": coherence.get("coherence", coherence.get("gpt_coherence", 0)),
    }
