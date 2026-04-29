from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable
from uuid import uuid4


@dataclass
class ApprovalDecision:
    allowed: bool
    status: str
    ticket_id: str | None = None


class ApprovalGate:
    def __init__(
        self,
        log_path: Path,
        auto_approve_high_risk: bool = True,
        interactive_confirm: Callable[[str, str, dict], bool] | None = None,
    ) -> None:
        self.log_path = log_path
        self.auto_approve_high_risk = auto_approve_high_risk
        self.interactive_confirm = interactive_confirm
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def allow_decision(self, requires_approval: bool, tool_name: str = "", args: dict | None = None) -> ApprovalDecision:
        args = args or {}
        if not requires_approval:
            self._write_event(status="not_required", tool_name=tool_name, args=args)
            return ApprovalDecision(allowed=True, status="not_required")

        ticket_id = str(uuid4())
        if self.auto_approve_high_risk:
            self._write_event(status="auto_approved", tool_name=tool_name, args=args, ticket_id=ticket_id)
            return ApprovalDecision(allowed=True, status="auto_approved", ticket_id=ticket_id)

        if self.interactive_confirm is not None:
            confirmed = self.interactive_confirm(tool_name, ticket_id, args)
            if confirmed:
                self._write_event(status="interactive_approved", tool_name=tool_name, args=args, ticket_id=ticket_id)
                return ApprovalDecision(allowed=True, status="interactive_approved", ticket_id=ticket_id)
            else:
                self._write_event(status="interactive_rejected", tool_name=tool_name, args=args, ticket_id=ticket_id)
                return ApprovalDecision(allowed=False, status="interactive_rejected", ticket_id=ticket_id)

        self._write_event(status="pending", tool_name=tool_name, args=args, ticket_id=ticket_id)
        return ApprovalDecision(allowed=False, status="pending", ticket_id=ticket_id)

    def allow(self, requires_approval: bool, tool_name: str = "", args: dict | None = None) -> bool:
        decision = self.allow_decision(requires_approval=requires_approval, tool_name=tool_name, args=args)
        return decision.allowed

    def _write_event(self, status: str, tool_name: str, args: dict, ticket_id: str | None = None) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "tool_name": tool_name,
            "ticket_id": ticket_id,
            "args": args,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")

    def list_pending(self) -> list[dict]:
        events = self._read_events()
        if not events:
            return []

        latest_by_ticket: dict[str, dict] = {}
        for event in events:
            ticket_id = event.get("ticket_id")
            if not ticket_id:
                continue
            latest_by_ticket[ticket_id] = event

        pending = [evt for evt in latest_by_ticket.values() if evt.get("status") == "pending"]
        pending.sort(key=lambda e: e.get("timestamp", ""))
        return pending

    def decide(self, ticket_id: str, approve: bool, actor: str = "cli") -> ApprovalDecision:
        pending = {evt.get("ticket_id") for evt in self.list_pending()}
        if ticket_id not in pending:
            return ApprovalDecision(allowed=False, status="not_found", ticket_id=ticket_id)

        status = "approved" if approve else "rejected"
        self._write_event(
            status=status,
            tool_name="approval_decision",
            args={"actor": actor},
            ticket_id=ticket_id,
        )
        return ApprovalDecision(allowed=approve, status=status, ticket_id=ticket_id)

    def _read_events(self) -> list[dict]:
        if not self.log_path.exists():
            return []

        events: list[dict] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events
