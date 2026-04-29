from __future__ import annotations


def summarize_recent(events: str, max_lines: int = 10) -> str:
    lines = [line for line in events.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])
