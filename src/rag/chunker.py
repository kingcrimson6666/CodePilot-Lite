from __future__ import annotations

from pathlib import Path
import re


def _fixed_chunks(text: str, max_chars: int) -> list[str]:
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def _chunk_markdown(text: str, max_chars: int) -> list[str]:
    sections = re.split(r"(?m)^#{1,6}\s+", text)
    chunks = [s.strip() for s in sections if s.strip()]
    out: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
        else:
            out.extend(_fixed_chunks(chunk, max_chars))
    return out or _fixed_chunks(text, max_chars)


def _chunk_python(text: str, max_chars: int) -> list[str]:
    # Split on top-level class/function declarations to preserve symbol context.
    blocks = re.split(r"(?m)^(?=class\s+|def\s+)", text)
    chunks = [b.strip() for b in blocks if b.strip()]
    out: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
        else:
            out.extend(_fixed_chunks(chunk, max_chars))
    return out or _fixed_chunks(text, max_chars)


def chunk_file(path: Path, max_chars: int = 1200) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    suffix = path.suffix.lower()
    if suffix == ".md":
        return _chunk_markdown(text, max_chars)
    if suffix == ".py":
        return _chunk_python(text, max_chars)
    return _fixed_chunks(text, max_chars)
