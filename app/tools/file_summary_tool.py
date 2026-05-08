"""File summary tool."""

from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class FileSummaryTool(Tool):
    """Summarize a single source file."""

    def __init__(self, project_root: Path):
        super().__init__(
            name="FileSummary",
            description="Summarize a file with functions and classes listed.",
            expandable=False,
        )
        self.project_root = project_root.resolve()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="File path to summarize (relative to project root)",
                required=True,
            ),
            ToolParameter(
                name="max_lines",
                type="integer",
                description="Maximum number of lines to read",
                required=False,
                default=400,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        path = parameters.get("path")
        if not path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="Missing required parameter: path",
            )

        max_lines = int(parameters.get("max_lines", 400))
        file_path = self._resolve_path(path)
        if not file_path.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"File '{path}' does not exist",
            )
        if file_path.is_dir():
            return ToolResponse.error(
                code=ToolErrorCode.IS_DIRECTORY,
                message=f"Path '{path}' is a directory",
            )

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"Failed to read file: {exc}",
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
