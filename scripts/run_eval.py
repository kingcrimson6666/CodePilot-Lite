from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.bootstrap import build_orchestrator
from src.infra.config import AppSettings
from src.observability.metrics_db import write_eval_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--max-retries", type=int, default=0)
    args = parser.parse_args()

    dataset = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    orchestrator = build_orchestrator()
    settings = AppSettings()

    reports = []
    task_durations_ms: list[float] = []
    passed_count = 0
    first_passed_count = 0
    failed_tool_calls = 0
    total_tool_calls = 0

    for item in dataset:
        started = time.perf_counter()
        result = orchestrator.run_task(item["task"])
        if result.total_score.passed:
            first_passed_count += 1

        retry = 0
        while (not result.total_score.passed) and retry < max(0, args.max_retries):
            retry += 1
            result = orchestrator.run_task(item["task"])

        duration_ms = (time.perf_counter() - started) * 1000
        task_durations_ms.append(duration_ms)

        payload = result.model_dump()
        reports.append(payload)

        if payload["total_score"]["passed"]:
            passed_count += 1

        tool_history = payload.get("tool_history", [])
        total_tool_calls += len(tool_history)
        failed_tool_calls += sum(1 for evt in tool_history if "failed" in evt.lower())

    total_tasks = len(reports)
    tsr = (passed_count / total_tasks) if total_tasks else 0.0
    otr = (first_passed_count / total_tasks) if total_tasks else 0.0
    mttr_ms = (sum(task_durations_ms) / total_tasks) if total_tasks else 0.0
    invalid_tool_call_rate = (failed_tool_calls / total_tool_calls) if total_tool_calls else 0.0

    output = {
        "summary": {
            "total_tasks": total_tasks,
            "passed_tasks": passed_count,
            "tsr": tsr,
            "otr": otr,
            "mttr_ms": mttr_ms,
            "invalid_tool_call_rate": invalid_tool_call_rate,
        },
        "reports": reports,
    }

    out = Path("data/eval/reports/latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    write_eval_summary(summary=output["summary"], report_path=str(out), db_path=settings.metrics_db_path)
    print(f"Wrote report: {out}")


if __name__ == "__main__":
    main()
