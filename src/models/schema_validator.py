from __future__ import annotations

from src.models.output_schema import Action, ActionType


class SchemaValidator:
    """Validate and normalize model action payloads."""

    @staticmethod
    def validate_action_payload(payload: dict) -> Action:
        action_type = payload.get("type", ActionType.final_answer.value)
        try:
            parsed_type = ActionType(action_type)
        except Exception:  # noqa: BLE001
            parsed_type = ActionType.final_answer

        args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        tool_name = payload.get("tool_name")
        response = payload.get("response")
        rationale = str(payload.get("rationale", ""))

        if parsed_type == ActionType.tool_call and not tool_name:
            parsed_type = ActionType.final_answer
            response = response or "Model output invalid tool call payload; fallback to final answer."

        return Action(
            type=parsed_type,
            tool_name=tool_name,
            args=args,
            response=response,
            rationale=rationale,
        )
