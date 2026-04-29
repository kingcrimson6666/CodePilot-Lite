from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.core.context_assembler import ContextAssembler
from src.core.orchestrator import AgentOrchestrator
from src.core.planner import Planner
from src.eval.runner import Evaluator
from src.infra.config import AppSettings
from src.memory.long_memory import LongMemory
from src.memory.short_memory import ShortMemory
from src.models.llm_gateway import LLMGateway
from src.observability.logger import LoggerFactory
from src.rag.factory import build_rag_store, ensure_rag_dirs
from src.rag.indexer import RAGIndexer
from src.rag.retriever import RAGRetriever
from src.tools.register_builtin import register_builtin_tools
from src.tools.registry import ToolRegistry
from src.tools.runtime import ToolRuntime


def build_orchestrator(
    settings: AppSettings | None = None,
    interactive_confirm: Callable[[str, str, dict], bool] | None = None,
) -> AgentOrchestrator:
    settings = settings or AppSettings()
    LoggerFactory.configure(settings.log_level)
    workspace_root = Path(settings.workspace_root)

    registry = ToolRegistry()
    register_builtin_tools(registry)

    runtime = ToolRuntime(
        registry=registry,
        workspace_root=workspace_root,
        auto_approve_high_risk=settings.auto_approve_high_risk,
        approval_log_path=settings.approval_log_path,
        interactive_confirm=interactive_confirm,
    )

    ensure_rag_dirs(settings)
    rag_store = build_rag_store(settings)
    RAGIndexer(rag_store).build_index(str(workspace_root))
    rag_retriever = RAGRetriever(rag_store)

    return AgentOrchestrator(
        planner=Planner(),
        context_assembler=ContextAssembler(),
        llm_gateway=LLMGateway(
            provider=settings.model_provider,
            model=settings.model_name,
            api_key=settings.model_api_key,
            api_base=settings.model_api_base,
        ),
        tool_runtime=runtime,
        short_memory=ShortMemory(root=Path("data/memory")),
        long_memory=LongMemory(root=Path("data/memory")),
        rag_retriever=rag_retriever,
        evaluator=Evaluator(
            workspace_root=workspace_root,
            live_hard_checks=settings.live_hard_checks,
            command_timeout_sec=settings.command_timeout_sec,
            judge_provider=settings.judge_model_provider,
            judge_model=settings.judge_model_name,
            api_key=settings.model_api_key,
            api_base=settings.model_api_base,
        ),
        max_steps=settings.max_steps,
        short_memory_summary_every_n=settings.short_memory_summary_every_n,
    )
