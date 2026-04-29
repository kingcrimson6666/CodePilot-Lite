from __future__ import annotations

from pydantic import BaseModel


class Observation(BaseModel):
    kind: str
    message: str
