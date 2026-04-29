from __future__ import annotations

from pathlib import Path

from src.models.output_schema import ToolResult


def run(path: str, content: str) -> ToolResult:
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, stdout=f"已写入 {path}")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
