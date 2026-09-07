from fastapi import APIRouter, Depends

from app.auth.entra import CurrentUser, get_current_user
from app.config import get_settings
from app.core.cost_tracking import current_month_total_usd
from app.models.schemas import CostSummaryResponse

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("/summary", response_model=CostSummaryResponse)
async def cost_summary(user: CurrentUser = Depends(get_current_user)) -> CostSummaryResponse:
    """Month-to-date Azure OpenAI spend tracked by this process, vs. the configured budget.

    For historical/cross-replica reporting, see scripts/cost_report.py which
    aggregates the durable JSONL records this endpoint's writes land in
    (Blob Storage container `cost-exports`).
    """
    settings = get_settings()
    total = current_month_total_usd()
    return CostSummaryResponse(
        month_to_date_usd=total,
        monthly_budget_usd=settings.cost_budget_monthly_usd,
        percent_of_budget=round(100 * total / settings.cost_budget_monthly_usd, 2) if settings.cost_budget_monthly_usd else 0.0,
    )
