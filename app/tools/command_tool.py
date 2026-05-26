"""带确认和白名单的命令执行工具（含安全沙箱）"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import shlex
import subprocess
import time
import uuid
import os
import logging

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode

from app.tools.path_safety import is_safe_path, get_safe_path

# 设置日志
logger = logging.getLogger(__name__)


class CommandTool(Tool):
    """执行白名单中的命令，需要显式确认，带资源限制"""

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

    # 资源限制配置
    RESOURCE_LIMITS = {
        "cpu_seconds": 10,  # CPU时间限制（秒）
        "memory_bytes": 512 * 1024 * 1024,  # 内存限制（512MB）
        "file_size_bytes": 10 * 1024 * 1024,  # 最大文件大小（10MB）
    }

    def __init__(self, project_root: Path, allowlist: List[str] | None = None):
        super().__init__(
            name="Command",
            description="执行白名单中的系统命令，需要确认",
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
                description="要执行的命令（不使用 shell）。",
                required=True,
            ),
            ToolParameter(
                name="timeout_seconds",
                type="integer",
                description="超时时间（秒），默认为 300。",
                required=False,
                default=300,
            ),
            ToolParameter(
                name="confirm",
                type="boolean",
                description="为 true 时应用待执行的命令",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="pending_id",
                type="string",
                description="预览返回的待执行命令 ID",
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
                        message="确认需要 pending_id",
                    )
            if pending_id not in self._pending:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="无效的 pending_id",
                )
            pending = self._pending.pop(pending_id)
            logger.info(f"执行确认命令: {pending['command']}")
            return self._execute(pending["command"], pending["timeout_seconds"])

        command = parameters.get("command")
        if not command:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="需要 command 参数",
            )

        parsed = self._parse_command(command)
        if isinstance(parsed, ToolResponse):
            return parsed

        if not self._requires_confirmation(parsed):
            logger.info(f"执行自动批准命令: {command}")
            return self._execute(command, int(parameters.get("timeout_seconds", 300)))

        pending_id = f"pc-{uuid.uuid4().hex[:8]}"
        timeout_seconds = int(parameters.get("timeout_seconds", 300))
        self._pending[pending_id] = {
            "command": command,
            "timeout_seconds": timeout_seconds,
        }

        return ToolResponse.partial(
            text="已生成命令预览。请在执行前询问用户确认。",
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
                message="命令包含不允许的 shell 操作符",
            )
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"命令解析错误：{exc}",
            )

        if not parts:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="命令为空",
            )

        exe = Path(parts[0]).name
        if exe not in self.allowlist:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"命令 '{exe}' 不在白名单中",
            )

        # 检查命令中涉及的路径是否安全
        path_validation = self._validate_command_paths(parts)
        if path_validation is not None:
            return path_validation

        validation = self._validate_command(parts)
        if validation is not None:
            return validation

        return parts

    def _validate_command_paths(self, parts: List[str]) -> ToolResponse | None:
        """验证命令中涉及的路径是否安全"""
        exe = Path(parts[0]).name

        # 对需要路径参数的命令进行检查
        path_param_commands = {
            "cat", "head", "tail", "grep", "rg", "find", "git", "python", "pytest",
            "ls", "stat", "du", "tree"
        }

        if exe not in path_param_commands:
            return None

        # 检查所有看起来像路径的参数
        for i, part in enumerate(parts[1:], start=1):
            if "/" in part or "\\" in part or part == ".":
                # 看起来像路径，检查安全性
                if not is_safe_path(part, self.project_root):
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"命令参数 '{part}' 指向不安全的路径",
                    )

        return None

    def _validate_command(self, parts: List[str]) -> ToolResponse | None:
        exe = Path(parts[0]).name
        if exe == "git":
            if len(parts) < 2:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="需要 git 子命令",
                )
            subcommand = parts[1]
            if subcommand not in self.GIT_ALLOWED_SUBCOMMANDS:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=(
                        f"git 子命令 '{subcommand}' 不允许；"
                        f"允许的子命令：{', '.join(sorted(self.GIT_ALLOWED_SUBCOMMANDS))}"
                    ),
                )
            return None

        if exe == "python":
            if len(parts) < 3 or parts[1] != "-m":
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="python 只允许使用 '-m <module>' 形式",
                )
            module = parts[2]
            if module not in self.PYTHON_ALLOWED_MODULES:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=(
                        f"python -m '{module}' 不允许；"
                        f"允许的模块：{', '.join(sorted(self.PYTHON_ALLOWED_MODULES))}"
                    ),
                )
            return None

        if exe == "find":
            for token in parts[1:]:
                if token in self.FIND_DENIED_TOKENS:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"find 选项 '{token}' 不允许",
                    )
                if token.startswith("-") and token not in self.FIND_ALLOWED_PREFIXES:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"find 选项 '{token}' 不允许",
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

    def _set_resource_limits(self) -> None:
        """设置子进程资源限制（仅在 Unix 系统上有效）"""
        try:
            # 尝试导入 resource 模块（仅 Unix）
            import resource

            # 限制 CPU 时间
            cpu_limit = (self.RESOURCE_LIMITS["cpu_seconds"], self.RESOURCE_LIMITS["cpu_seconds"])
            resource.setrlimit(resource.RLIMIT_CPU, cpu_limit)

            # 限制虚拟内存（地址空间）
            mem_limit = (self.RESOURCE_LIMITS["memory_bytes"], self.RESOURCE_LIMITS["memory_bytes"])
            resource.setrlimit(resource.RLIMIT_AS, mem_limit)

            # 限制最大文件大小
            file_limit = (self.RESOURCE_LIMITS["file_size_bytes"], self.RESOURCE_LIMITS["file_size_bytes"])
            resource.setrlimit(resource.RLIMIT_FSIZE, file_limit)

        except (ImportError, AttributeError):
            # 非 Unix 系统或某些限制不可用，忽略
            pass

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
                preexec_fn=self._set_resource_limits,  # 设置资源限制
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"命令超时: {command}")
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"命令在 {timeout_seconds} 秒后超时",
            )
        except Exception as exc:
            logger.error(f"命令执行失败: {command}, 错误: {exc}")
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"命令执行失败：{exc}",
            )

        elapsed_ms = int((time.time() - start_time) * 1000)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        output = stdout + ("\n" + stderr if stderr else "")
        preview = self._truncate_output(output)

        # 记录执行日志
        logger.info(f"命令执行完成: {command}, 退出码: {completed.returncode}, 耗时: {elapsed_ms}ms")

        return ToolResponse.success(
            text="命令已执行",
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
