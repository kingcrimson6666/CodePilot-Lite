from __future__ import annotations

from pathlib import Path

from src.models.output_schema import ToolResult


def run(query: str, path: str = ".", max_results: int = 20) -> ToolResult:
    try:
        matches: list[str] = []
        root = Path(path)
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in {".py", ".md", ".txt", ".yaml", ".yml", ".toml"}:
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                continue
            if query.lower() in content.lower():
                matches.append(str(file_path))
            if len(matches) >= max_results:
                break
        return ToolResult(ok=True, stdout="\n".join(matches), data={"count": len(matches)})
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
