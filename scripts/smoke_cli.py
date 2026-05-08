"""Run a CLI smoke test (requires LLM env vars)."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.settings import init_environment
from app.agents.main_agent import build_agent


def main() -> None:
    init_environment()
    agent = build_agent(REPO_ROOT)
    response = agent.run("Hello")
    print(response)


if __name__ == "__main__":
    main()
