from __future__ import annotations

import subprocess

from src.models.output_schema import ToolResult


def run(path: str = ".") -> ToolResult:
    try:
        proc = subprocess.run(
            ["git", "-C", path, "--no-pager", "diff"],
            check=False,
            capture_output=True,
            text=True,
        )
        return ToolResult(ok=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, stderr=str(exc))
