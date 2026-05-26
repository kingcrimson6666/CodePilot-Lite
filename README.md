# 🤖 CodePilot Lite

基于 **HelloAgents** 框架开发的智能编程助手，面向对话式问答、项目分析、代码调试、文件编辑与任务执行等场景。

这个项目的默认形态是一个清晰的单入口 ReAct Agent：`app/cli.py` 负责接收输入，`app/agents/main_agent.py` 负责构建主 Agent 并注册工具，框架层提供上下文工程、会话持久化、Trace、Skills 和子代理等增强能力。


## 🏆 项目亮点

| 指标 | 数据 |
|------|------|
| **主入口** | 单一 ReAct Agent 编排 |
| **CLI 命令** | 7 个 Markdown 命令模板 |
| **核心工具** | 10 个默认注册工具 |
| **本地 Skills** | 2 个应用级技能 |
| **可观测性** | Trace + HTML 报告 |
| **会话能力** | 支持保存、加载与恢复 |
| **上下文工程** | 历史管理、Token 计数、截断 |


## 🚀 核心功能

### 🤖 Agent 智能体系统

| Agent 类型 | 特点 | 适用场景 |
|-----------|------|----------|
| **ReAct Agent** | 当前应用默认入口，基于工具调用的推理与行动循环 | 需要工具调用的复杂任务 |
| **Reflection Agent** | 自我反思与迭代优化 | 需要深度分析的任务 |
| **PlanSolve Agent** | 规划-执行两阶段模式 | 复杂多步骤任务 |
| **Simple Agent** | 直接对话模式 | 简单问答场景 |
| **子代理机制** | 框架层可选扩展，支持任务拆分与并行执行 | 大型项目分析 |

### 🛠️ 工具系统

- **文件操作**: 读取、写入、编辑，覆盖主工作流中的代码查看与修改。
- **项目分析**: 目录树、依赖解析、入口识别、文件摘要，适合快速建立仓库认知。
- **错误诊断**: Traceback 解析、Bug 修复建议，适合定位异常与生成修复方向。
- **系统命令**: 命令执行工具可用于 `pwd`、`ls` 等事实核验。
- **工具编排**: 主 Agent 默认注册 10 个工具，必要时还能通过 Skills 自动扩展能力。


### 📚 Skills 技能系统

```
├── AI 能力:     LLM, VLM, TTS, ASR
├── 文档处理:    PDF, DOCX, XLSX, PPTX
├── 多媒体:      图像生成、视频生成、视频理解
└── Web 能力:    网页搜索、网页阅读、金融分析
```

应用层目前内置两个本地技能：`code-explain` 和 `python-debug`。框架层还提供更广泛的技能目录，覆盖 LLM、VLM、ASR、TTS、Office 文档、多媒体、Web 与前端设计等方向。

## 🔍 项目分析与亮点

### 1. 默认入口非常克制，利于调试和迭代

整个应用默认只有一个主入口和一个主 Agent，不把“多智能体”做成必选项，而是把它放在框架层作为扩展能力。这样的好处是：主流程清晰、排障更容易、提示词更稳定。

### 2. 命令、提示词和代码分离

`app/commands/` 里的 Markdown 文件不是文档装饰，而是真正的命令模板。命令系统把 `/overview`、`/explain`、`/review`、`/fix`、`/generate`、`/implement`、`/analyze` 这些能力拆成独立文件，降低了维护成本。

### 3. 工具层围绕真实工程工作流设计

这套工具不是为了做演示，而是直接覆盖项目分析、文件修改、错误定位和命令核验。它能让模型先看结构、再看文件、再修复问题，而不是在大段自然语言里猜代码。

### 4. 上下文工程和可观测性是项目的核心资产

历史管理、Token 计数、输出截断、Trace 日志和 HTML 报告共同构成了一个可复盘系统。对一个长对话编程助手来说，这比单纯“会回答”更重要，因为它决定了系统能否长期工作。

### 5. 会话持久化让任务可以跨轮继续

项目支持保存、恢复和列表查看会话，适合实际工程中的“今天分析一半、明天继续处理”的场景。结合 `--load-session` 和 `--list-sessions`，这个助手更接近真正的开发工具，而不是一次性聊天机器人。

### 6. Skills 与子代理是可扩展性的关键

