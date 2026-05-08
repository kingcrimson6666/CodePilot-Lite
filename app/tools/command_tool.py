"""Command execution tool with confirmation and allowlist."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import shlex
import subprocess
import time
import uuid

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class CommandTool(Tool):
    """Execute allowlisted commands after explicit confirmation."""

    DEFAULT_ALLOWLIST = {
        "pwd",
        "ls",
        "cat",
        "head",
        "tail",
        "wc",
        "find",
        "rg",
        "grep",
        "git",
        "python",
        "pytest",
    }

    AUTO_APPROVE_EXECUTABLES = {
        "pwd",
        "ls",
        "cat",
        "head",
        "tail",
        "wc",
        "rg",
        "grep",
        "git",
        "find",
        "echo",
        "date",
        "whoami",
        "which",
        "stat",
        "du",
        "df",
        "tree",
    }

    GIT_ALLOWED_SUBCOMMANDS = {"status", "diff", "log", "show"}
    PYTHON_ALLOWED_MODULES = {"pytest", "unittest"}
    FIND_DENIED_TOKENS = {"-exec", "-ok", "-delete", "-quit", "-printf"}
    FIND_ALLOWED_PREFIXES = {"-name", "-maxdepth", "-type", "-path", "-print"}

    def __init__(self, project_root: Path, allowlist: List[str] | None = None):
        super().__init__(
            name="Command",
            description="Execute an allowlisted system command with confirmation.",
            expandable=False,
        )
        self.project_root = project_root.resolve()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self.allowlist = set(allowlist or self.DEFAULT_ALLOWLIST)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="Command to execute (no shell).",
                required=True,
            ),
            ToolParameter(
                name="timeout_seconds",
                type="integer",
                description="Timeout in seconds (default 300).",
                required=False,
                default=300,
            ),
            ToolParameter(
                name="confirm",
                type="boolean",
                description="Apply the pending command when true",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="pending_id",
                type="string",
                description="Pending id returned from preview",
                required=False,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        confirm = bool(parameters.get("confirm", False))
        if confirm:
            pending_id = parameters.get("pending_id")
            if not pending_id:
                if len(self._pending) == 1:
                    pending_id = next(iter(self._pending))
                else:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message="pending_id is required for confirmation",
                    )
            if pending_id not in self._pending:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="Invalid pending_id",
                )
            pending = self._pending.pop(pending_id)
            return self._execute(pending["command"], pending["timeout_seconds"])

        command = parameters.get("command")
        if not command:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="command is required",
            )

        parsed = self._parse_command(command)
        if isinstance(parsed, ToolResponse):
            return parsed

        if not self._requires_confirmation(parsed):
            return self._execute(command, int(parameters.get("timeout_seconds", 300)))

        pending_id = f"pc-{uuid.uuid4().hex[:8]}"
        timeout_seconds = int(parameters.get("timeout_seconds", 300))
        self._pending[pending_id] = {
            "command": command,
            "timeout_seconds": timeout_seconds,
        }

        return ToolResponse.partial(
            text="Command preview generated. Ask the user to confirm before executing.",
            data={
                "pending_id": pending_id,
                "command": command,
                "cwd": str(self.project_root),
                "allowlist": sorted(self.allowlist),
                "confirm_hint": f"confirm {pending_id}",
            },
        )

    def _parse_command(self, command: str) -> List[str] | ToolResponse:
        if any(token in command for token in ("|", ">", "<", "&&", "||", ";")):
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="command contains shell operators which are not allowed",
            )
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"command parse error: {exc}",
            )

        if not parts:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="command is empty",
            )

        exe = Path(parts[0]).name
        if exe not in self.allowlist:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"command '{exe}' is not in allowlist",
            )

        validation = self._validate_command(parts)
        if validation is not None:
            return validation

        return parts

    def _validate_command(self, parts: List[str]) -> ToolResponse | None:
        exe = Path(parts[0]).name
        if exe == "git":
            if len(parts) < 2:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="git subcommand is required",
                )
            subcommand = parts[1]
            if subcommand not in self.GIT_ALLOWED_SUBCOMMANDS:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=(
                        f"git subcommand '{subcommand}' is not allowed; "
                        f"allowed: {', '.join(sorted(self.GIT_ALLOWED_SUBCOMMANDS))}"
                    ),
                )
            return None

        if exe == "python":
            if len(parts) < 3 or parts[1] != "-m":
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="python is only allowed with '-m <module>'",
                )
            module = parts[2]
            if module not in self.PYTHON_ALLOWED_MODULES:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=(
                        f"python -m '{module}' is not allowed; "
                        f"allowed: {', '.join(sorted(self.PYTHON_ALLOWED_MODULES))}"
                    ),
                )
            return None

        if exe == "find":
            for token in parts[1:]:
                if token in self.FIND_DENIED_TOKENS:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"find option '{token}' is not allowed",
                    )
                if token.startswith("-") and token not in self.FIND_ALLOWED_PREFIXES:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"find option '{token}' is not allowed",
                    )
            return None

        if exe == "pytest":
            return None

        return None

    def _requires_confirmation(self, parts: List[str]) -> bool:
        exe = Path(parts[0]).name
        if exe == "python" or exe == "pytest":
            return True
        if exe == "git":
            return False
        return exe not in self.AUTO_APPROVE_EXECUTABLES

    def _execute(self, command: str, timeout_seconds: int) -> ToolResponse:
        parts = self._parse_command(command)
        if isinstance(parts, ToolResponse):
            return parts

        start_time = time.time()
        try:
            completed = subprocess.run(
                parts,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"command timed out after {timeout_seconds}s",
            )
        except Exception as exc:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"command execution failed: {exc}",
            )

        elapsed_ms = int((time.time() - start_time) * 1000)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        output = stdout + ("\n" + stderr if stderr else "")
        preview = self._truncate_output(output)

        return ToolResponse.success(
            text="Command executed",
            data={
                "command": command,
                "cwd": str(self.project_root),
                "exit_code": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "output_preview": preview,
            },
            stats={"time_ms": elapsed_ms},
        )

    def _truncate_output(self, output: str, limit: int = 4000) -> str:
        if len(output) <= limit:
            return output
        return output[:limit] + "\n...<truncated>"
