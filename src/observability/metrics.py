from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metrics:
    tasks_total: int = 0
    tasks_passed: int = 0

    def record(self, passed: bool) -> None:
        self.tasks_total += 1
        if passed:
            self.tasks_passed += 1

    @property
    def tsr(self) -> float:
        if self.tasks_total == 0:
            return 0.0
        return self.tasks_passed / self.tasks_total
