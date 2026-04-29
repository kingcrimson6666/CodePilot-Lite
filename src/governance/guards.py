from __future__ import annotations

from pathlib import Path


class SecurityGuards:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def ensure_path_in_workspace(self, candidate: str | None) -> None:
        if not candidate:
            return
        target = (self.workspace_root / candidate).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Path escapes workspace: {candidate}")

    def block_dangerous_command(self, args: dict) -> None:
        text = " ".join(str(v) for v in args.values()).lower()
        banned = ["rm -rf", "shutdown", "reboot", "mkfs", "dd if="]
        if any(x in text for x in banned):
            raise PermissionError("Dangerous command pattern detected.")
