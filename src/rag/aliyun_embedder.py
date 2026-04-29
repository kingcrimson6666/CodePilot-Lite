from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class AliyunEmbedderConfig:
    api_key: str
    base_url: str
    model: str
    dimensions: int | None = None


class AliyunOpenAIEmbedder:
    def __init__(self, config: AliyunEmbedderConfig) -> None:
        self._config = config
        self._client = None
        self._max_batch_size = 10

    def _batched(self, items: Sequence[str]) -> list[list[str]]:
        return [list(items[i : i + self._max_batch_size]) for i in range(0, len(items), self._max_batch_size)]

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        from openai import OpenAI

        self._client = OpenAI(api_key=self._config.api_key, base_url=self._config.base_url)
        return self._client

    def encode(self, texts: Sequence[str], normalize_embeddings: bool = True):
        client = self._ensure_client()
        vectors: list[list[float]] = []
        for batch in self._batched(texts):
            payload = {
                "model": self._config.model,
                "input": batch,
                "encoding_format": "float",
            }
            if self._config.dimensions is not None:
                payload["dimensions"] = int(self._config.dimensions)
            response = client.embeddings.create(**payload)
            vectors.extend([item.embedding for item in response.data])

        if not normalize_embeddings:
            return vectors

        try:
            import numpy as np
        except Exception:  # noqa: BLE001
            return vectors

        arr = np.array(vectors, dtype=float)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        arr = arr / norms
        return arr


class AliyunChromaEmbeddingFunction:
    def __init__(self, embedder: AliyunOpenAIEmbedder) -> None:
        self._embedder = embedder

    def __call__(self, input: Iterable[str]):
        return self._embedder.encode(list(input), normalize_embeddings=False)
