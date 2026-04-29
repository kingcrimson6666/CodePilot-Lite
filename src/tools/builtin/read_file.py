from __future__ import annotations

from pathlib import Path

from src.models.output_schema import ToolResult


def run(path: str, start_line: int = 1, end_line: int = 200) -> ToolResult:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        total = len(lines)
        if total == 0:
            return ToolResult(ok=True, stdout="", data={"line_count": 0})
        start = max(start_line - 1, 0)
        end = min(end_line, total)
        if end <= start:
            end = start + 1
        chunk = lines[start:end]
        return ToolResult(ok=True, stdout="\n".join(chunk), data={"line_count": len(chunk)})
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
