from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ActionType(str, Enum):
    tool_call = "tool_call"
    final_answer = "final_answer"


class PlanStep(BaseModel):
    id: int
    title: str
    done: bool = False


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class Action(BaseModel):
    type: ActionType
    tool_name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
    rationale: str = ""


class ToolResult(BaseModel):
    ok: bool
    stdout: str = ""
    stderr: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


class HardScore(BaseModel):
    tests_passed: float = 0.0
    constraints_ok: float = 0.0


class JudgeScore(BaseModel):
    coverage: float = 0.0
    readability: float = 0.0
    risk_awareness: float = 0.0
    explanation: float = 0.0


class TotalScore(BaseModel):
    hard: float
    judge: float
    total: float
    passed: bool


class TaskResult(BaseModel):
    task_id: str = ""
    session_id: str = ""
    task: str
    final_answer: str
    tool_history: list[str] = Field(default_factory=list)
    pending_approval_tickets: list[str] = Field(default_factory=list)
    replay_path: str = ""
    hard_score: HardScore
    judge_score: JudgeScore
    total_score: TotalScore
