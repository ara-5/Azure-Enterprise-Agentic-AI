"""Aggregates the durable cost JSONL records (written by
app.core.cost_tracking to the `cost-exports` blob container) into a
per-day / per-model summary. This is the historical, cross-replica
complement to the live GET /api/cost/summary endpoint, which only reflects
the current process's in-memory running total.

Usage:
    python scripts/cost_report.py --days 30
"""
import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.services import blob_storage  # noqa: E402
import json  # noqa: E402


async def main(days: int) -> None:
    settings = get_settings()
    container = settings.azure_storage_container_cost
    since = datetime.now(timezone.utc) - timedelta(days=days)

    totals_by_day: dict[str, float] = defaultdict(float)
    totals_by_model: dict[str, float] = defaultdict(float)
    total_tokens = 0
    total_cost = 0.0

    async for blob_name in blob_storage.list_documents(container):
        if not blob_name.startswith("usage/"):
            continue
        date_str = blob_name.split("/")[-1].replace(".jsonl", "")
        try:
            blob_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if blob_date < since:
            continue

        raw = await blob_storage.download_document(container, blob_name)
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            totals_by_day[date_str] += record["cost_usd"]
            totals_by_model[record["model"]] += record["cost_usd"]
            total_tokens += record["total_tokens"]
            total_cost += record["cost_usd"]

    print(f"Cost report: last {days} day(s)\n" + "=" * 40)
    print(f"Total spend: ${total_cost:.4f}")
    print(f"Total tokens: {total_tokens:,}")
    print("\nBy day:")
    for day in sorted(totals_by_day):
        print(f"  {day}: ${totals_by_day[day]:.4f}")
    print("\nBy model:")
    for model, cost in sorted(totals_by_model.items(), key=lambda x: -x[1]):
        print(f"  {model}: ${cost:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(main(args.days))
