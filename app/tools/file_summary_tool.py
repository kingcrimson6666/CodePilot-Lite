"""文件摘要工具"""

from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class FileSummaryTool(Tool):
    """汇总单个源文件"""

    def __init__(self, project_root: Path):
        super().__init__(
            name="FileSummary",
            description="汇总文件，列出函数和类",
            expandable=False,
        )
        self.project_root = project_root.resolve()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="要汇总的文件路径（相对于项目根目录）",
                required=True,
            ),
            ToolParameter(
                name="max_lines",
                type="integer",
                description="要读取的最大行数",
                required=False,
                default=400,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        path = parameters.get("path")
        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数：path",
            )

        max_lines = int(parameters.get("max_lines", 400))
        file_path = self._resolve_path(path)
        if not file_path.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"文件 '{path}' 不存在",
            )
        if file_path.is_dir():
            return ToolResponse.error(
                code=ToolErrorCode.IS_DIRECTORY,
                message=f"路径 '{path}' 是一个目录",
            )

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"读取文件失败：{exc}",
            )

        limited = lines[:max_lines]
        content = "\n".join(limited)

        functions = self._extract_symbols(limited, "def ")
        classes = self._extract_symbols(limited, "class ")

        summary = (
            f"File: {path}\n"
            f"Lines read: {len(limited)} / {len(lines)}\n"
            f"Classes: {', '.join(classes) if classes else '(none)'}\n"
            f"Functions: {', '.join(functions) if functions else '(none)'}"
        )

        return ToolResponse.success(
            text=summary,
            data={
                "summary": summary,
                "functions": functions,
                "classes": classes,
                "content": content,
            },
        )

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()

    def _extract_symbols(self, lines: List[str], prefix: str) -> List[str]:
        symbols: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith(prefix):
                continue
            name = stripped[len(prefix):].split("(", 1)[0].split(":", 1)[0].strip()
            if name:
                symbols.append(name)
        return symbols
