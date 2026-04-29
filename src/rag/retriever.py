from __future__ import annotations

from src.rag.reranker import rerank
from src.rag.vector_store import InMemoryVectorStore


class RAGRetriever:
    def __init__(self, store: InMemoryVectorStore) -> None:
        self.store = store

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        chunks = self.store.search_hybrid(query, k_sparse=top_k, k_dense=top_k)
        ranked = rerank(chunks, query)
        return [self._format_chunk(c) for c in ranked[:top_k]]

    def sparse_retrieve(self, query: str, top_k: int = 5) -> list[str]:
        chunks = self.store.search_sparse(query, top_k=top_k)
        return [self._format_chunk(c) for c in chunks[:top_k]]

    def dense_retrieve(self, query: str, top_k: int = 5) -> list[str]:
        chunks = self.store.search_dense(query, top_k=top_k)
        return [self._format_chunk(c) for c in chunks[:top_k]]

    def hybrid_retrieve(self, query: str, k_sparse: int = 3, k_dense: int = 3) -> list[str]:
        chunks = self.store.search_hybrid(query, k_sparse=k_sparse, k_dense=k_dense)
        ranked = rerank(chunks, query)
        return [self._format_chunk(c) for c in ranked[: k_sparse + k_dense]]

    def _format_chunk(self, chunk) -> str:
        prefix = f"[{chunk.kind}] {chunk.path}#{chunk.chunk_index}"
        if chunk.symbol_hint:
            prefix += f" ({chunk.symbol_hint})"
        return f"{prefix}\n{chunk.content}"
