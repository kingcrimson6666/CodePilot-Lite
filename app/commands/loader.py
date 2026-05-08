"""Command loader for markdown-based prompts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass
class CommandSpec:
    name: str
    description: str
    body: str
    usage: str = ""
    requires_args: bool = False
    arg_hint: str = ""

    def render(self, args: str) -> str:
        if not args:
            args = "(no arguments)"
        return self.body.replace("$ARGUMENTS", args)


def parse_command(text: str) -> Tuple[str, str]:
    """Parse /command and argument string."""
    text = text.strip()
    if not text.startswith("/"):
        return "", ""

    parts = text[1:].split(maxsplit=1)
    name = parts[0].strip()
    args = parts[1].strip() if len(parts) > 1 else ""
    return name, args


def load_commands(commands_dir: Path) -> Dict[str, CommandSpec]:
    """Load command specs from markdown files."""
    registry: Dict[str, CommandSpec] = {}

    for path in sorted(commands_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(content)
        meta = _parse_frontmatter(frontmatter)

        name = meta.get("name", path.stem).strip()
        description = meta.get("description", "").strip()
        usage = meta.get("usage", "").strip()
        requires_args = _parse_bool(meta.get("requires_args", "false"))
        arg_hint = meta.get("arg_hint", "").strip()
        body = body.strip() + "\n"

        registry[name] = CommandSpec(
            name=name,
            description=description,
            body=body,
            usage=usage,
            requires_args=requires_args,
            arg_hint=arg_hint,
        )

    return registry


def _split_frontmatter(content: str) -> Tuple[str, str]:
    if not content.startswith("---"):
        return "", content

    lines = content.splitlines()
    frontmatter_lines = []
    body_lines = []
    in_frontmatter = True

    for line in lines[1:]:
        if in_frontmatter and line.strip() == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            frontmatter_lines.append(line)
        else:
            body_lines.append(line)

    return "\n".join(frontmatter_lines), "\n".join(body_lines)


def _parse_frontmatter(frontmatter: str) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("\"").strip("'")
    return meta


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "1"}
