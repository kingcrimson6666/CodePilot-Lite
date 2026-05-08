"""Project tree tool."""

from pathlib import Path
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class ProjectTreeTool(Tool):
    """Build a project tree with key files highlighted."""

    def __init__(self, project_root: Path):
        super().__init__(
            name="ProjectTree",
            description="Build a directory tree for the project with key files highlighted.",
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
            ),
            ToolParameter(
                name="max_depth",
                type="integer",
                description="Maximum depth to include",
                required=False,
                default=4,
            ),
            ToolParameter(
                name="ignore",
                type="array",
                description="Directory names to ignore",
                required=False,
                default=[],
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        root_path = parameters.get("root_path")
        if not root_path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="Missing required parameter: root_path",
            )

        max_depth = int(parameters.get("max_depth", 4))
        ignore = set(parameters.get("ignore") or [])
        ignore.update({".git", ".venv", "__pycache__", "storage"})

        root = self._resolve_root(root_path)
        if not root.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"Root path '{root_path}' does not exist",
            )

        tree_lines: List[str] = []
        key_files: List[str] = []
        total_files = 0

        for path in self._iter_paths(root, max_depth, ignore):
            rel_path = path.relative_to(root)
            depth = len(rel_path.parts)
            indent = "  " * depth
            if path.is_dir():
                tree_lines.append(f"{indent}{path.name}/")
            else:
                tree_lines.append(f"{indent}{path.name}")
                total_files += 1
                if self._is_key_file(path):
                    key_files.append(str(path.relative_to(self.project_root)))

        tree_text = "\n".join(tree_lines) if tree_lines else "(empty)"

        return ToolResponse.success(
            text=f"Project tree for {root_path} (depth <= {max_depth})",
            data={
                "tree": tree_text,
                "key_files": sorted(set(key_files)),
                "total_files": total_files,
            },
        )

    def _resolve_root(self, root_path: str) -> Path:
        path = Path(root_path)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def _iter_paths(self, root: Path, max_depth: int, ignore: set) -> List[Path]:
        paths: List[Path] = []
        for current_root, dirnames, filenames in os.walk(root):
            current_path = Path(current_root)
            rel_depth = len(current_path.relative_to(root).parts)
            if rel_depth > max_depth:
                dirnames[:] = []
                continue

            dirnames[:] = [d for d in dirnames if d not in ignore]
            for dirname in dirnames:
                paths.append(current_path / dirname)
            for filename in filenames:
                paths.append(current_path / filename)

        return sorted(paths)

    def _is_key_file(self, path: Path) -> bool:
        if path.name in {"README.md", "pyproject.toml", "requirements.txt"}:
            return True
        if path.name.endswith(".md") and "README" in path.name.upper():
            return True
        if path.suffix == ".py" and path.name in {"__main__.py", "main.py", "cli.py"}:
            return True
        return False


import os
