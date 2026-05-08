---
name: generate
description: Generate code for a requirement
usage: /generate <requirements>
requires_args: true
arg_hint: "Describe the feature or change you want to generate."
---
根据以下需求生成代码。如果需要写入文件，请说明目标文件路径和修改点，并给出补丁建议。

需求：
$ARGUMENTS
