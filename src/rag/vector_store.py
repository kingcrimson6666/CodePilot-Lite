from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import math
import re
from typing import Any


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if t]


def _char_ngrams(text: str, n: int = 3) -> Counter[str]:
    s = re.sub(r"\s+", " ", text.lower())
    if len(s) < n:
        return Counter({s: 1}) if s else Counter()
    return Counter(s[i : i + n] for i in range(len(s) - n + 1))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class ChunkRecord:
    item_id: str
    content: str
    path: str
    chunk_index: int
    kind: str = "text"
    symbol_hint: str = ""


class InMemoryVectorStore:
    def __init__(
        self,
        use_bm25: bool = True,
        use_embeddings: bool = False,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedder: Any | None = None,
    ) -> None:
        self.items: list[ChunkRecord] = []
        self.use_bm25 = use_bm25
        self.use_embeddings = use_embeddings
        self.embedding_model = embedding_model
        self._bm25: Any | None = None
        self._bm25_corpus: list[list[str]] = []
        self._embedder: Any | None = embedder
        self._item_embeddings: Any | None = None
        self._dirty = True

    def upsert(
        self,
        item_id: str,
        content: str,
        path: str,
        chunk_index: int,
        kind: str = "text",
        symbol_hint: str = "",
    ) -> None:
        self.items.append(
            ChunkRecord(
                item_id=item_id,
                content=content,
                path=path,
                chunk_index=chunk_index,
                kind=kind,
                symbol_hint=symbol_hint,
            )
        )
        self._dirty = True

    def all_chunks(self) -> list[ChunkRecord]:
        return list(self.items)

    def clear(self) -> None:
        self.items.clear()
        self._bm25 = None
        self._bm25_corpus = []
        self._item_embeddings = None
        self._dirty = True

    def search_sparse(self, query: str, top_k: int = 5) -> list[ChunkRecord]:
        if self.use_bm25:
            bm25_hits = self._search_sparse_bm25(query, top_k)
            if bm25_hits:
                return bm25_hits

        q_tokens = set(_tokenize(query))
        scored: list[tuple[float, ChunkRecord]] = []
        for item in self.items:
            tokens = set(_tokenize(item.content))
            if not tokens:
                continue
            overlap = len(q_tokens.intersection(tokens))
            score = overlap / max(1, len(q_tokens))
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def search_dense(self, query: str, top_k: int = 5) -> list[ChunkRecord]:
        if self.use_embeddings:
            emb_hits = self._search_dense_embeddings(query, top_k)
            if emb_hits:
                return emb_hits

        q_vec = _char_ngrams(query)
        scored: list[tuple[float, ChunkRecord]] = []
        for item in self.items:
            score = _cosine(q_vec, _char_ngrams(item.content))
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def search_hybrid(self, query: str, k_sparse: int = 3, k_dense: int = 3) -> list[ChunkRecord]:
        sparse = self.search_sparse(query, top_k=k_sparse)
        dense = self.search_dense(query, top_k=k_dense)
        seen: set[str] = set()
        merged: list[ChunkRecord] = []
        for item in [*sparse, *dense]:
            if item.item_id in seen:
                continue
            seen.add(item.item_id)
            merged.append(item)
        return merged

    def search(self, query: str, top_k: int = 5) -> list[str]:
        return [c.content for c in self.search_hybrid(query, k_sparse=top_k, k_dense=top_k)[:top_k]]

    def _search_sparse_bm25(self, query: str, top_k: int) -> list[ChunkRecord]:
        bm25 = self._ensure_bm25()
        if bm25 is None:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = bm25.get_scores(tokens)
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)
        return [self.items[i] for i, score in indexed[:top_k] if score > 0]

    def _search_dense_embeddings(self, query: str, top_k: int) -> list[ChunkRecord]:
        if not self.items:
            return []
        embedder = self._ensure_embedder()
        if embedder is None:
            return []

        try:
            import numpy as np
        except Exception:  # noqa: BLE001
            return []

        if self._item_embeddings is None or self._dirty:
            texts = [item.content for item in self.items]
            try:
                self._item_embeddings = embedder.encode(texts, normalize_embeddings=True)
                self._dirty = False
            except Exception:  # noqa: BLE001
                return []

        try:
            q_vec = embedder.encode([query], normalize_embeddings=True)[0]
            sims = np.dot(self._item_embeddings, q_vec)
            ranked_idx = np.argsort(-sims)[:top_k]
            return [self.items[int(i)] for i in ranked_idx if float(sims[int(i)]) > 0]
        except Exception:  # noqa: BLE001
            return []

    def _ensure_bm25(self):
        if self._bm25 is not None and not self._dirty:
            return self._bm25
        if not self.items:
            return None
        try:
            from rank_bm25 import BM25Okapi
        except Exception:  # noqa: BLE001
            return None

        self._bm25_corpus = [_tokenize(item.content) for item in self.items]
        self._bm25 = BM25Okapi(self._bm25_corpus)
        return self._bm25

    def _ensure_embedder(self):
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:  # noqa: BLE001
            return None

        try:
            self._embedder = SentenceTransformer(self.embedding_model)
            return self._embedder
        except Exception:  # noqa: BLE001
            return None
