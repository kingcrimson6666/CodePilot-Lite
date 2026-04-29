from __future__ import annotations

from pathlib import PurePosixPath

from src.models.output_schema import RiskLevel


class PolicyEngine:
    def classify_risk(self, task: str, action_name: str) -> RiskLevel:
        lower = f"{task} {action_name}".lower()
        if any(name in lower for name in ["delete", "apply_patch", "write_file"]):
            return RiskLevel.high
        if "git_diff" in lower:
            return RiskLevel.medium
        if "run_tests" in lower or "search" in lower or "read_file" in lower or "list_dir" in lower:
            return RiskLevel.low
        return RiskLevel.low

    def should_require_approval(self, risk: RiskLevel, action_name: str) -> bool:
        return risk == RiskLevel.high

    def apply_constraints(self, tool_name: str, args: dict) -> dict:
        safe = dict(args)

        if "path" in safe and isinstance(safe["path"], str):
            raw = safe["path"].strip() or "."
            normalized = PurePosixPath(raw).as_posix()
            if normalized.startswith(".git"):
                raise PermissionError("Path under .git is protected by policy.")
            safe["path"] = normalized

        if tool_name == "search_code" and "query" in safe and isinstance(safe["query"], str):
            safe["query"] = safe["query"].strip()[:200]

        if tool_name == "run_tests":
            path = safe.get("path", ".")
            if not isinstance(path, str):
                path = "."
            safe["path"] = path.strip() or "."

        return safe
