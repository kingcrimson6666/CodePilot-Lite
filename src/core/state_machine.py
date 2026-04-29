from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    initialized = "initialized"
    running = "running"
    evaluating = "evaluating"
    completed = "completed"
    failed = "failed"
