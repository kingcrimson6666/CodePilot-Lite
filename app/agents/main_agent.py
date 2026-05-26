"""第一阶段主代理工厂"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_ROOT = REPO_ROOT / "frameworks" / "HelloAgents"
sys.path.insert(0, str(FRAMEWORK_ROOT))

from hello_agents import HelloAgentsLLM, ReActAgent
from hello_agents.core.config import Config
from hello_agents.tools import ToolRegistry

from app.tools import (
    ProjectTreeTool,
    DependencyTool,
    EntryPointTool,
    FileSummaryTool,
    ErrorParserTool,
    BugFixTool,
    CommandTool,
    SafeReadTool,
    SafeWriteTool,
    SafeEditTool,
)


def build_tool_registry(repo_root: Path) -> ToolRegistry:
    """构建工具注册表（分组注册，带安全检查）"""
    registry = ToolRegistry()

    file_tools = [
        SafeReadTool(project_root=repo_root, registry=registry),
        SafeWriteTool(project_root=repo_root, registry=registry),
        SafeEditTool(project_root=repo_root, registry=registry),
    ]

    analysis_tools = [
        ProjectTreeTool(project_root=repo_root),
        DependencyTool(project_root=repo_root),
        EntryPointTool(project_root=repo_root),
        FileSummaryTool(project_root=repo_root),
    ]

    dev_tools = [
        ErrorParserTool(),
        BugFixTool(project_root=repo_root),
        CommandTool(project_root=repo_root),
    ]

    for tool in file_tools + analysis_tools + dev_tools:
        registry.register_tool(tool)

    return registry


def build_agent(repo_root: Path) -> ReActAgent:
    """创建启用文件工具的主 ReAct 代理"""
    llm = HelloAgentsLLM()

    config = Config(
        trace_enabled=True,
        trace_dir=str(repo_root / "storage" / "traces"),
        session_enabled=True,
        session_dir=str(repo_root / "storage" / "sessions"),
        skills_enabled=True,
        skills_dir=str(repo_root / "app" / "skills"),
        auto_save_enabled=True,
        auto_save_interval=5,
        min_retain_rounds=5,
        context_window=128000,
    )

    registry = build_tool_registry(repo_root)

    system_prompt = """你是一个具备推理和行动能力的 AI 编程助手。

## 工作流程
1. **Thought 工具**：分析问题，制定策略，记录推理过程。在需要思考时主动调用。
2. **业务工具**：根据任务需求调用合适的工具（Read/Write/Edit/Command 等）获取信息或执行操作。
3. **Finish 工具**：当有足够信息得出结论时，调用此工具返回最终答案。

## 工具使用规则
- 你可以直接写入或编辑文件，无需用户确认。
- 当用户询问当前工作目录、仓库中的文件或类似的 shell 检查时，优先使用 Command 工具（如 'pwd', 'ls'）而不是 ProjectTree。
- 避免重复调用相同的工具来回答问题；如果工具未能回答问题，请选择其他工具或请求澄清。
- 如果上一步操作创建或编辑了文件，而用户没有指定文件名就请求后续更改，假设他们指的是最近创建/编辑的文件。
- 如果用户要求修改特定文件，直接读取该文件而不是扫描整个仓库。
- 读取一次文件后，除非需要新内容，否则不要重新读取，直接进行编辑。

## 重要提醒
- 主动使用 Thought 工具记录推理过程，这有助于你更清晰地思考问题。
- 可以多次调用工具获取信息，逐步深入分析。
- 只有在确信有足够信息时才调用 Finish 工具返回答案。
"""

    agent = ReActAgent(
        name="assistant",
        llm=llm,
        tool_registry=registry,
        config=config,
        system_prompt=system_prompt,
        max_steps=8,
    )

    return agent
