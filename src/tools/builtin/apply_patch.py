from __future__ import annotations

from pathlib import Path

from src.models.output_schema import ToolResult


def run(path: str, old_text: str, new_text: str) -> ToolResult:
    try:
        target = Path(path)
        content = target.read_text(encoding="utf-8")
        if old_text not in content:
            return ToolResult(ok=False, stderr="未找到 old_text")
        updated = content.replace(old_text, new_text, 1)
        target.write_text(updated, encoding="utf-8")
        return ToolResult(ok=True, stdout=f"已替换 {path}")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
