from __future__ import annotations

from src.tools.contracts import ToolCallable, ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._tools: dict[str, ToolCallable] = {}

    def register(self, spec: ToolSpec, callable_obj: ToolCallable) -> None:
        self._specs[spec.name] = spec
        self._tools[spec.name] = callable_obj

    def get(self, tool_name: str) -> ToolCallable:
        if tool_name not in self._tools:
            raise KeyError(f"未知工具: {tool_name} (unknown tool)")
        return self._tools[tool_name]

    def validate(self, tool_name: str, args: dict) -> None:
        spec = self._specs.get(tool_name)
        if not spec:
            raise KeyError(f"未知工具规格: {tool_name} (unknown tool)")
        missing = [k for k in spec.required_args if k not in args]
        if missing:
            raise ValueError(f"缺少参数: {tool_name} {missing} (missing args)")
