"""带确认的安全文件编辑工具"""

from pathlib import Path
from typing import Any, Dict, List
import difflib
import uuid
import logging

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.builtin import EditTool

from app.tools.path_safety import is_safe_path, get_safe_path

logger = logging.getLogger(__name__)


class SafeEditTool(Tool):
    """Edit files only after explicit confirmation with path safety checks."""

    def __init__(self, project_root: Path, registry=None):
        super().__init__(
            name="Edit",
            description="Edit files with preview and confirmation.",
            expandable=False,
        )
        self.project_root = project_root.resolve()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._editor = EditTool(project_root=str(self.project_root), registry=registry)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to edit (relative to project root)",
                required=True,
            ),
            ToolParameter(
                name="old_string",
                type="string",
                description="Existing content to replace",
                required=True,
            ),
            ToolParameter(
                name="new_string",
                type="string",
                description="Replacement content",
                required=True,
            ),
            ToolParameter(
                name="file_mtime_ms",
                type="integer",
                description="Cached file mtime (optional)",
                required=False,
            ),
            ToolParameter(
                name="confirm",
                type="boolean",
                description="Apply the pending edit when true",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="pending_id",
                type="string",
                description="Pending change id returned from preview",
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
            logger.info(f"执行确认编辑: {pending['path']}")
            return self._editor.run(
                {
                    "path": pending["path"],
                    "old_string": pending["old_string"],
                    "new_string": pending["new_string"],
                    "file_mtime_ms": pending.get("file_mtime_ms"),
                }
            )

        path = parameters.get("path")
        old_string = parameters.get("old_string")
        new_string = parameters.get("new_string")
        if not path or old_string is None or new_string is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="path, old_string, and new_string are required",
            )

        # 检查路径安全性
        if not is_safe_path(path, self.project_root):
            logger.warning(f"拒绝访问不安全路径: {path}")
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"路径 '{path}' 不在安全范围内",
            )

        diff = self._build_diff(path, old_string, new_string)
        if diff is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="Cannot find old_string in file or file does not exist",
            )

        pending_id = f"pe-{uuid.uuid4().hex[:8]}"
        self._pending[pending_id] = {
            "path": path,
            "old_string": old_string,
            "new_string": new_string,
            "file_mtime_ms": parameters.get("file_mtime_ms"),
        }

        return ToolResponse.partial(
            text=f"Edit preview generated for {path}.\n\n{diff}",
            data={
                "pending_id": pending_id,
                "path": path,
                "confirm_hint": f"confirm {pending_id}",
            },
        )

    def _build_diff(self, path: str, old_string: str, new_string: str) -> str | None:
        file_path = self._resolve_path(path)
        if not file_path.exists() or not file_path.is_file():
            return None
        content = file_path.read_text(encoding="utf-8")
        if content.count(old_string) != 1:
            return None
        updated = content.replace(old_string, new_string)
        diff = difflib.unified_diff(
            content.splitlines(),
            updated.splitlines(),
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
        return "\n".join(diff) or "(no changes)"

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.project_root / candidate).resolve()
