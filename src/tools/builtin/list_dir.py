from __future__ import annotations

from pathlib import Path

from src.models.output_schema import ToolResult


def run(path: str = ".") -> ToolResult:
    try:
        items = sorted(p.name + ("/" if p.is_dir() else "") for p in Path(path).iterdir())
        return ToolResult(ok=True, stdout="\n".join(items), data={"count": len(items)})
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
