from __future__ import annotations


def should_stop(step_count: int, max_steps: int) -> bool:
    return step_count >= max_steps
