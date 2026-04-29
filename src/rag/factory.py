from __future__ import annotations

from pathlib import Path

from src.infra.config import AppSettings
from src.rag.aliyun_embedder import AliyunChromaEmbeddingFunction, AliyunEmbedderConfig, AliyunOpenAIEmbedder
from src.rag.vector_store import ChromaVectorStore, InMemoryVectorStore


def _build_local_embedder(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(model_name)
    except Exception:
        return None


def _build_embedding_provider(settings: AppSettings):
    if not settings.rag_use_embeddings:
        return None, None

    provider = settings.rag_embedding_provider.lower().strip()
    if provider == "local":
        embedder = _build_local_embedder(settings.rag_embedding_model)
        return embedder, None
    if provider == "aliyun":
        api_key = settings.rag_embedding_api_key or settings.model_api_key
        if not api_key:
            raise ValueError("rag_embedding_api_key or model_api_key is required for aliyun embeddings")
        base_url = settings.rag_embedding_api_base or settings.model_api_base
        config = AliyunEmbedderConfig(
            api_key=api_key,
            base_url=base_url,
            model=settings.rag_embedding_model,
            dimensions=settings.rag_embedding_dimensions,
        )
        embedder = AliyunOpenAIEmbedder(config)
        return embedder, AliyunChromaEmbeddingFunction(embedder)

    raise ValueError(f"unknown embedding provider: {provider}")


def build_rag_store(settings: AppSettings):
    backend = settings.rag_backend.lower().strip()
    embedder, embedding_function = _build_embedding_provider(settings)
    if backend == "chroma":
        try:
            return ChromaVectorStore(
                persist_directory=str(settings.rag_chroma_path),
                collection_name=settings.rag_collection,
                use_bm25=settings.rag_use_bm25,
                use_embeddings=settings.rag_use_embeddings,
                embedding_model=settings.rag_embedding_model,
                embedding_function=embedding_function,
                embedder=embedder,
            )
        except Exception:  # noqa: BLE001
            # Safe fallback when Chroma is unavailable.
            return InMemoryVectorStore(
                use_bm25=settings.rag_use_bm25,
                use_embeddings=settings.rag_use_embeddings,
                embedding_model=settings.rag_embedding_model,
                embedder=embedder,
            )

    return InMemoryVectorStore(
        use_bm25=settings.rag_use_bm25,
        use_embeddings=settings.rag_use_embeddings,
        embedding_model=settings.rag_embedding_model,
        embedder=embedder,
    )


def ensure_rag_dirs(settings: AppSettings) -> None:
    Path(settings.rag_chroma_path).mkdir(parents=True, exist_ok=True)
