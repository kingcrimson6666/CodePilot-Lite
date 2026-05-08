"""Stage 1 CLI entry for the coding assistant."""

import argparse
from pathlib import Path
import sys
import asyncio

try:
    import readline
    readline.parse_and_bind('tab: complete')
except ImportError:
    pass

# Ensure the repo root is importable when running as a script.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.settings import init_environment
from app.agents.main_agent import build_agent
from app.commands import load_commands, parse_command
from hello_agents.core.streaming import StreamEventType


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI coding assistant CLI")
    parser.add_argument("-m", "--message", help="Single prompt to run")
    parser.add_argument(
        "--student",
        action="store_true",
        help="Enable guided mode without direct answers",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List saved sessions and exit",
    )
    parser.add_argument(
        "--load-session",
        help="Load a session file before running",
    )
    return parser


def _print_help(commands) -> None:
    print("\nAvailable commands:")
    for name in sorted(commands):
        spec = commands[name]
        usage = spec.usage or f"/{name}"
        description = spec.description or ""
        print(f"  {usage} - {description}")


def _run_command(agent, commands, text: str, echo_response: bool = False) -> bool:
    name, args = parse_command(text)
    if not name:
        return False

    if name in {"help", "?"}:
        _print_help(commands)
        return True

    if name not in commands:
        print(f"Unknown command: /{name}")
        _print_help(commands)
        return True

    spec = commands[name]
    if spec.requires_args and not args:
        print(f"Missing arguments for /{name}.")
        if spec.usage:
            print(f"Usage: {spec.usage}")
        if spec.arg_hint:
            print(f"Hint: {spec.arg_hint}")
        return True

    prompt_text = commands[name].render(args)

    response = agent.run(prompt_text)
    if echo_response:
        print("\n--- Response ---")
        print(response)
    return True


async def run_streaming_response(agent, user_input: str) -> str:
    """Run agent with streaming output."""
    final_result = ""
    async for event in agent.arun_stream(user_input):
        if event.type == StreamEventType.LLM_CHUNK:
            chunk = event.data.get("chunk", "")
            print(chunk, end="", flush=True)
        elif event.type == StreamEventType.AGENT_FINISH:
            pass
        elif event.type == StreamEventType.TOOL_CALL_FINISH:
            result = event.data.get("result", "")
            print(f"\n👀 {result}")
        elif event.type == StreamEventType.STEP_START:
            step = event.data.get("step", 0)
            max_steps = event.data.get("max_steps", 0)
            print(f"\n--- 第 {step}/{max_steps} 步 ---")
        elif event.type == StreamEventType.THINKING:
            thought = event.data.get("thought", "")
            if thought:
                print(f"\n💭 {thought}")
    print()
    return final_result


async def run_interactive_async(agent, commands) -> None:
    """Run interactive mode with streaming support."""
    print("AI coding assistant (type 'exit' to quit, /help for commands)")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break
            if _run_command(agent, commands, user_input):
                continue
            
            if user_input:
                await run_streaming_response(agent, user_input)
        except EOFError:
            print("\n检测到输入结束，退出程序...")
            break
        except Exception as e:
            print(f"\n❌ 输入处理错误: {e}")
            continue


async def main_async() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    init_environment()
    agent = build_agent(REPO_ROOT, student_mode=args.student)
    commands = load_commands(REPO_ROOT / "app" / "commands")

    if args.list_sessions:
        for session in agent.list_sessions():
            print(f"{session.get('filename')} - {session.get('saved_at')}")
        return

    if args.load_session:
        session_path = Path(args.load_session)
        if not session_path.is_absolute():
            session_path = REPO_ROOT / "storage" / "sessions" / session_path
        agent.load_session(str(session_path))

    if args.message:
        if not _run_command(agent, commands, args.message):
            await run_streaming_response(agent, args.message)
        return

    await run_interactive_async(agent, commands)


if __name__ == "__main__":
    asyncio.run(main_async())