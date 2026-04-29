from __future__ import annotations

import re


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def _content_of(item) -> str:
    return item.content if hasattr(item, "content") else str(item)


def rerank(chunks: list, query: str) -> list:
    query_tokens = _tokenize(query)

    def score(item) -> float:
        text = _content_of(item)
        tokens = _tokenize(text)
        overlap = len(query_tokens.intersection(tokens))
        exact = 1 if query.lower() in text.lower() else 0
        return overlap * 1.0 + exact * 2.0

    return sorted(chunks, key=score, reverse=True)
