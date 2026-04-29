from __future__ import annotations

from src.models.output_schema import HardScore, JudgeScore, TotalScore


class Scorer:
    def aggregate_scores(self, hard: HardScore, judge: JudgeScore, pass_threshold: float = 0.65) -> TotalScore:
        hard_value = (hard.tests_passed + hard.constraints_ok) / 2
        judge_value = (judge.coverage + judge.readability + judge.risk_awareness + judge.explanation) / 4
        total = hard_value * 0.7 + judge_value * 0.3
        return TotalScore(hard=hard_value, judge=judge_value, total=total, passed=total >= pass_threshold)
