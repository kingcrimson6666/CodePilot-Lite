from __future__ import annotations

import subprocess
from pathlib import Path
import shutil

from src.models.output_schema import HardScore


class HardEvaluator:
    def __init__(self, workspace_root: Path, live_checks: bool = False, timeout_sec: int = 20) -> None:
        self.workspace_root = workspace_root
        self.live_checks = live_checks
        self.timeout_sec = timeout_sec

    def run(self, final_answer: str, tool_history: list[str]) -> HardScore:
        constraints_ok = self._constraints_score(final_answer=final_answer, tool_history=tool_history)

        if not self.live_checks:
            tests_passed = self._estimate_tests_passed(tool_history, final_answer)
            return HardScore(tests_passed=tests_passed, constraints_ok=constraints_ok)

        tests_passed = self._run_pytest_score()
        syntax_ok = self._run_compileall_score()
        lint_ok = self._run_lint_score()
        type_ok = self._run_type_score()
        constraints_ok = (constraints_ok + syntax_ok + lint_ok + type_ok) / 4
        return HardScore(tests_passed=tests_passed, constraints_ok=constraints_ok)

    def _constraints_score(self, final_answer: str, tool_history: list[str]) -> float:
        history = " ".join(tool_history).lower()
        if "blocked" in history:
            return 0.0
        if "failed" in history:
            return 0.5 if final_answer else 0.2
        if final_answer:
            return 1.0
        return 0.2

    def _estimate_tests_passed(self, tool_history: list[str], final_answer: str) -> float:
        if not tool_history:
            return 0.2 if final_answer else 0.0
        history = " ".join(tool_history).lower()
        if "blocked" in history:
            return 0.0
        if "failed" in history:
            return 0.4 if final_answer else 0.2
        all_ok = all("ok" in entry.lower() for entry in tool_history if "ok" in entry.lower() or "failed" in entry.lower())
        if all_ok and final_answer:
            return 0.85
        return 0.5

    def _run_pytest_score(self) -> float:
        proc = self._run_cmd(["pytest", "-q"])
        return 1.0 if proc is not None and proc.returncode == 0 else 0.0

    def _run_compileall_score(self) -> float:
        python_bin = shutil.which("python") or "python"
        proc = self._run_cmd([python_bin, "-m", "compileall", "-q", "src"])
        return 1.0 if proc is not None and proc.returncode == 0 else 0.0

    def _run_lint_score(self) -> float:
        if shutil.which("ruff"):
            proc = self._run_cmd(["ruff", "check", "."])
            return 1.0 if proc is not None and proc.returncode == 0 else 0.0
        if shutil.which("flake8"):
            proc = self._run_cmd(["flake8", "."])
            return 1.0 if proc is not None and proc.returncode == 0 else 0.0
        return 1.0

    def _run_type_score(self) -> float:
        if shutil.which("mypy"):
            proc = self._run_cmd(["mypy", "src"])
            return 1.0 if proc is not None and proc.returncode == 0 else 0.0
        if shutil.which("pyright"):
            proc = self._run_cmd(["pyright"])
            return 1.0 if proc is not None and proc.returncode == 0 else 0.0
        return 1.0

    def _run_cmd(self, cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                cmd,
                cwd=self.workspace_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
            )
        except Exception:  # noqa: BLE001
            return None
