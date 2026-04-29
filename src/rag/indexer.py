from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from src.rag.chunker import chunk_file


ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".toml"}
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}


def _symbol_hint(text: str) -> str:
    match = re.search(r"(?m)^(class|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)", text)
    if not match:
        return ""
    return match.group(2)


class RAGIndexer:
    def __init__(self, store: Any) -> None:
        self.store = store

    def build_index(self, repo_path: str) -> int:
        if hasattr(self.store, "clear"):
            self.store.clear()
        elif hasattr(self.store, "items"):
            self.store.items.clear()
        count = 0
        root = Path(repo_path)
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            if any(part in IGNORED_DIRS for part in file_path.parts):
                continue

            kind = "code" if file_path.suffix.lower() == ".py" else "doc"
            for idx, chunk in enumerate(chunk_file(file_path)):
                self.store.upsert(
                    item_id=f"{file_path}:{idx}",
                    content=chunk,
                    path=str(file_path),
                    chunk_index=idx,
                    kind=kind,
                    symbol_hint=_symbol_hint(chunk),
                )
                count += 1
        return count
