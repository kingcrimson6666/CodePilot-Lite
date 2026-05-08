---
name: implement
description: Run a subagent to implement changes
usage: /implement <task>
requires_args: true
arg_hint: "Describe the implementation task and expected changes."
---
请使用 Task 工具启动子代理执行实现任务，要求：
- agent_type: react
- tool_filter: full
- 需要修改时先给出补丁建议或明确变更点

子任务：
$ARGUMENTS
