import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.auth.entra import CurrentUser, require_role

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

# backend/evaluation/results, kept separate from app/ so the eval harness
# can also be run standalone via `python -m evaluation.run_evaluation`.
RESULTS_DIR = Path(__file__).resolve().parents[3] / "evaluation" / "results"


@router.get("/latest")
async def latest_report(user: CurrentUser = Depends(require_role("admin"))) -> dict:
    """Returns the most recent evaluation report written by evaluation/run_evaluation.py
    (run manually, or automatically in CI -- see .github/workflows/ci.yml)."""
    if not RESULTS_DIR.exists():
        return {"status": "no_reports_yet"}
    reports = sorted(RESULTS_DIR.glob("eval-*.json"))
    if not reports:
        return {"status": "no_reports_yet"}
    return json.loads(reports[-1].read_text(encoding="utf-8"))
