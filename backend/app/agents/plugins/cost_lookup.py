"""A small second plugin so the agent demonstrably has more than one tool
and has to *choose* between them -- also doubles as a live demo of the
cost-tracking system from inside a chat conversation."""
import json

from semantic_kernel.functions import kernel_function

from app.config import get_settings
from app.core.cost_tracking import current_month_total_usd


class CostLookupPlugin:
    """Report on this platform's own Azure OpenAI usage cost."""

    @kernel_function(
        name="get_current_month_ai_spend",
        description="Get the platform's own Azure OpenAI spend (USD) for the current calendar month, and the configured budget.",
    )
    def get_current_month_ai_spend(self) -> str:
        settings = get_settings()
        return json.dumps(
            {
                "month_to_date_usd": current_month_total_usd(),
                "monthly_budget_usd": settings.cost_budget_monthly_usd,
            }
        )
