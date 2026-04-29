from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.governance.convergence import evaluate_release_gate
from src.observability.metrics_db import detect_tsr_drift, read_latest_eval_summary, read_recent_eval_summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="data/codepilot.sqlite")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.65)
    parser.add_argument("--min-runs", type=int, default=2)
    parser.add_argument("--max-drop", type=float, default=0.05)
    parser.add_argument("--baseline-window", type=int, default=5)
    parser.add_argument("--recent-window", type=int, default=3)
    parser.add_argument("--drift-tolerance", type=float, default=0.05)
    parser.add_argument("--min-latest-tasks", type=int, default=20)
    args = parser.parse_args()

    db_path = Path(args.db_path)
    rows = read_recent_eval_summaries(db_path=db_path, limit=args.limit)
    rates = [float(row.get("tsr", 0.0)) for row in reversed(rows)]

    convergence = evaluate_release_gate(
        recent_success_rates=rates,
        threshold=args.threshold,
        min_runs=args.min_runs,
        max_drop=args.max_drop,
    )
    drift = detect_tsr_drift(
        db_path=db_path,
        baseline_window=args.baseline_window,
        recent_window=args.recent_window,
        tolerance=args.drift_tolerance,
    )
    latest = read_latest_eval_summary(db_path=db_path)
    dod_tasks_ok = bool(latest) and int(latest.get("total_tasks", 0)) >= int(args.min_latest_tasks)

    decision = {
        "allowed": bool(convergence.get("allowed", False)) and (not bool(drift.get("drifted", False))) and dod_tasks_ok,
        "convergence": convergence,
        "drift": drift,
        "dod_latest_tasks_ok": dod_tasks_ok,
        "latest_total_tasks": int(latest.get("total_tasks", 0)) if latest else 0,
        "required_latest_tasks": int(args.min_latest_tasks),
    }
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    raise SystemExit(0 if decision["allowed"] else 1)


if __name__ == "__main__":
    main()
