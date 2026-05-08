---
name: analyze
description: Run a read-only subagent for analysis tasks
usage: /analyze <task>
requires_args: true
arg_hint: "Describe the analysis task for the subagent."
---
请使用 Task 工具启动子代理执行分析任务，要求：
- agent_type: react
- tool_filter: readonly
- 只读分析，不做写入修改

子任务：
$ARGUMENTS
