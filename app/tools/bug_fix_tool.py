"""Bug 修复工具（仅补丁建议）"""

from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class BugFixTool(Tool):
    """建议修复补丁但不应用"""

    def __init__(self, project_root: Path):
        super().__init__(
            name="BugFix",
            description="为目标文件生成补丁建议",
            expandable=False,
        )
        self.project_root = project_root.resolve()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="target_file",
                type="string",
                description="要修补的目标文件",
                required=True,
            ),
            ToolParameter(
                name="context_snippet",
                type="string",
                description="相关代码片段或差异上下文",
                required=True,
            ),
            ToolParameter(
                name="fix_instructions",
                type="string",
                description="修复说明",
                required=True,
            ),
            ToolParameter(
                name="apply",
                type="boolean",
                description="是否应用修复（暂不支持）",
                required=False,
                default=False,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        target_file = parameters.get("target_file")
        context_snippet = parameters.get("context_snippet")
        fix_instructions = parameters.get("fix_instructions")

        if not target_file or not context_snippet or not fix_instructions:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="需要 target_file、context_snippet 和 fix_instructions 参数",
            )

        file_path = self._resolve_path(target_file)
        if not file_path.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"目标文件 '{target_file}' 不存在",
            )

        diff = self._build_placeholder_diff(target_file, context_snippet, fix_instructions)

        return ToolResponse.success(
            text="已生成补丁建议",
            data={
                "diff": diff,
                "applied": False,
                "notes": "补丁未应用。请查看并手动应用。",
            },
        )

    def _resolve_path(self, target_file: str) -> Path:
        path = Path(target_file)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def _build_placeholder_diff(self, target_file: str, snippet: str, instructions: str) -> str:
        return (
            f"*** Begin Patch\n"
            f"*** Update File: {target_file}\n"
            f"@@\n"
            f"- {snippet}\n"
            f"+ {instructions}\n"
            f"*** End Patch"
        )
