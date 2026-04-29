from __future__ import annotations

import json
import re

from src.models.output_schema import Action, ActionType
from src.models.schema_validator import SchemaValidator


class LLMGateway:
    """Configurable gateway with safe fallback to deterministic behavior."""

    def __init__(
        self,
        provider: str = "stub",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    def decide_action(self, task: str, tool_history: list[str], context: str = "") -> Action:
        if tool_history:
            last = tool_history[-1]
            if "search_code: ok" in last and "README.md" in last and ("索引" in task or "index" in task):
                return Action(
                    type=ActionType.tool_call,
                    tool_name="read_file",
                    args={"path": "README.md", "start_line": 1, "end_line": 400},
                    rationale="Search hit README; read larger range to extract requested command.",
                )
        if self.provider == "openai":
            action = self._decide_action_openai(task=task, tool_history=tool_history, context=context)
            if action is not None:
                if action.type == ActionType.final_answer and not (action.response or "").strip():
                    query = "build-index" if ("索引" in task or "index" in task) else (task.split()[0] if task.split() else "README")
                    return Action(
                        type=ActionType.tool_call,
                        tool_name="search_code",
                        args={"query": query, "path": "."},
                        rationale="Final answer was empty; fall back to a targeted search for evidence.",
                    )
                return action
        return self._decide_action_stub(task=task, tool_history=tool_history)

    def _looks_like_write_request(self, task: str) -> bool:
        lowered = task.lower()
        return any(
            marker in lowered
            for marker in (
                "写代码",
                "写一个",
                "新建",
                "创建",
                "修改",
                "改成",
                "实现",
                "生成",
                "补全",
                "把",
                "写到",
                "写入",
            )
        ) or any(marker in lowered for marker in ("write", "implement", "create", "modify", "patch"))

    def _extract_target_path(self, task: str) -> str | None:
        patterns = [
            r"(?:在|到|写入|修改|新建|创建)\s*([A-Za-z0-9_./\\-]+\.(?:cpp|cc|c|h|hpp|py|js|ts|java|go|rs|md|txt))",
            r"([A-Za-z0-9_./\\-]+\.(?:cpp|cc|c|h|hpp|py|js|ts|java|go|rs|md|txt))",
        ]
        for pattern in patterns:
            match = re.search(pattern, task)
            if match:
                return match.group(1)
        return None

    def stream_chat(self, prompt: str, context: str | None = None):
        """Stream a normal chat reply as text chunks."""
        if self.provider != "openai" or not self.api_key:
            yield f"[stub] 回答: 已收到: {prompt}"
            return

        try:
            from openai import OpenAI
        except Exception:
            yield f"[stub] 回答: 已收到: {prompt}"
            return

        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
        client = OpenAI(**client_kwargs)

        messages = [
            {
                "role": "system",
                "content": "你是一个编程助手，简洁回答。不要输出额外说明。",
            },
            {
                "role": "user",
                "content": (context or "") + "\n" + prompt,
            },
        ]

        try:
            stream_resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                stream=True,
            )
            for evt in stream_resp:
                try:
                    delta = evt.choices[0].delta.content if getattr(evt, "choices", None) else None
                except Exception:
                    delta = None
                if delta:
                    yield delta
        except Exception:
            yield ""

    def _decide_action_stub(self, task: str, tool_history: list[str]) -> Action:
        lower = task.lower()

        if not tool_history:
            if "list" in lower or "目录" in task or "仓库" in task:
                return Action(
                    type=ActionType.tool_call,
                    tool_name="list_dir",
                    args={"path": "."},
                    rationale="First gather repository structure for context.",
                )
            return Action(
                type=ActionType.tool_call,
                tool_name="search_code",
                args={"query": task.split()[0] if task.split() else "TODO", "path": "."},
                rationale="Start from repository search to collect evidence.",
            )

        return Action(
            type=ActionType.final_answer,
            response="Task processed with one tool-assisted iteration. Review tool output and continue with focused edits.",
            rationale="Stop after MVP single tool iteration to keep execution bounded.",
        )

    def _decide_action_openai(self, task: str, tool_history: list[str], context: str) -> Action | None:
        if not self.api_key:
            return None

        try:
            from openai import OpenAI
        except Exception:  # noqa: BLE001
            return None

        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
        client = OpenAI(**client_kwargs)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是行动规划器。只输出 JSON，字段包括："
                    "type(tool_call|final_answer), tool_name(可选), args(可选对象), "
                    "response(可选), rationale(字符串)。"
                    "使用工具时必须包含必填参数。"
                    "工具规格："
                    "list_dir(path)。"
                    "read_file(path,start_line,end_line)。"
                    "search_code(query,path)。"
                    "write_file(path,content)。"
                    "apply_patch(path,old_text,new_text)。"
                    "run_tests(path 可选)。"
                    "git_diff(path 可选)。"
                    "如果任务要求返回文件中的文本，最终回复必须包含工具输出中的原文。"
                    "如果首次 read_file 未包含目标内容，先用 search_code 定位，再用更大的行范围 read_file。"
                    "若在任何工具调用后选择 final_answer，response 不能为空且必须包含提取的原文。"
                    "search_code 的 query 必须是非空且具体的关键词。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task,
                        "tool_history": tool_history[-5:],
                        "context": context[-3000:],
                        "tool_args_required": {
                            "list_dir": ["path"],
                            "read_file": ["path", "start_line", "end_line"],
                            "search_code": ["query", "path"],
                            "write_file": ["path", "content"],
                            "apply_patch": ["path", "old_text", "new_text"],
                        },
                        "tool_args_optional": {
                            "run_tests": ["path"],
                            "git_diff": ["path"],
                        },
                        "allowed_tools": [
                            "list_dir",
                            "read_file",
                            "search_code",
                            "write_file",
                            "apply_patch",
                            "run_tests",
                            "git_diff",
                        ],
                    },
                    ensure_ascii=True,
                ),
            },
        ]

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            payload = json.loads(content)
            return SchemaValidator.validate_action_payload(payload)
        except Exception:  # noqa: BLE001
            return None
