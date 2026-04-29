from __future__ import annotations

import json
from pathlib import Path


def save_replay(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, ensure_ascii=True, indent=2), encoding="utf-8")
