"""带安全检查的文件读取工具"""

from pathlib import Path
from typing import Any, Dict, List
import logging

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.builtin import ReadTool

from app.tools.path_safety import is_safe_path, get_safe_path

logger = logging.getLogger(__name__)


class SafeReadTool(Tool):
    """Read files with path safety checks."""

    def __init__(self, project_root: Path, registry=None):
        super().__init__(
            name="Read",
            description="Read file contents with path safety checks.",
            expandable=False,
        )
        self.project_root = project_root.resolve()
        self._reader = ReadTool(project_root=str(self.project_root), registry=registry)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to read (relative to project root)",
                required=True,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        path = parameters.get("path")
        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="path is required",
            )

        # 检查路径安全性
        if not is_safe_path(path, self.project_root):
            logger.warning(f"拒绝访问不安全路径: {path}")
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"路径 '{path}' 不在安全范围内",
            )

        logger.info(f"读取文件: {path}")
        return self._reader.run(parameters)
