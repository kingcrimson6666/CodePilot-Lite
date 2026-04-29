from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    workspace_root: Path = Field(default=Path("."))
    log_level: str = Field(default="INFO")
    max_steps: int = Field(default=6)
    short_memory_summary_every_n: int = Field(default=3)
    model_provider: str = Field(default="stub")
    model_name: str = Field(default="gpt-4o-mini")
    judge_model_provider: str = Field(default="stub")
    judge_model_name: str = Field(default="gpt-4o-mini")
    model_api_key: str | None = Field(default=None)
    model_api_base: str | None = Field(default=None)
    live_hard_checks: bool = Field(default=False)
    command_timeout_sec: int = Field(default=20)
    auto_approve_high_risk: bool = Field(default=False)
    approval_log_path: Path = Field(default=Path("data/governance/approvals.jsonl"))
    rag_backend: str = Field(default="memory")
    rag_chroma_path: Path = Field(default=Path("data/rag/chroma"))
    rag_collection: str = Field(default="codepilot_chunks")
    rag_use_bm25: bool = Field(default=True)
    rag_use_embeddings: bool = Field(default=True)
    rag_embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    rag_embedding_provider: str = Field(default="local")
    rag_embedding_api_key: str | None = Field(default=None)
    rag_embedding_api_base: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    rag_embedding_dimensions: int | None = Field(default=None)
    metrics_db_path: Path = Field(default=Path("data/codepilot.sqlite"))

    model_config = SettingsConfigDict(
        env_prefix="CODEPILOT_",
        env_file=".env",
        extra="ignore",
    )
