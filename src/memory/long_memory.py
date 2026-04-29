from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from src.memory.store import MemoryStore


class LongMemory:
    def __init__(self, root: Path) -> None:
        self.store = MemoryStore(root)

    def recall(self, query: str, top_k: int = 3, tags: list[str] | None = None) -> list[str]:
        file_path = self.store.long_file()
        if not file_path.exists():
            return []

        active = self._load_active_entries(file_path)
        query_tokens = [t for t in query.lower().split() if t]
        wanted_tags = {t.lower() for t in (tags or []) if t}

        def score(entry: dict) -> int:
            text = str(entry.get("text", "")).lower()
            entry_tags = {str(t).lower() for t in entry.get("tags", [])}
            token_hits = sum(1 for t in query_tokens if t in text)
            tag_hits = len(wanted_tags.intersection(entry_tags)) if wanted_tags else 0
            return token_hits * 2 + tag_hits

        ranked = sorted(active, key=score, reverse=True)
        hits = [str(entry.get("text", "")) for entry in ranked if score(entry) > 0]
        return hits[:top_k]

    def write(self, item: str, tags: list[str] | None = None, ttl_days: int = 30) -> None:
        file_path = self.store.long_file()
        created = datetime.now(timezone.utc)
        expires = created + timedelta(days=max(1, ttl_days))
        payload = {
            "text": item,
            "tags": [t for t in (tags or []) if t],
            "created_at": created.isoformat(),
            "expires_at": expires.isoformat(),
        }
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

        # Opportunistic cleanup keeps file bounded without extra cron jobs.
        self._cleanup_expired(file_path)

    def _cleanup_expired(self, file_path: Path) -> None:
        active = self._load_active_entries(file_path)
        with file_path.open("w", encoding="utf-8") as fh:
            for entry in active:
                if entry.get("_legacy"):
                    fh.write(str(entry.get("text", "")) + "\n")
                    continue
                out = dict(entry)
                out.pop("_legacy", None)
                fh.write(json.dumps(out, ensure_ascii=True) + "\n")

    def _load_active_entries(self, file_path: Path) -> list[dict]:
        now = datetime.now(timezone.utc)
        entries: list[dict] = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                entries.append({"text": text, "tags": [], "_legacy": True})
                continue

            if not isinstance(payload, dict):
                continue
            expires_at = payload.get("expires_at")
            if isinstance(expires_at, str):
                try:
                    exp = datetime.fromisoformat(expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < now:
                        continue
                except ValueError:
                    # Keep malformed legacy payloads instead of dropping data silently.
                    pass
            entries.append(payload)
        return entries
