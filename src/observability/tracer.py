from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tracer:
    events: list[dict] = field(default_factory=list)

    def add(self, event: dict) -> None:
        self.events.append(event)
