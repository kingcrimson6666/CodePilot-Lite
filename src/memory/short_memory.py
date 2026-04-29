from __future__ import annotations

from pathlib import Path

from src.memory.store import MemoryStore


class ShortMemory:
    def __init__(self, root: Path) -> None:
        self.store = MemoryStore(root)

    def read(self, session_id: str) -> str:
        file_path = self.store.short_file(session_id)
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")[-2000:]

    def write(self, session_id: str, event: str) -> None:
        file_path = self.store.short_file(session_id)
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(event + "\n")
