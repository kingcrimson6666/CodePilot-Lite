"""Safe write tool with confirmation flow."""

from pathlib import Path
from typing import Any, Dict, List
import difflib
import uuid

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.builtin import WriteTool


class SafeWriteTool(Tool):
    """Write files only after explicit confirmation."""

    def __init__(self, project_root: Path, registry=None):
        super().__init__(
            name="Write",
            description="Write files with preview and confirmation.",
            expandable=False,
        )
        self.project_root = project_root.resolve()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._writer = WriteTool(project_root=str(self.project_root), registry=registry)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to write (relative to project root)",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="File contents to write",
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
                description="Apply the pending write when true",
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
            return self._writer.run(
                {
                    "path": pending["path"],
                    "content": pending["content"],
                    "file_mtime_ms": pending.get("file_mtime_ms"),
                }
            )

        path = parameters.get("path")
        content = parameters.get("content")
        if not path or content is None:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="path and content are required",
            )

        diff = self._build_diff(path, content)
        pending_id = f"pw-{uuid.uuid4().hex[:8]}"
        self._pending[pending_id] = {
            "path": path,
            "content": content,
            "file_mtime_ms": parameters.get("file_mtime_ms"),
        }

        return ToolResponse.partial(
            text=f"Write preview generated for {path}.\n\n{diff}",
            data={
                "pending_id": pending_id,
                "path": path,
                "confirm_hint": f"confirm {pending_id}",
            },
        )

    def _build_diff(self, path: str, content: str) -> str:
        file_path = self._resolve_path(path)
        if file_path.exists() and file_path.is_file():
            original = file_path.read_text(encoding="utf-8").splitlines()
        else:
            original = []
        updated = content.splitlines()
        diff = difflib.unified_diff(
            original,
            updated,
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
        return "\n".join(diff) or "(no changes)"

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()