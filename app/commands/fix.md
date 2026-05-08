---
name: fix
description: Diagnose errors and propose a fix
usage: /fix <error>
requires_args: true
arg_hint: "Paste the traceback or error message to analyze."
---
请按以下步骤处理报错：
1) 调用 ErrorParser 工具解析 traceback
2) 如果可以定位文件与修复思路，调用 BugFix 工具生成补丁建议
3) 输出结构化结论与下一步建议

报错：
$ARGUMENTS
