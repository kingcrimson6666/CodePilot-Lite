"""Tests for command loading and parsing."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.commands.loader import load_commands, parse_command


def test_parse_command():
    name, args = parse_command("/explain app/cli.py")
    assert name == "explain"
    assert args == "app/cli.py"


def test_load_commands():
    commands = load_commands(REPO_ROOT / "app" / "commands")
    assert "explain" in commands
    assert commands["explain"].requires_args is True
    assert commands["overview"].requires_args is True
