"""Error parser tool."""

from typing import Any, Dict, List
import re

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class ErrorParserTool(Tool):
    """Parse Python tracebacks and return structured hints."""

    def __init__(self) -> None:
        super().__init__(
            name="ErrorParser",
            description="Parse traceback text and extract error details.",
            expandable=False,
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="traceback_text",
                type="string",
                description="Raw traceback text",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        tb_text = parameters.get("traceback_text")
        if not tb_text:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="Missing required parameter: traceback_text",
            )

        error_type, message = self._extract_error(tb_text)
        file_path, line_number = self._extract_location(tb_text)
        hints = self._build_hints(error_type, message)

        return ToolResponse.success(
            text="Parsed traceback",
            data={
                "error_type": error_type or "UnknownError",
                "message": message or "",
                "file": file_path or "",
                "line": line_number or 0,
                "hints": hints,
            },
        )

    def _extract_error(self, tb_text: str) -> tuple:
        lines = [line.strip() for line in tb_text.splitlines() if line.strip()]
        if not lines:
            return None, None
        last = lines[-1]
        if ":" in last:
            error_type, message = last.split(":", 1)
            return error_type.strip(), message.strip()
        return last, ""

    def _extract_location(self, tb_text: str) -> tuple:
        matches = re.findall(r"File \"([^\"]+)\", line (\d+)", tb_text)
        if not matches:
            return None, None
        file_path, line_number = matches[-1]
        try:
            return file_path, int(line_number)
        except ValueError:
            return file_path, None

    def _build_hints(self, error_type: str, message: str) -> List[str]:
        hints: List[str] = []
        if error_type == "ModuleNotFoundError":
            hints.append("Check whether the module is installed and import path is correct.")
        if error_type == "FileNotFoundError":
            hints.append("Verify the file path and ensure it exists.")
        if error_type == "KeyError":
            hints.append("Ensure the key exists before access, or use dict.get().")
        if error_type == "TypeError":
            hints.append("Check argument types and function signatures.")
        if error_type == "ValueError":
            hints.append("Validate input values before casting or parsing.")
        if not hints and message:
            hints.append("Review the stack trace context and inspect the failing line.")
        return hints