Skills 让知识模块化，子代理让复杂任务分解化。两者结合后，项目具备了从单次问答扩展到长任务协作的能力。

### 📊 上下文工程

- 历史消息由管理器维护，不是把所有轮次无差别拼接。
- Token 计数支持缓存和增量计算，适合长会话场景。
- 工具输出会按行数和字节数截断，避免大输出淹没上下文。
- 当历史过长时，可以触发压缩和摘要机制。

### 🔍 可观测性

- Trace 默认启用。
- 记录格式包含 JSONL 和 HTML 可视化报告。
- 方便回溯每一步推理、工具调用和最终结果。

### 💾 会话持久化

- 支持保存和恢复会话。
- 支持列出已有会话文件。
- 支持加载指定会话继续工作。
- 适合“今天开始，明天继续”的真实工程任务。



## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Coding Assistant                          │
├─────────────────────────────────────────────────────────────────┤
│  app/                    应用层                                │
│  ├── cli.py              命令行入口                            │
│  ├── agents/main_agent.py Agent 工厂与配置                     │
│  ├── tools/              自定义工具 (10个核心工具)           │
│  ├── commands/           CLI 命令系统                         │
│  └── skills/             应用级技能                           │
├─────────────────────────────────────────────────────────────────┤
│  frameworks/HelloAgents/ 框架层                               │
│  ├── hello_agents/       框架核心                             │
│  │   ├── agents/         Agent 实现 (5种)                    │
│  │   ├── core/           核心组件                            │
│  │   │   ├── agent.py    Agent 基类                          │
│  │   │   ├── llm.py      LLM 统一接口                         │
│  │   │   ├── config.py   配置管理                            │
│  │   │   └── session_store.py 会话存储                      │
│  │   ├── tools/          工具系统                            │
│  │   ├── context/        上下文工程                          │
│  │   ├── observability/  可观测性                            │
│  │   └── skills/         框架级技能 (丰富扩展库)              │
│  └── tests/              单元测试与验证                       │
└─────────────────────────────────────────────────────────────────┘
```


## 🛠️ 技术栈

| 分类 | 技术 | 说明 |
|------|------|------|
| **语言** | Python 3.10+ | 核心开发语言 |
| **LLM** | OpenAI Compatible API | 支持多模型提供商 |
| **框架** | HelloAgents | 自研 Agent 框架 |
| **测试** | pytest | 单元测试框架 |
| **流式** | SSE (Server-Sent Events) | 实时输出 |


## 📦 快速开始

### 环境要求

```bash
# 安装依赖
pip install -r requirements.txt

# 安装框架（重要！否则找不到 hello_agents 模块）
cd frameworks/HelloAgents
pip install -e .
cd ../..

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入:
# - LLM_MODEL_ID
# - LLM_API_KEY
# - LLM_BASE_URL
```

### 启动方式

```bash
# 🖥️ CLI 模式（推荐）
./start.sh

# 📝 单次提问
./start.sh -m "帮我分析项目结构"

# 📋 列出会话
./start.sh --list-sessions

