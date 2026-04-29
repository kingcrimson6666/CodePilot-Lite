from __future__ import annotations

from src.models.output_schema import Plan


class PromptBuilder:
    def build_context_prompt(self, task: str, plan: Plan, memory: str, rag: str) -> str:
        steps = "\n".join(f"- [{ 'x' if s.done else ' '}] {s.id}. {s.title}" for s in plan.steps)
        return (
            "任务:\n"
            f"{task}\n\n"
            "计划:\n"
            f"{steps}\n\n"
            "记忆:\n"
            f"{memory}\n\n"
            "RAG:\n"
            f"{rag}\n"
        )
