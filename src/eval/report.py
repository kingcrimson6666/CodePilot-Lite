from __future__ import annotations

from pydantic import BaseModel

from src.models.output_schema import HardScore, JudgeScore, TotalScore


class EvalReport(BaseModel):
    hard_score: HardScore | None = None
    judge_score: JudgeScore | None = None
    total_score: TotalScore
