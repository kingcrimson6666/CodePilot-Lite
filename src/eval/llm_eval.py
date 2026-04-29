from __future__ import annotations

import json

from src.models.output_schema import JudgeScore


class LLMEvaluator:
    def __init__(
        self,
        provider: str = "stub",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    def run(self, task: str, final_answer: str) -> JudgeScore:
        if self.provider == "openai":
            judge = self._run_openai(task, final_answer)
            if judge is not None:
                return judge

        return self._run_heuristic(task, final_answer)

    def _run_heuristic(self, task: str, final_answer: str) -> JudgeScore:
        coverage = 1.0 if any(token in final_answer.lower() for token in task.lower().split()[:2]) else 0.6
        readability = 0.9 if len(final_answer) > 40 else 0.6
        risk_awareness = 0.8 if "review" in final_answer.lower() or "risk" in final_answer.lower() else 0.6
        explanation = 0.8 if "." in final_answer else 0.6
        return JudgeScore(
            coverage=coverage,
            readability=readability,
            risk_awareness=risk_awareness,
            explanation=explanation,
        )

    def _run_openai(self, task: str, final_answer: str) -> JudgeScore | None:
        if not self.api_key:
            return None
        try:
            from openai import OpenAI
        except Exception:  # noqa: BLE001
            return None

        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
        client = OpenAI(**client_kwargs)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict code assistant judge. Score each field from 0.0 to 1.0. "
                    "Output JSON only with keys: coverage, readability, risk_awareness, explanation."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"task": task, "answer": final_answer},
                    ensure_ascii=True,
                ),
            },
        ]

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            payload = json.loads(content)
            return JudgeScore(
                coverage=self._clamp(payload.get("coverage", 0.0)),
                readability=self._clamp(payload.get("readability", 0.0)),
                risk_awareness=self._clamp(payload.get("risk_awareness", 0.0)),
                explanation=self._clamp(payload.get("explanation", 0.0)),
            )
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _clamp(value: float) -> float:
        try:
            v = float(value)
        except Exception:  # noqa: BLE001
            return 0.0
        return max(0.0, min(1.0, v))
