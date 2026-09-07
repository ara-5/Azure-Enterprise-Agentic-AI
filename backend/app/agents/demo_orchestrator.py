"""Zero-Azure-cost stand-in for app/agents/orchestrator.py.

The real orchestrator lets Azure OpenAI decide which Semantic Kernel plugin
to call. Without a live model, this uses simple keyword rules to make the
same decision, so the demo still shows the *shape* of agentic tool choice
(the UI literally displays which tool fired) even though the routing logic
here is hand-written rather than model-chosen. Swap DEMO_MODE off for the
real thing.
"""
import re

from app.config import get_settings
from app.core.cost_tracking import current_month_total_usd
from app.rag.demo import answer_question_demo

_COST_KEYWORDS = re.compile(r"\b(cost|spend|spending|budget|expense|usd|\$|price|pricing)\b", re.IGNORECASE)


async def run_agent_turn_demo(question: str) -> str:
    if _COST_KEYWORDS.search(question):
        settings = get_settings()
        total = current_month_total_usd()
        return (
            "[Demo mode - rule-based tool routing, no Azure OpenAI configured]\n\n"
            "Tool called: CostLookup.get_current_month_ai_spend\n"
            f"Result: ${total:.2f} spent this month against a ${settings.cost_budget_monthly_usd:.0f} budget.\n\n"
            "(In live mode, a Semantic Kernel agent backed by Azure OpenAI decides this for itself via "
            "function calling -- see app/agents/orchestrator.py.)"
        )

    result = answer_question_demo(question)
    citation_list = ", ".join(c["source"] for c in result.citations) or "no matching documents"
    return (
        "[Demo mode - rule-based tool routing, no Azure OpenAI configured]\n\n"
        "Tool called: KnowledgeBase.search_knowledge_base\n"
        f"Sources retrieved: {citation_list}\n\n"
        f"{result.answer}"
    )
