from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    required_args: list[str] = field(default_factory=list)


ToolCallable = Any
