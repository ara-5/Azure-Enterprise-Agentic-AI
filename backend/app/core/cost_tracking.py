"""Turns Azure OpenAI token usage into dollars, in real time.

Every chat completion and embedding call goes through `record_usage`, which:
  1. computes $ cost from the token counts using configurable per-1K rates
  2. emits an App Insights custom event (queryable in Log Analytics / a
     workbook) tagged with user, operation, model and route
  3. appends a durable JSONL record to Blob Storage for offline reporting
  4. maintains an in-process running total for the current month and fires
     a webhook alert once the configured budget is crossed

This is intentionally simple (no external billing API) so it works
identically for local dev and Azure -- the same $/1K rates you'd pull from
the Azure Pricing calculator are just config (see .env.example).
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

import httpx

from app.config import get_settings
from app.core.telemetry import emit_event
from app.services import blob_storage

logger = logging.getLogger(__name__)

COST_CONTAINER = "cost-exports"


@dataclass
class UsageRecord:
    timestamp: str
    operation: str  # "chat" | "embedding"
    model: str
    route: str
    user_id: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class _MonthlyTotal:
    """Process-local running total. Good enough for a single-replica demo;
    for multi-replica production this would move to a shared store
    (Table Storage / Redis) -- called out explicitly rather than faked."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._month_key = self._current_month_key()
        self._total_usd = 0.0
        self._alerted = False

    @staticmethod
    def _current_month_key() -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    def add(self, amount: float) -> float:
        with self._lock:
            key = self._current_month_key()
            if key != self._month_key:
                self._month_key = key
                self._total_usd = 0.0
                self._alerted = False
            self._total_usd += amount
            return self._total_usd

    @property
    def alerted(self) -> bool:
        return self._alerted

    def mark_alerted(self) -> None:
        with self._lock:
            self._alerted = True


_monthly_total = _MonthlyTotal()


def _cost_for(operation: str, prompt_tokens: int, completion_tokens: int) -> float:
    settings = get_settings()
    if operation == "embedding":
        return (prompt_tokens / 1000) * settings.cost_embedding_per_1k_tokens
    return (
        (prompt_tokens / 1000) * settings.cost_input_per_1k_tokens
        + (completion_tokens / 1000) * settings.cost_output_per_1k_tokens
    )


async def record_usage(
    *,
    operation: str,
    model: str,
    route: str,
    prompt_tokens: int,
    completion_tokens: int = 0,
    user_id: str | None = None,
) -> UsageRecord:
    settings = get_settings()
    cost = _cost_for(operation, prompt_tokens, completion_tokens)
    record = UsageRecord(
        timestamp=datetime.now(UTC).isoformat(),
        operation=operation,
        model=model,
        route=route,
        user_id=user_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=round(cost, 6),
    )

    emit_event(
        "llm_usage",
        {
            "operation": operation,
            "model": model,
            "route": route,
            "user_id": user_id or "anonymous",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": record.cost_usd,
        },
    )

    running_total = _monthly_total.add(cost)
    if running_total >= settings.cost_budget_monthly_usd and not _monthly_total.alerted:
        _monthly_total.mark_alerted()
        asyncio.create_task(_fire_budget_alert(running_total))

    try:
        await blob_storage.append_jsonl_record(COST_CONTAINER, "usage", record.__dict__)
    except Exception:
        logger.exception("Failed to persist cost record; continuing (non-fatal).")

    return record


async def _fire_budget_alert(running_total_usd: float) -> None:
    settings = get_settings()
    logger.warning("Monthly cost budget exceeded: $%.2f >= $%.2f", running_total_usd, settings.cost_budget_monthly_usd)
    emit_event("cost_budget_exceeded", {"running_total_usd": running_total_usd, "budget_usd": settings.cost_budget_monthly_usd})
    if not settings.cost_alert_webhook_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                settings.cost_alert_webhook_url,
                json={
                    "text": (
                        f":rotating_light: Azure Enterprise Agentic AI cost budget exceeded: "
                        f"${running_total_usd:.2f} of ${settings.cost_budget_monthly_usd:.2f} this month."
                    )
                },
            )
    except Exception:
        logger.exception("Failed to send cost budget alert webhook.")


def current_month_total_usd() -> float:
    return round(_monthly_total._total_usd, 4)
