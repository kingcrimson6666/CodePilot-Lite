"""Entrypoint detection tool."""

from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class EntryPointTool(Tool):
    """Locate likely entrypoints in the repository."""

    def __init__(self, project_root: Path):
        super().__init__(
            name="EntryPoint",
            description="Locate likely entrypoints such as CLI or main modules.",
            expandable=False,
        )
        self.project_root = project_root.resolve()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="root_path",
                type="string",
                description="Root path to scan (relative to project root)",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        root_path = parameters.get("root_path")
        if not root_path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="Missing required parameter: root_path",
            )

        root = self._resolve_root(root_path)
        if not root.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"Root path '{root_path}' does not exist",
            )

        entrypoints: List[str] = []
        reasoning: List[str] = []

        candidates = [
            root / "app" / "cli.py",
            root / "app" / "web.py",
            root / "main.py",
            root / "__main__.py",
        ]

        for candidate in candidates:
            if candidate.exists():
                entrypoints.append(str(candidate.relative_to(self.project_root)))
                reasoning.append(f"Found candidate file: {candidate.name}")

        for path in root.rglob("*.py"):
            if path.name in {"setup.py", "conftest.py"}:
                continue
            if self._has_main_guard(path):
                entrypoints.append(str(path.relative_to(self.project_root)))
                reasoning.append(f"Contains __main__ guard: {path.name}")

        entrypoints = sorted(set(entrypoints))

        return ToolResponse.success(
            text="Entrypoint scan complete",
            data={
                "entrypoints": entrypoints,
                "reasoning": "; ".join(reasoning),
            },
        )

    def _resolve_root(self, root_path: str) -> Path:
        path = Path(root_path)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def _has_main_guard(self, path: Path) -> bool:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return False
        return "if __name__ == \"__main__\"" in content