class ChromaVectorStore:
    """Persistent vector store backed by ChromaDB with in-memory metadata mirror."""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "codepilot_chunks",
        use_bm25: bool = True,
        use_embeddings: bool = False,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_function: Any | None = None,
        embedder: Any | None = None,
    ) -> None:
        self._memory = InMemoryVectorStore(
            use_bm25=use_bm25,
            use_embeddings=use_embeddings,
            embedding_model=embedding_model,
            embedder=embedder,
        )
        self._embedding_function = None
        try:
            import chromadb
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("chromadb is not available") from exc

        if use_embeddings and embedding_function is not None:
            self._embedding_function = embedding_function
        elif use_embeddings:
            try:
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

                self._embedding_function = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"failed to initialize embedding function for {embedding_model}") from exc

        self.client = chromadb.PersistentClient(path=persist_directory)
        collection_kwargs = {"name": collection_name}
        if self._embedding_function is not None:
            collection_kwargs["embedding_function"] = self._embedding_function
        self.collection = self.client.get_or_create_collection(**collection_kwargs)

    @property
    def items(self) -> list[ChunkRecord]:
        return self._memory.items

    def clear(self) -> None:
        self._memory.clear()
        existing = self.collection.get(include=[])
        ids = existing.get("ids", []) if isinstance(existing, dict) else []
        if ids:
            self.collection.delete(ids=ids)

    def upsert(
        self,
        item_id: str,
        content: str,
        path: str,
        chunk_index: int,
        kind: str = "text",
        symbol_hint: str = "",
    ) -> None:
        self._memory.upsert(
            item_id=item_id,
            content=content,
            path=path,
            chunk_index=chunk_index,
            kind=kind,
            symbol_hint=symbol_hint,
        )
        self.collection.upsert(
            ids=[item_id],
            documents=[content],
            metadatas=[
                {
                    "path": path,
                    "chunk_index": chunk_index,
                    "kind": kind,
                    "symbol_hint": symbol_hint,
                }
            ],
        )

    def all_chunks(self) -> list[ChunkRecord]:
        return self._memory.all_chunks()

    def search_sparse(self, query: str, top_k: int = 5) -> list[ChunkRecord]:
        return self._memory.search_sparse(query, top_k=top_k)

    def search_dense(self, query: str, top_k: int = 5) -> list[ChunkRecord]:
        # Prefer persisted dense search via Chroma and then map to chunk records.
        try:
            rows = self.collection.query(query_texts=[query], n_results=top_k)
            ids = rows.get("ids", [[]])[0]
            by_id = {item.item_id: item for item in self._memory.items}
            result = [by_id[item_id] for item_id in ids if item_id in by_id]
            if result:
                return result
        except Exception:  # noqa: BLE001
            pass
        return self._memory.search_dense(query, top_k=top_k)

    def search_hybrid(self, query: str, k_sparse: int = 3, k_dense: int = 3) -> list[ChunkRecord]:
        sparse = self.search_sparse(query, top_k=k_sparse)
        dense = self.search_dense(query, top_k=k_dense)
        seen: set[str] = set()
        merged: list[ChunkRecord] = []
        for item in [*sparse, *dense]:
            if item.item_id in seen:
                continue
            seen.add(item.item_id)
            merged.append(item)
        return merged

    def search(self, query: str, top_k: int = 5) -> list[str]:
        return [c.content for c in self.search_hybrid(query, k_sparse=top_k, k_dense=top_k)[:top_k]]
