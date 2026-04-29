from __future__ import annotations

from pathlib import Path

from src.eval.hard_eval import HardEvaluator
from src.eval.llm_eval import LLMEvaluator
from src.eval.report import EvalReport
from src.eval.scorer import Scorer


class Evaluator:
    def __init__(
        self,
        workspace_root: Path,
        live_hard_checks: bool = False,
        command_timeout_sec: int = 20,
        judge_provider: str = "stub",
        judge_model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.hard_eval = HardEvaluator(
            workspace_root=workspace_root,
            live_checks=live_hard_checks,
            timeout_sec=command_timeout_sec,
        )
        self.llm_eval = LLMEvaluator(
            provider=judge_provider,
            model=judge_model,
            api_key=api_key,
            api_base=api_base,
        )
        self.scorer = Scorer()

    def run(self, task: str, final_answer: str, tool_history: list[str]) -> EvalReport:
        hard = self.hard_eval.run(final_answer=final_answer, tool_history=tool_history)
        judge = self.llm_eval.run(task=task, final_answer=final_answer)
        total = self.scorer.aggregate_scores(hard, judge)
        return EvalReport(hard_score=hard, judge_score=judge, total_score=total)
