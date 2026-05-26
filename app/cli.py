"""AI 编程助手 CLI 入口（第一阶段）"""

import argparse
from pathlib import Path
import sys
import asyncio

try:
    import readline
    readline.parse_and_bind('tab: complete')
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.settings import init_environment
from app.agents.main_agent import build_agent
from app.commands import load_commands, parse_command
from hello_agents.core.streaming import StreamEventType
from hello_agents.core.lifecycle import AgentEvent


async def on_agent_start(event: AgentEvent) -> None:
    """Agent 开始执行时触发"""
    user_input = event.data.get("input_text", "")
    print(f"\n🚀 [{event.agent_name}] 开始执行")
    if len(user_input) > 50:
        print(f"   输入: {user_input[:50]}...")
    else:
        print(f"   输入: {user_input}")


async def on_step_start(event: AgentEvent) -> None:
    """推理步骤开始时触发"""
    step = event.data.get("step", 0)
    max_steps = event.data.get("max_steps", 0)
    print(f"\n📍 步骤 {step}/{max_steps} 开始")


async def on_tool_call(event: AgentEvent) -> None:
    """工具调用时触发"""
    tool_name = event.data.get("tool_name")
    args = event.data.get("args", {})
    args_str = str(args)[:100] if args else ""
    print(f"   🔧 调用工具: {tool_name}({args_str}...)")


async def on_agent_finish(event: AgentEvent) -> None:
    """Agent 执行完成时触发"""
    result = event.data.get("result", "")
    total_steps = event.data.get("total_steps", 0)
    total_tokens = event.data.get("total_tokens", 0)
    duration = event.data.get("duration_seconds", 0)

    print(f"\n✅ [{event.agent_name}] 执行完成")
    print(f"   总步骤: {total_steps}")
    print(f"   总 Token: {total_tokens}")
    print(f"   耗时: {duration:.2f}秒")


async def on_error(event: AgentEvent) -> None:
    """发生错误时触发"""
    error = event.data.get("error")
    error_type = event.data.get("error_type", "Unknown")
    step = event.data.get("step", 0)

    print(f"\n❌ 错误 (步骤 {step}): {error_type}")
    print(f"   {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 编程助手命令行界面")
    parser.add_argument("-m", "--message", help="要执行的单条提示消息")
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="列出已保存的会话并退出",
    )
    parser.add_argument(
        "--load-session",
        help="运行前加载会话文件",
    )
    return parser


def _print_help(commands) -> None:
    print("\n可用命令：")
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
        print(f"未知命令：/{name}")
        _print_help(commands)
        return True

    spec = commands[name]
    if spec.requires_args and not args:
        print(f"/{name} 缺少参数。")
        if spec.usage:
            print(f"用法：{spec.usage}")
        if spec.arg_hint:
            print(f"提示：{spec.arg_hint}")
        return True

    prompt_text = commands[name].render(args)

    response = agent.run(prompt_text)
    if echo_response:
        print("\n--- 响应 ---")
        print(response)
    return True


async def run_streaming_response(agent, user_input: str) -> str:
    """使用流式输出运行代理（带生命周期钩子）"""
    final_result = ""
    try:
        async for event in agent.arun_stream(
            user_input,
            on_start=on_agent_start,
            on_step=on_step_start,
            on_tool_call=on_tool_call,
            on_finish=on_agent_finish,
            on_error=on_error
        ):
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
    except Exception as e:
        print(f"\n❌ 执行错误：{e}")
    print()
    return final_result


async def run_interactive_async(agent, commands) -> None:
    """运行带流式支持的交互模式"""
    print("AI 编程助手（输入 'exit' 退出，输入 /help 查看命令）")

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
            print(f"\n❌ 输入处理错误：{e}")
            continue


async def main_async() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    init_environment()
    agent = build_agent(REPO_ROOT)
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
