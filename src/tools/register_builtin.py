from __future__ import annotations

from src.tools.builtin import apply_patch, git_diff, list_dir, read_file, run_tests, search_code, write_file
from src.tools.contracts import ToolSpec
from src.tools.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    registry.register(ToolSpec(name="list_dir", description="列出目录", required_args=["path"]), list_dir.run)
    registry.register(
        ToolSpec(name="read_file", description="读取文件行", required_args=["path"]),
        read_file.run,
    )
    registry.register(
        ToolSpec(name="search_code", description="搜索文本", required_args=["query"]),
        search_code.run,
    )
    registry.register(
        ToolSpec(name="write_file", description="写入文件内容", required_args=["path", "content"]),
        write_file.run,
    )
    registry.register(
        ToolSpec(
            name="apply_patch",
            description="字符串补丁替换",
            required_args=["path", "old_text", "new_text"],
        ),
        apply_patch.run,
    )
    registry.register(ToolSpec(name="run_tests", description="运行测试", required_args=[]), run_tests.run)
    registry.register(ToolSpec(name="git_diff", description="显示 git diff", required_args=[]), git_diff.run)
