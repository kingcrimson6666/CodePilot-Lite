from __future__ import annotations

from src.models.prompt_builder import PromptBuilder
from src.models.output_schema import Plan


class ContextAssembler:
    def __init__(self) -> None:
        self.prompt_builder = PromptBuilder()

    def assemble(self, task: str, plan: Plan, memory: str, rag: str) -> str:
        return self.prompt_builder.build_context_prompt(task=task, plan=plan, memory=memory, rag=rag)

    def enforce_budget(self, context: str, token_budget: int = 2500) -> str:
        # Keep high-priority sections first and trim RAG/memory aggressively.
        if len(context) <= token_budget:
            return context

        task_split = context.split("Memory:\n", maxsplit=1)
        if len(task_split) != 2:
            return context[:token_budget]

        head = task_split[0] + "Memory:\n"
        memory_and_rag = task_split[1]
        mem_split = memory_and_rag.split("RAG:\n", maxsplit=1)
        if len(mem_split) != 2:
            return (head + memory_and_rag)[:token_budget]

        memory_block, rag_block = mem_split

        # Budget slices: preserve head, then memory, then RAG.
        remaining = max(token_budget - len(head), 0)
        memory_quota = int(remaining * 0.35)
        rag_quota = remaining - memory_quota

        memory_trimmed = memory_block[-memory_quota:] if memory_quota > 0 else ""
        rag_trimmed = rag_block[:rag_quota] if rag_quota > 0 else ""

        return f"{head}{memory_trimmed}RAG:\n{rag_trimmed}"
