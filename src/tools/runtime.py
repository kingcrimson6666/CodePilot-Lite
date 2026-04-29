from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from src.governance.approval_gate import ApprovalGate
from src.governance.guards import SecurityGuards
from src.governance.policy_engine import PolicyEngine
from src.models.output_schema import ToolResult
from src.tools.registry import ToolRegistry


class ToolRuntime:
    def __init__(
        self,
        registry: ToolRegistry,
        workspace_root: Path,
        auto_approve_high_risk: bool = True,
        approval_log_path: Path | None = None,
        interactive_confirm: Callable[[str, str, dict], bool] | None = None,
    ) -> None:
        self.registry = registry
        self.guards = SecurityGuards(workspace_root)
        self.policy = PolicyEngine()
        self.approval = ApprovalGate(
            log_path=approval_log_path or Path("data/governance/approvals.jsonl"),
            auto_approve_high_risk=auto_approve_high_risk,
            interactive_confirm=interactive_confirm,
        )

    def execute(self, tool_name: str, args: dict) -> ToolResult:
        started = time.perf_counter()
        try:
            self.registry.validate(tool_name, args)
            self.guards.ensure_path_in_workspace(args.get("path"))
            self.guards.block_dangerous_command(args)

            risk = self.policy.classify_risk(task="", action_name=tool_name)
            decision = self.approval.allow_decision(
                self.policy.should_require_approval(risk, tool_name),
                tool_name=tool_name,
                args=args,
            )
            if not decision.allowed:
                return ToolResult(
                    ok=False,
                    stderr="操作被审批门阻止 (approval gate blocked).",
                    data={
                        "approval_status": decision.status,
                        "approval_ticket_id": decision.ticket_id or "",
                        "failure_category": "approval_blocked",
                    },
                )

            safe_args = self.policy.apply_constraints(tool_name, args)
            tool = self.registry.get(tool_name)
            result: ToolResult = tool(**safe_args)
            result.data["approval_status"] = decision.status
            if decision.ticket_id:
                result.data["approval_ticket_id"] = decision.ticket_id
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            return result
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                ok=False,
                stderr=str(exc),
                data={"failure_category": self._classify_failure(str(exc))},
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

    def execute_with_retry(self, tool_name: str, args: dict, retries: int = 1) -> ToolResult:
        last = ToolResult(ok=False, stderr="未知错误 (unknown)")
        for _ in range(retries + 1):
            last = self.execute(tool_name, args)
            if last.ok:
                return last
            if not self._is_retryable(last):
                break
        return last

    def _is_retryable(self, result: ToolResult) -> bool:
        category = str(result.data.get("failure_category", ""))
        if category in {"approval_blocked", "permission", "validation", "unknown_tool"}:
            return False
        text = (result.stderr or "").lower()
        if "approval gate" in text:
            return False
        if "missing args" in text or "unknown tool" in text or "缺少参数" in text or "未知工具" in text:
            return False
        if "permission" in text or "dangerous" in text:
            return False
        return True

    def _classify_failure(self, stderr: str) -> str:
        text = (stderr or "").lower()
        if "unknown tool" in text or "未知工具" in text:
            return "unknown_tool"
        if "missing args" in text or "missing" in text or "缺少参数" in text:
            return "validation"
        if "permission" in text or "dangerous" in text:
            return "permission"
        if "timeout" in text:
            return "timeout"
        return "transient"
