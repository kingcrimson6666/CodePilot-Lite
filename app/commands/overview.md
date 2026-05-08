---
name: overview
description: Summarize project structure and entrypoints
usage: /overview <root>
requires_args: true
arg_hint: "Use '.' for the repo root, or provide a subdirectory."
---
请对项目进行快速概览：
1) 调用 ProjectTree 工具获取目录结构
2) 调用 Dependency 工具获取依赖
3) 调用 EntryPoint 工具定位入口
4) 输出结构化概览

项目根目录：
$ARGUMENTS
