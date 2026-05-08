"""Main agent factory for stage 1."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_ROOT = REPO_ROOT / "frameworks" / "HelloAgents"
sys.path.insert(0, str(FRAMEWORK_ROOT))

from hello_agents import HelloAgentsLLM, ReActAgent
from hello_agents.core.config import Config
from hello_agents.tools import ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, EditTool

from app.tools import (
    ProjectTreeTool,
    DependencyTool,
    EntryPointTool,
    FileSummaryTool,
    ErrorParserTool,
    BugFixTool,
    CommandTool,
)


def build_agent(repo_root: Path, student_mode: bool = False) -> ReActAgent:
    """Create the primary ReAct agent with file tools enabled."""
    llm = HelloAgentsLLM()

    config = Config(
        trace_enabled=True,
        trace_dir=str(repo_root / "storage" / "traces"),
        session_enabled=True,
        session_dir=str(repo_root / "storage" / "sessions"),
        skills_enabled=True,
        skills_dir=str(repo_root / "app" / "skills"),
    )

    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root=str(repo_root), registry=registry))
    registry.register_tool(WriteTool(project_root=str(repo_root), registry=registry))
    registry.register_tool(EditTool(project_root=str(repo_root), registry=registry))

    registry.register_tool(ProjectTreeTool(project_root=repo_root))
    registry.register_tool(DependencyTool(project_root=repo_root))
    registry.register_tool(EntryPointTool(project_root=repo_root))
    registry.register_tool(FileSummaryTool(project_root=repo_root))
    registry.register_tool(ErrorParserTool())
    registry.register_tool(BugFixTool(project_root=repo_root))
    registry.register_tool(CommandTool(project_root=repo_root))

    base_prompt = (
        "你可以直接写入或编辑文件，无需用户确认。"
        "当用户询问当前工作目录、仓库中的文件或类似的 shell 检查时，"
        "优先使用 Command 工具（如 'pwd', 'ls'）而不是 ProjectTree。"
        "避免重复调用相同的工具来回答问题；如果工具未能回答问题，"
        "请选择其他工具或请求澄清。如果上一步操作创建或编辑了文件，"
        "而用户没有指定文件名就请求后续更改，假设他们指的是最近创建/编辑的文件。"
        "如果用户要求修改特定文件，直接读取该文件而不是扫描整个仓库。"
        "读取一次文件后，除非需要新内容，否则不要重新读取，直接进行编辑。"
    )
    system_prompt = base_prompt
    if student_mode:
        system_prompt = (
            base_prompt
            + " 你还处于教学模式：先用提示和问题引导用户，"
            "除非用户明确要求，否则不要直接给出最终代码。"
        )

    agent = ReActAgent(
        name="assistant",
        llm=llm,
        tool_registry=registry,
        config=config,
        system_prompt=system_prompt,
        max_steps=8,
    )

    return agent
