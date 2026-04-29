from __future__ import annotations

from pathlib import Path
from statistics import mean
from sqlalchemy import text

from src.infra.db import build_engine


def ensure_metrics_tables(db_path: Path | str = "data/codepilot.sqlite") -> None:
    engine = build_engine(db_path)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    report_path TEXT NOT NULL,
                    total_tasks INTEGER NOT NULL,
                    passed_tasks INTEGER NOT NULL,
                    tsr REAL NOT NULL,
                    otr REAL NOT NULL,
                    mttr_ms REAL NOT NULL,
                    invalid_tool_call_rate REAL NOT NULL
                )
                """
            )
        )


def write_eval_summary(summary: dict, report_path: str, db_path: Path | str = "data/codepilot.sqlite") -> None:
    ensure_metrics_tables(db_path)
    engine = build_engine(db_path)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO eval_runs (
                    created_at,
                    report_path,
                    total_tasks,
                    passed_tasks,
                    tsr,
                    otr,
                    mttr_ms,
                    invalid_tool_call_rate
                ) VALUES (
                    datetime('now'),
                    :report_path,
                    :total_tasks,
                    :passed_tasks,
                    :tsr,
                    :otr,
                    :mttr_ms,
                    :invalid_tool_call_rate
                )
                """
            ),
            {
                "report_path": report_path,
                "total_tasks": int(summary.get("total_tasks", 0)),
                "passed_tasks": int(summary.get("passed_tasks", 0)),
                "tsr": float(summary.get("tsr", 0.0)),
                "otr": float(summary.get("otr", 0.0)),
                "mttr_ms": float(summary.get("mttr_ms", 0.0)),
                "invalid_tool_call_rate": float(summary.get("invalid_tool_call_rate", 0.0)),
            },
        )


def read_recent_eval_summaries(db_path: Path | str = "data/codepilot.sqlite", limit: int = 10) -> list[dict]:
    ensure_metrics_tables(db_path)
    engine = build_engine(db_path)
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT created_at, report_path, total_tasks, passed_tasks, tsr, otr, mttr_ms, invalid_tool_call_rate
                FROM eval_runs
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": max(1, int(limit))},
        ).mappings()
        return [dict(row) for row in rows]


def read_latest_eval_summary(db_path: Path | str = "data/codepilot.sqlite") -> dict | None:
    rows = read_recent_eval_summaries(db_path=db_path, limit=1)
    if not rows:
        return None
    return rows[0]


def build_trend_snapshot(db_path: Path | str = "data/codepilot.sqlite", window: int = 5) -> dict:
    rows = list(reversed(read_recent_eval_summaries(db_path=db_path, limit=window)))
    if not rows:
        return {
            "count": 0,
            "avg_tsr": 0.0,
            "avg_otr": 0.0,
            "avg_mttr_ms": 0.0,
            "avg_invalid_tool_call_rate": 0.0,
            "tsr_delta": 0.0,
        }

    tsr_values = [float(r.get("tsr", 0.0)) for r in rows]
    otr_values = [float(r.get("otr", 0.0)) for r in rows]
    mttr_values = [float(r.get("mttr_ms", 0.0)) for r in rows]
    invalid_values = [float(r.get("invalid_tool_call_rate", 0.0)) for r in rows]

    return {
        "count": len(rows),
        "avg_tsr": mean(tsr_values),
        "avg_otr": mean(otr_values),
        "avg_mttr_ms": mean(mttr_values),
        "avg_invalid_tool_call_rate": mean(invalid_values),
        "tsr_delta": tsr_values[-1] - tsr_values[0] if len(tsr_values) >= 2 else 0.0,
        "first_tsr": tsr_values[0],
        "last_tsr": tsr_values[-1],
    }


def detect_tsr_drift(db_path: Path | str = "data/codepilot.sqlite", baseline_window: int = 5, recent_window: int = 3, tolerance: float = 0.05) -> dict:
    baseline_rows = read_recent_eval_summaries(db_path=db_path, limit=max(1, baseline_window + recent_window))
    ordered = list(reversed(baseline_rows))
    if len(ordered) < (baseline_window + recent_window):
        return {
            "drifted": False,
            "reason": "insufficient_data",
            "required": baseline_window + recent_window,
            "observed": len(ordered),
        }

    baseline_part = ordered[:baseline_window]
    recent_part = ordered[-recent_window:]

    baseline_avg = mean(float(r.get("tsr", 0.0)) for r in baseline_part)
    recent_avg = mean(float(r.get("tsr", 0.0)) for r in recent_part)
    drop = baseline_avg - recent_avg

    return {
        "drifted": drop > tolerance,
        "reason": "drop_exceeds_tolerance" if drop > tolerance else "stable",
        "baseline_avg_tsr": baseline_avg,
        "recent_avg_tsr": recent_avg,
        "drop": drop,
        "tolerance": tolerance,
    }
