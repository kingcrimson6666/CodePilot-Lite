from __future__ import annotations

from dataclasses import dataclass, field
import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from src.core.context_assembler import ContextAssembler
from src.core.planner import Planner
from src.core.state_machine import TaskStatus
from src.core.stop_rules import should_stop
from src.eval.runner import Evaluator
from src.memory.long_memory import LongMemory
from src.memory.short_memory import ShortMemory
from src.memory.summarizer import summarize_recent
from src.models.llm_gateway import LLMGateway
from src.models.output_schema import HardScore, JudgeScore, TaskResult
from src.observability.logger import LoggerFactory
from src.observability.replay import save_replay
from src.rag.retriever import RAGRetriever
from src.tools.runtime import ToolRuntime


@dataclass
class RuntimeState:
    task: str
    status: TaskStatus = TaskStatus.initialized
    step_count: int = 0
    tool_history: list[str] = field(default_factory=list)
    final_answer: str = ""
    session_id: str = "default"
    task_id: str = ""
    events: list[dict] = field(default_factory=list)
    pending_approval_tickets: list[str] = field(default_factory=list)


class AgentOrchestrator:
    def __init__(
        self,
        planner: Planner,
        context_assembler: ContextAssembler,
        llm_gateway: LLMGateway,
        tool_runtime: ToolRuntime,
        short_memory: ShortMemory,
        long_memory: LongMemory,
        rag_retriever: RAGRetriever,
        evaluator: Evaluator,
        max_steps: int = 6,
        short_memory_summary_every_n: int = 3,
    ) -> None:
        self.planner = planner
        self.context_assembler = context_assembler
        self.llm_gateway = llm_gateway
        self.tool_runtime = tool_runtime
        self.short_memory = short_memory
        self.long_memory = long_memory
        self.rag_retriever = rag_retriever
        self.evaluator = evaluator
        self.max_steps = max_steps
        self.short_memory_summary_every_n = max(1, short_memory_summary_every_n)
        self.logger = LoggerFactory.get_logger("orchestrator")

    def run_task(self, task_input: str, session_id: str | None = None) -> TaskResult:
        task_id = str(uuid4())
        if session_id is None:
            session_id = task_id.split("-")[0]
        state = RuntimeState(task=task_input, status=TaskStatus.running, session_id=session_id, task_id=task_id)
        plan = self.planner.build_plan(task_input)
        state.events.append({"type": "task_started", "task_id": task_id, "task": task_input})

        while not should_stop(state.step_count, self.max_steps):
            short_memory_snapshot = self.short_memory.read(state.session_id)
            long_memories = self.long_memory.recall(task_input, top_k=3)
            rag_chunks = self.rag_retriever.hybrid_retrieve(task_input, k_sparse=2, k_dense=2)

            memory_block = short_memory_snapshot
            if long_memories:
                memory_block = memory_block + "\n" + "\n".join(long_memories)

            rag_block = "\n".join(rag_chunks)
            context = self.context_assembler.assemble(task_input, plan, memory_block, rag=rag_block)
            context = self.context_assembler.enforce_budget(context)

            action = self.llm_gateway.decide_action(task_input, state.tool_history, context=context)
            state.step_count += 1
            state.events.append(
                {
                    "type": "action_decided",
                    "step": state.step_count,
                    "action_type": action.type.value,
                    "tool_name": action.tool_name,
                }
            )

            if action.type.value == "final_answer":
                state.final_answer = action.response or "Task finished."
                state.events.append({"type": "final_answer", "text": state.final_answer})
                break

            result = self.tool_runtime.execute_with_retry(action.tool_name or "", action.args)
            stdout = (result.stdout or "").strip()
            if action.tool_name == "read_file":
                stdout_preview = stdout.replace("\n", " ")[:2000]
            else:
                stdout_preview = stdout.replace("\n", " ")[:160]
            event = f"{action.tool_name}: {'ok' if result.ok else 'failed'} | {stdout_preview}"
            state.tool_history.append(event)
            approval_ticket = str(result.data.get("approval_ticket_id", ""))
            approval_status = str(result.data.get("approval_status", ""))
            if approval_ticket and approval_status == "pending":
                state.pending_approval_tickets.append(approval_ticket)

            self.short_memory.write(state.session_id, event)
            if state.step_count % self.short_memory_summary_every_n == 0:
                summary = summarize_recent(self.short_memory.read(state.session_id), max_lines=8)
                if summary:
                    self.short_memory.write(state.session_id, f"[summary@step={state.step_count}]\n{summary}")
            if result.ok:
                tags = ["outcome:ok"]
                if action.tool_name:
                    tags.append(f"tool:{action.tool_name}")
                self.long_memory.write(
                    f"task={task_input} strategy={action.tool_name} outcome=ok",
                    tags=tags,
                )
            self.logger.info("tool_event", tool=action.tool_name, ok=result.ok)
            state.events.append(
                {
                    "type": "tool_result",
                    "step": state.step_count,
                    "tool_name": action.tool_name,
                    "ok": result.ok,
                    "approval_status": approval_status,
                    "approval_ticket_id": approval_ticket,
                    "duration_ms": result.duration_ms,
                }
            )
            plan = self.planner.update_plan(plan, "tool_ok" if result.ok else "tool_failed")

        if not state.final_answer:
            state.final_answer = (
                "Execution reached stop condition. Collected observations from tools; "
                "please review history and continue with a focused follow-up task."
            )

        auto_write_result = self._maybe_write_generated_code(task_input, state.final_answer)
        if auto_write_result:
            state.events.append(
                {
                    "type": "generated_code_written",
                    "path": auto_write_result,
                }
            )
            if "未写入：" in auto_write_result:
                state.final_answer = f"代码未通过校验，未写入：{auto_write_result}"
            else:
                state.final_answer = f"已写入 {auto_write_result}"

        state.status = TaskStatus.evaluating
        eval_report = self.evaluator.run(task=task_input, final_answer=state.final_answer, tool_history=state.tool_history)
        state.events.append(
            {
                "type": "evaluation",
                "total": eval_report.total_score.total,
                "passed": eval_report.total_score.passed,
            }
        )

        state.status = TaskStatus.completed
        state.events.append({"type": "task_completed", "task_id": state.task_id, "status": state.status.value})
        replay_path = Path("data/replays") / f"{state.task_id}.json"
        save_replay(replay_path, state.events)

        return TaskResult(
            task_id=state.task_id,
            session_id=state.session_id,
            task=task_input,
            final_answer=state.final_answer or "No final answer produced.",
            tool_history=state.tool_history,
            pending_approval_tickets=state.pending_approval_tickets,
            replay_path=str(replay_path),
            hard_score=eval_report.hard_score or HardScore(),
            judge_score=eval_report.judge_score or JudgeScore(),
            total_score=eval_report.total_score,
        )

    def _maybe_write_generated_code(self, task_input: str, final_answer: str) -> str | None:
        target_path = self._extract_target_path(task_input)
        if not target_path:
            return None

        code = self._extract_code_block(final_answer)
        if code is None:
            stripped = final_answer.strip()
            if not stripped or stripped.startswith("请"):
                return None
            code = stripped

        valid, validation_message = self._validate_generated_code(target_path, code)
        if not valid:
            self.logger.info("generated_code_rejected", path=target_path, reason=validation_message)
            return f"{target_path}（未写入：{validation_message}）"

        self.tool_runtime.guards.ensure_path_in_workspace(target_path)
        output_path = self.tool_runtime.guards.workspace_root / target_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")
        self.logger.info("generated_code_written", path=target_path)
        return target_path

    def _validate_generated_code(self, target_path: str, code: str) -> tuple[bool, str]:
        suffix = Path(target_path).suffix.lower()
        if suffix == ".py":
            try:
                ast.parse(code)
                return True, "ok"
            except SyntaxError as exc:
                return False, f"Python 语法错误：{exc.msg}"

        if suffix in {".cpp", ".cc", ".cxx", ".hpp", ".h", ".c"}:
            compiler = shutil.which("g++") or shutil.which("clang++") or shutil.which("gcc") or shutil.which("clang")
            if compiler:
                with tempfile.TemporaryDirectory() as tmpdir:
                    source_path = Path(tmpdir) / ("snippet" + (".c" if suffix == ".c" else ".cpp"))
                    source_path.write_text(code, encoding="utf-8")
                    args = [compiler, "-fsyntax-only"]
                    if suffix == ".c":
                        args.extend(["-x", "c"])
                    else:
                        args.extend(["-x", "c++"])
                    args.append(str(source_path))
                    proc = subprocess.run(args, capture_output=True, text=True, check=False)
                    if proc.returncode == 0:
                        return True, "ok"
                    detail = (proc.stderr or proc.stdout or "编译器校验失败").strip().splitlines()[:1]
                    return False, detail[0] if detail else "编译器校验失败"
            return self._basic_c_like_sanity_check(code)

        return True, "ok"

    def _basic_c_like_sanity_check(self, code: str) -> tuple[bool, str]:
        pairs = {"{": "}", "(": ")", "[": "]"}
        closing = {v: k for k, v in pairs.items()}
        stack: list[str] = []
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in closing:
                if not stack or stack[-1] != closing[char]:
                    return False, "括号不匹配"
                stack.pop()
        if stack:
            return False, "括号不平衡"
        if "main(" in code and ";" not in code:
            return False, "可能缺少分号"
        return True, "ok"

    def _extract_target_path(self, task_input: str) -> str | None:
        patterns = [
            r"(?:在|到|写入|修改|新建|创建)\s*([A-Za-z0-9_./\\-]+\.(?:cpp|cc|c|h|hpp|py|js|ts|java|go|rs|md|txt))",
            r"([A-Za-z0-9_./\\-]+\.(?:cpp|cc|c|h|hpp|py|js|ts|java|go|rs|md|txt))",
        ]
        for pattern in patterns:
            match = re.search(pattern, task_input)
            if match:
                return match.group(1)
        return None

    def _extract_code_block(self, text: str) -> str | None:
        match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", text, flags=re.DOTALL)
        if match:
            return match.group(1).strip() or None
        return None