# 📂 加载会话
./start.sh --load-session <会话文件>
```


## 💻 使用示例

```
> 帮我分析这个项目的结构
💭 思考: 用户需要项目结构分析，我需要调用 ProjectTree 工具来生成目录树。
🔧 调用工具: ProjectTree({'depth': 3})
👀 观察: AI-Agent/
├── app/
│   ├── cli.py
│   ├── agents/
│   └── tools/
├── frameworks/HelloAgents/
└── tests/
🎉 最终答案: 项目结构分析完成...
```


## 📁 项目结构

```
AI-Agent/                                    # 项目根目录
├── app/                                     # 应用层
│   ├── cli.py                               # CLI 入口 (交互式会话)
│   ├── agents/
│   │   └── main_agent.py                    # Agent 工厂与工具注册
│   ├── tools/                               # 自定义工具
│   │   ├── project_tree_tool.py             # 项目目录树
│   │   ├── dependency_tool.py               # 依赖分析
│   │   ├── entrypoint_tool.py               # 入口识别
│   │   ├── file_summary_tool.py             # 文件摘要
│   │   ├── error_parser_tool.py             # 错误解析
│   │   ├── bug_fix_tool.py                  # Bug 修复
│   │   ├── command_tool.py                  # 命令执行
│   │   └── ...
│   ├── commands/                            # CLI 命令模板
│   │   ├── overview.md                      # /overview 命令
│   │   ├── explain.md                       # /explain 命令
│   │   ├── review.md                        # /review 命令
│   │   ├── fix.md                           # /fix 命令
│   │   ├── generate.md                      # /generate 命令
│   │   ├── implement.md                     # /implement 命令
│   │   ├── analyze.md                       # /analyze 命令
│   │   └── ...
│   └── skills/                              # 应用级技能
│       ├── code-explain/                    # 代码解释技能
│       └── python-debug/                    # Python 调试技能
├── frameworks/HelloAgents/                   # 框架层
│   ├── hello_agents/                        # 框架核心
│   │   ├── agents/                          # Agent 实现
│   │   │   ├── react_agent.py               # ReAct Agent
│   │   │   ├── reflection_agent.py          # Reflection Agent
│   │   │   ├── plan_solve_agent.py          # PlanSolve Agent
│   │   │   ├── simple_agent.py              # Simple Agent
│   │   │   └── factory.py                   # Agent 工厂
│   │   ├── core/                            # 核心组件
│   │   │   ├── agent.py                     # Agent 基类
│   │   │   ├── llm.py                       # LLM 统一接口
│   │   │   ├── config.py                    # 配置管理
│   │   │   ├── message.py                   # 消息模型
│   │   │   ├── session_store.py             # 会话存储
│   │   │   └── streaming.py                 # 流式输出支持
│   │   ├── tools/                           # 工具系统
│   │   │   ├── base.py                      # 工具基类
│   │   │   ├── registry.py                  # 工具注册表
│   │   │   ├── response.py                  # 响应协议
│   │   │   ├── circuit_breaker.py           # 熔断器机制
│   │   │   └── builtin/                     # 内置工具
│   │   ├── context/                         # 上下文工程
│   │   │   ├── history.py                   # 历史管理
│   │   │   ├── truncator.py                 # 输出截断
│   │   │   └── token_counter.py             # Token 计数
│   │   ├── observability/                   # 可观测性
│   │   │   └── trace_logger.py              # Trace 日志
│   │   └── skills/                          # 框架级技能 (17个)
│   └── tests/                               # 单元测试 (484+)
├── storage/                                 # 会话与日志
├── tests/                                   # 项目级测试
├── README.md                                # 项目说明
├── requirements.txt                         # 依赖列表
└── .gitignore                               # Git 忽略配置
```


## ✨ 核心设计亮点

### 1. 流式输出机制
```python
async def arun_stream(input_text: str):
    async for event in agent.arun_stream(input_text):
        if event.type == StreamEventType.LLM_CHUNK:
            # 实时输出每个文本块
            print(event.data.get("chunk"), end="", flush=True)
```

### 2. 安全写入机制

### 3. 智能上下文管理

### 4. 子代理协作

### 5. 完整可观测性


## 🧪 测试覆盖

| 测试模块 | 测试文件 | 说明 |
|----------|----------|------|
| Agent 测试 | `test_all_agents.py` | 所有 Agent 类型 |
| 工具测试 | `test_file_tools.py`, `test_custom_tools.py` | 文件工具、自定义工具 |
| 上下文测试 | `test_context_engineering.py` | 上下文工程 |
| 会话测试 | `test_session_persistence.py` | 会话持久化 |
| 可观测性测试 | `test_observability.py`, `test_trace_integration.py` | Trace 日志 |
| 技能测试 | `test_skills.py` | Skills 系统 |


## 📊 性能特点

| 特性 | 说明 |
|------|------|
| **异步执行** | 支持异步 LLM 调用和工具并行执行 |
| **增量计算** | Token 计数采用缓存机制 |
| **熔断保护** | 工具调用失败自动熔断 |
| **自动保存** | 会话定期自动保存 |


## 👨‍💻 开发者友好



## 📝 总结

这是一个**功能完整、架构清晰**的 AI 编程助手项目，涵盖：

1. **Agent 框架**: 5 种 Agent 类型，支持复杂推理
2. **工具系统**: 文件操作、项目分析、错误诊断
3. **上下文工程**: 智能历史管理和压缩
4. **可观测性**: 完整的日志和报告系统
5. **扩展性**: 支持自定义工具和 Skills


