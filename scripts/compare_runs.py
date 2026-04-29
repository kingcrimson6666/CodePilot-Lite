from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract_reports(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("reports"), list):
        return payload["reports"]
    return []


def average_total(report: list[dict]) -> float:
    if not report:
        return 0.0
    return sum(item["total_score"]["total"] for item in report) / len(report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--max-regression", type=float, default=0.02)
    args = parser.parse_args()

    a = json.loads(Path(args.run_a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.run_b).read_text(encoding="utf-8"))
    reports_a = extract_reports(a)
    reports_b = extract_reports(b)

    score_a = average_total(reports_a)
    score_b = average_total(reports_b)
    delta = score_b - score_a
    release_ok = delta >= (-1.0 * max(0.0, args.max_regression))

    print(f"run_a avg total: {score_a:.3f}")
    print(f"run_b avg total: {score_b:.3f}")
    print(f"delta: {delta:+.3f}")
    print(f"release_gate: {'PASS' if release_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
