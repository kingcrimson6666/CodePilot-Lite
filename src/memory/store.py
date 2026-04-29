from __future__ import annotations

from pathlib import Path


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.short_root = self.root / "short"
        self.long_root = self.root / "long"
        self.short_root.mkdir(parents=True, exist_ok=True)
        self.long_root.mkdir(parents=True, exist_ok=True)

    def short_file(self, session_id: str) -> Path:
        return self.short_root / f"{session_id}.log"

    def long_file(self) -> Path:
        return self.long_root / "knowledge.log"
