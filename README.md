# 🤖 CodePilot Lite

基于 **HelloAgents** 框架开发的智能编程助手，支持对话式问答、项目分析、代码调试与修复。

---

## 🏆 项目亮点

| 指标 | 数据 |
|------|------|
| **代码规模** | 27,806 行 Python 代码 |
| **文件数量** | 129 个 Python 文件 |
| **测试用例** | 484+ 个单元测试 |
| **Agent 类型** | 5 种 (ReAct, Reflection, PlanSolve, Simple) |
| **内置工具** | 6 个核心工具 |
| **Skills 技能** | 17 个专业技能 |
| **CLI 命令** | 10 个快捷命令 |

---

## 🚀 核心功能

### 🤖 Agent 智能体系统

| Agent 类型 | 特点 | 适用场景 |
|-----------|------|----------|
| **ReAct Agent** | 基于 Function Calling 的推理与行动循环 | 需要工具调用的复杂任务 |
| **Reflection Agent** | 自我反思与迭代优化 | 需要深度分析的任务 |
| **PlanSolve Agent** | 规划-执行两阶段模式 | 复杂多步骤任务 |
| **Simple Agent** | 直接对话模式 | 简单问答场景 |
| **子代理机制** | 任务分解与并行执行 | 大型项目分析 |

### 🛠️ 工具系统

- **文件操作**: 读取、写入、编辑（乐观锁 + 原子写入）
- **项目分析**: 目录树、依赖解析、入口识别
- **错误诊断**: Traceback 解析、补丁生成
- **系统命令**: 安全命令自动批准

### 📚 Skills 技能系统

```
├── AI 能力:     LLM, VLM, TTS, ASR
├── 文档处理:    PDF, DOCX, XLSX, PPTX
├── 多媒体:      图像生成、视频生成、视频理解
└── Web 能力:    网页搜索、网页阅读、金融分析
```

### 📊 上下文工程

- 历史消息管理（轮次检测、智能压缩）
- Token 计数（增量计算、缓存优化）
- 输出截断与持久化

### 🔍 可观测性

- Trace 日志（JSONL 格式）
- HTML 可视化报告
- 完整错误追踪

### 💾 会话持久化

- 自动/手动保存会话
- 状态恢复与环境一致性检查

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Coding Assistant                          │
├─────────────────────────────────────────────────────────────────┤
│  app/                    应用层                                │
│  ├── cli.py              命令行入口                            │
│  ├── agents/main_agent.py Agent 工厂与配置                     │
│  ├── tools/              自定义工具 (10个)                    │
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
│  │   └── skills/         框架级技能 (17个)                   │
│  └── tests/              单元测试 (484+)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 分类 | 技术 | 说明 |
|------|------|------|
| **语言** | Python 3.10+ | 核心开发语言 |
| **LLM** | OpenAI Compatible API | 支持多模型提供商 |
| **框架** | HelloAgents | 自研 Agent 框架 |
| **测试** | pytest | 单元测试框架 |
| **流式** | SSE (Server-Sent Events) | 实时输出 |

---

## 📦 快速开始

### 环境要求

```bash
# 安装依赖
pip install -r requirements.txt

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
python app/cli.py

# 📝 单次提问
python app/cli.py -m "帮我分析项目结构"

# 👨‍🏫 教学模式
python app/cli.py --student
```

---

## 💻 使用示例

```
> 帮我分析这个项目的结构
--- 第 1/8 步 ---
💭 思考: 用户需要项目结构分析，我需要调用 ProjectTree 工具来生成目录树。
🔧 调用工具: ProjectTree({'depth': 3})
👀 观察: AI-Agent/
├── app/
│   ├── cli.py
│   ├── agents/
│   └── tools/
├── frameworks/HelloAgents/
└── tests/
--- 第 2/8 步 ---
🎉 最终答案: 项目结构分析完成...
```

---

## 📁 项目结构

```
AI-Agent/                                    # 项目根目录
├── app/                                     # 应用层
│   ├── cli.py                               # CLI 入口 (交互式会话)
│   ├── agents/
│   │   └── main_agent.py                    # Agent 工厂与工具注册
│   ├── tools/                               # 自定义工具
│   │   ├── ProjectTreeTool.py               # 项目目录树
│   │   ├── DependencyTool.py                # 依赖分析
│   │   ├── EntryPointTool.py                # 入口识别
│   │   ├── FileSummaryTool.py               # 文件摘要
│   │   ├── ErrorParserTool.py               # 错误解析
│   │   ├── BugFixTool.py                    # Bug 修复
│   │   ├── CommandTool.py                   # 命令执行
│   │   └── ...
│   ├── commands/                            # CLI 命令模板
│   │   ├── overview.md                      # /overview 命令
│   │   ├── explain.md                       # /explain 命令
│   │   ├── fix.md                           # /fix 命令
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

---

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
- 乐观锁检测文件修改时间
- 自动备份原文件
- 支持预览和确认

### 3. 智能上下文管理
- 历史消息轮次检测
- 自动摘要压缩
- Token 数量控制

### 4. 多 Agent 协作
- 子代理独立执行
- 结果汇总返回
- 上下文隔离

### 5. 完整可观测性
- JSONL 格式 Trace 日志
- HTML 可视化报告
- 统计信息追踪

---

## 🧪 测试覆盖

| 测试模块 | 测试文件 | 说明 |
|----------|----------|------|
| Agent 测试 | `test_all_agents.py` | 所有 Agent 类型 |
| 工具测试 | `test_file_tools.py`, `test_custom_tools.py` | 文件工具、自定义工具 |
| 上下文测试 | `test_context_engineering.py` | 上下文工程 |
| 会话测试 | `test_session_persistence.py` | 会话持久化 |
| 可观测性测试 | `test_observability.py`, `test_trace_integration.py` | Trace 日志 |
| 技能测试 | `test_skills.py` | Skills 系统 |

---

## 📊 性能特点

| 特性 | 说明 |
|------|------|
| **异步执行** | 支持异步 LLM 调用和工具并行执行 |
| **增量计算** | Token 计数采用缓存机制 |
| **熔断保护** | 工具调用失败自动熔断 |
| **自动保存** | 会话定期自动保存 |

---

## 👨‍💻 开发者友好

- **模块化设计**: 清晰的代码组织结构
- **类型提示**: 完整的 Python 类型注解
- **详细文档**: 代码注释和 Markdown 文档
- **快速调试**: 支持教学模式和详细日志

---

## 📝 总结

这是一个**功能完整、架构清晰**的 AI 编程助手项目，涵盖：

1. **Agent 框架**: 5 种 Agent 类型，支持复杂推理
2. **工具系统**: 文件操作、项目分析、错误诊断
3. **上下文工程**: 智能历史管理和压缩
4. **可观测性**: 完整的日志和报告系统
5. **扩展性**: 支持自定义工具和 Skills


