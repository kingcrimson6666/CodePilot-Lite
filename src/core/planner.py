from __future__ import annotations

from src.models.output_schema import Plan, PlanStep


class Planner:
    def build_plan(self, task_input: str) -> Plan:
        return Plan(
            goal=task_input,
            steps=[
                PlanStep(id=1, title="Gather repository evidence"),
                PlanStep(id=2, title="Produce actionable response"),
            ],
        )

    def update_plan(self, plan: Plan, observation: str) -> Plan:
        if "tool_ok" in observation and plan.steps:
            for step in plan.steps:
                if not step.done:
                    step.done = True
                    break
        return plan

    def current_step(self, plan: Plan) -> PlanStep | None:
        for step in plan.steps:
            if not step.done:
                return step
        return None
