"""项目依赖分析工具"""

from pathlib import Path
from typing import Any, Dict, List
import json

from hello_agents.tools import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class DependencyTool(Tool):
    """从常见清单文件汇总项目依赖"""

    def __init__(self, project_root: Path):
        super().__init__(
            name="Dependency",
            description="从清单文件汇总项目依赖",
            expandable=False,
        )
        self.project_root = project_root.resolve()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="root_path",
                type="string",
                description="要扫描的根路径（相对于项目根目录）",
                required=True,
            ),
            ToolParameter(
                name="include_dev",
                type="boolean",
                description="包含开发依赖",
                required=False,
                default=False,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        root_path = parameters.get("root_path")
        if not root_path:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="缺少必需参数：root_path",
            )

        include_dev = bool(parameters.get("include_dev", False))
        root = self._resolve_root(root_path)
        if not root.exists():
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"根路径 '{root_path}' 不存在",
            )

        python_deps: List[str] = []
        node_deps: List[str] = []
        notes: List[str] = []

        requirements = root / "requirements.txt"
        if requirements.exists():
            python_deps.extend(self._parse_requirements(requirements))
        else:
            notes.append("未找到 requirements.txt")

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            pyproject_deps = self._parse_pyproject(pyproject, include_dev)
            python_deps.extend(pyproject_deps)
        else:
            notes.append("未找到 pyproject.toml")

        package_json = root / "package.json"
        if package_json.exists():
            node_deps.extend(self._parse_package_json(package_json, include_dev))
        else:
            notes.append("未找到 package.json")

        python_deps = sorted(set(python_deps))
        node_deps = sorted(set(node_deps))

        return ToolResponse.success(
            text="依赖摘要已提取",
            data={
                "python": python_deps,
                "node": node_deps,
                "notes": "; ".join(notes) if notes else "",
            },
        )

    def _resolve_root(self, root_path: str) -> Path:
        path = Path(root_path)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def _parse_requirements(self, path: Path) -> List[str]:
        deps: List[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            deps.append(cleaned)
        return deps

    def _parse_pyproject(self, path: Path, include_dev: bool) -> List[str]:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return []

        data = tomllib.loads(path.read_text(encoding="utf-8"))
        deps: List[str] = []

        project = data.get("project", {})
        deps.extend(project.get("dependencies", []) or [])
        if include_dev:
            optional = project.get("optional-dependencies", {}) or {}
            for items in optional.values():
                deps.extend(items)

        return deps

    def _parse_package_json(self, path: Path, include_dev: bool) -> List[str]:
        data = json.loads(path.read_text(encoding="utf-8"))
        deps = list((data.get("dependencies") or {}).keys())
        if include_dev:
            deps.extend((data.get("devDependencies") or {}).keys())
        return deps
