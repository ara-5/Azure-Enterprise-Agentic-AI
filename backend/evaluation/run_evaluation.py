"""RAG evaluation runner.

Usage:
    python -m evaluation.run_evaluation [--threshold 3.5] [--dataset golden_dataset.jsonl]

Runs every question in the golden dataset through the real RAG pipeline
(app.rag.pipeline.answer_question), scores each answer with the AI-assisted
metrics in evaluators.py plus retrieval precision, writes a JSON report to
evaluation/results/, and exits non-zero if the average score is below
--threshold -- wired into .github/workflows/ci.yml as an evaluation gate
so regressions in retrieval or prompt quality fail the build, not just get
noticed later in production.
"""
import argparse
import asyncio
import json
import logging
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.pipeline import answer_question  # noqa: E402
from evaluation.evaluators import build_evaluators, evaluate_one, retrieval_precision  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evaluation")

RESULTS_DIR = Path(__file__).parent / "results"


async def run(dataset_path: Path) -> dict:
    evaluators = build_evaluators()
    rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    results = []
    for row in rows:
        logger.info("Evaluating: %s", row["question"])
        rag_result = await answer_question(row["question"], route="/evaluation")
        context = "\n\n".join(c.get("source", "") for c in rag_result.citations)

        scores = evaluate_one(
            evaluators,
            question=row["question"],
            answer=rag_result.answer,
            context=context,
            ground_truth=row["ground_truth"],
        )
        scores["retrieval_precision"] = retrieval_precision(row.get("expected_sources", []), rag_result.citations)
        results.append({"question": row["question"], "answer": rag_result.answer, **scores})

    summary = {
        metric: round(statistics.mean(r[metric] for r in results), 4)
        for metric in ("groundedness", "relevance", "coherence", "retrieval_precision")
    }

    return {"generated_at": datetime.now(UTC).isoformat(), "summary": summary, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(Path(__file__).parent / "golden_dataset.jsonl"))
    parser.add_argument("--threshold", type=float, default=3.5, help="Minimum average groundedness/relevance/coherence (1-5 scale) to pass.")
    args = parser.parse_args()

    report = asyncio.run(run(Path(args.dataset)))

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2))
    print(f"Full report: {out_path}")

    quality_avg = statistics.mean(
        [report["summary"]["groundedness"], report["summary"]["relevance"], report["summary"]["coherence"]]
    )
    if quality_avg < args.threshold:
        print(f"FAIL: average quality score {quality_avg:.2f} < threshold {args.threshold}", file=sys.stderr)
        sys.exit(1)

    print(f"PASS: average quality score {quality_avg:.2f} >= threshold {args.threshold}")


if __name__ == "__main__":
    main()
