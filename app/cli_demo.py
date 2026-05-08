"""Stage 0 minimal HelloAgents demo (CLI)."""

from pathlib import Path
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _add_framework_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    framework_path = repo_root / "frameworks" / "HelloAgents"
    sys.path.insert(0, str(framework_path))


def main() -> None:
    _add_framework_to_path()

    if load_dotenv:
        load_dotenv()

    from hello_agents import HelloAgentsLLM, SimpleAgent

    llm = HelloAgentsLLM()
    agent = SimpleAgent("assistant", llm, enable_tool_calling=False)

    prompt = "请用一句话介绍 HelloAgents。"
    response = agent.run(prompt)
    print("\n--- Response ---")
    print(response)


if __name__ == "__main__":
    main()
