"""错误解析工具"""

from typing import Any, Dict, List
import re

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class ErrorParserTool(Tool):
    """解析 Python 异常堆栈并返回结构化提示"""

    def __init__(self) -> None:
        super().__init__(
            name="ErrorParser",
            description="解析异常堆栈文本并提取错误详情",
            expandable=False,
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="traceback_text",
                type="string",
                description="原始异常堆栈文本",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        tb_text = parameters.get("traceback_text")
        if not tb_text:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数：traceback_text",
            )

        error_type, message = self._extract_error(tb_text)
        file_path, line_number = self._extract_location(tb_text)
        hints = self._build_hints(error_type, message)

        return ToolResponse.success(
            text="已解析异常堆栈",
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
            hints.append("检查模块是否已安装以及导入路径是否正确。")
        if error_type == "FileNotFoundError":
            hints.append("验证文件路径并确保它存在。")
        if error_type == "KeyError":
            hints.append("访问前确保键存在，或使用 dict.get()。")
        if error_type == "TypeError":
            hints.append("检查参数类型和函数签名。")
        if error_type == "ValueError":
            hints.append("转换或解析前验证输入值。")
        if not hints and message:
            hints.append("查看堆栈跟踪上下文并检查失败的行。")
        return hints
