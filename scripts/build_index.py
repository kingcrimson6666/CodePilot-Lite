from __future__ import annotations

import argparse

from src.infra.config import AppSettings
from src.rag.factory import build_rag_store, ensure_rag_dirs
from src.rag.indexer import RAGIndexer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    settings = AppSettings()
    ensure_rag_dirs(settings)
    store = build_rag_store(settings)
    indexer = RAGIndexer(store)
    count = indexer.build_index(args.repo)
    print(f"Indexed chunks: {count}")


if __name__ == "__main__":
    main()
