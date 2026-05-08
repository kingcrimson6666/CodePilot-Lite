---
name: review
description: Review a module or file for issues and risks
usage: /review <path or scope>
requires_args: true
arg_hint: "Provide a file path or module name to review."
---
请对以下范围进行代码审查，重点关注：潜在 bug、风险、边界条件、缺失测试。给出具体建议。

范围：
$ARGUMENTS
