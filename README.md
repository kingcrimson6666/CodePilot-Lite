# CodePilot Lite

> 面向本地代码库的 AI 编程助手，实现"读代码 → 改代码 → 运行测试 → 评估反馈"的完整闭环。

---

## 🌟 项目亮点

| 特性 | 描述 |
|------|------|
| **智能任务规划** | 基于 LLM 的行动决策系统，自动分解任务并选择合适工具 |
| **混合检索 RAG** | BM25 + 语义嵌入双重检索，精准定位代码上下文 |
| **安全治理体系** | 策略引擎、审批门、路径守卫三层安全防护 |
| **量化评估系统** | TSR/OTR/MTTR 核心指标，科学评估任务效果 |
| **完整可观测性** | 结构化日志、指标追踪、任务回放全链路覆盖 |

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- 虚拟环境（推荐）

### 安装依赖
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 配置环境
```bash
# 复制配置文件
cp .env.example .env

# 配置 AI 服务（可选）
# 修改 .env 中的 API Key 和 Endpoint
```

### 启动服务
```bash
# 启动交互式会话
./scripts/start.sh

# 或直接运行任务
python -m src.app.cli run --task "修复项目中的 bug"
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     CodePilot Lite                         │
├─────────────────────────────────────────────────────────────┤
│  CLI Layer                                                  │
│  ├── chat: 交互式会话                                       │
│  ├── run: 任务执行                                          │
│  ├── eval-run: 批量评估                                     │
│  └── metrics-dashboard: 指标看板                            │
├─────────────────────────────────────────────────────────────┤
│  Core Layer                                                 │
│  ├── AgentOrchestrator: 任务编排核心                        │
│  ├── Planner: 计划更新引擎                                  │
│  ├── ContextAssembler: 上下文组装器                         │
│  └── StateMachine: 状态管理                                 │
├─────────────────────────────────────────────────────────────┤
│  AI Layer                                                   │
│  ├── LLMGateway: LLM 访问网关（支持多提供商）                │
│  ├── PromptBuilder: 提示词构建器                            │
│  └── SchemaValidator: 输出格式验证                          │
├─────────────────────────────────────────────────────────────┤
│  RAG Layer                                                  │
│  ├── VectorStore: 向量存储（Chroma/InMemory）               │
│  ├── Retriever: 混合检索器（BM25 + Embedding）              │
│  ├── Indexer: 文档索引器                                    │
│  └── Chunker: 代码切分器                                   │
├─────────────────────────────────────────────────────────────┤
│  Governance Layer                                           │
│  ├── PolicyEngine: 策略引擎                                 │
│  ├── ApprovalGate: 审批门                                   │
│  └── SecurityGuards: 安全守卫                               │
├─────────────────────────────────────────────────────────────┤
│  Observability Layer                                        │
│  ├── Logger: 结构化日志                                     │
│  ├── MetricsDB: 指标数据库                                  │
│  └── Replay: 任务回放                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心功能

### 1. AI 任务规划
- 自动分析任务需求
- 智能选择执行工具
- 支持多轮迭代执行

### 2. 代码检索
- **BM25 检索**: 基于词频的快速检索
- **语义检索**: 基于 Embedding 的深度匹配
- **混合检索**: 综合排序提升准确率

### 3. 安全治理
- **路径守卫**: 防止目录穿越攻击
- **风险分类**: 自动识别高风险操作
- **审批机制**: 交互式确认或自动审批

### 4. 评估体系
| 指标 | 定义 |
|------|------|
| **TSR** | 任务成功率（Task Success Rate） |
| **OTR** | 首次尝试成功率（One-time Success Rate） |
| **MTTR** | 平均任务耗时（Mean Time to Resolution） |
| **无效工具调用率** | 失败工具调用占比 |

---

## 🛠️ 工具集

| 工具 | 功能 | 参数 |
|------|------|------|
| `list_dir` | 列出目录内容 | `path` |
| `read_file` | 读取文件内容 | `path`, `start_line`, `end_line` |
| `write_file` | 写入文件内容 | `path`, `content` |
| `apply_patch` | 应用代码补丁 | `path`, `old_text`, `new_text` |
| `search_code` | 搜索代码 | `query`, `path` |
| `run_tests` | 运行测试 | `path` (可选) |
| `git_diff` | 查看 Git 差异 | `path` (可选) |

---

## 📊 评估报告示例

```json
{
  "summary": {
    "total_tasks": 20,
    "passed_tasks": 15,
    "tsr": 0.75,
    "otr": 0.65,
    "mttr_ms": 12000,
    "invalid_tool_call_rate": 0.05
  }
}
```

---

## 🧪 测试覆盖

```
tests/
├── integration/          # 集成测试
│   ├── test_cli_eval_command.py
│   ├── test_orchestrator.py
│   └── test_orchestrator_traceability.py
└── unit/                 # 单元测试
    ├── test_approval_gate.py
    ├── test_convergence.py
    ├── test_llm_eval.py
    ├── test_policy_engine.py
    └── ...
```

运行测试：
```bash
python -m pytest tests/ -v
```

---

## 🔧 配置说明

### 配置文件示例

#### 开发环境配置（`.env`）
```bash
# 基础配置
CODEPILOT_WORKSPACE=.
CODEPILOT_LOG_LEVEL=INFO
CODEPILOT_MAX_STEPS=6

# AI 模型配置
CODEPILOT_MODEL_PROVIDER=openai
CODEPILOT_MODEL_NAME=qwen-plus
CODEPILOT_MODEL_API_KEY=sk-xxx-your-api-key-xxx
CODEPILOT_MODEL_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 评审模型配置
CODEPILOT_JUDGE_MODEL_PROVIDER=openai
CODEPILOT_JUDGE_MODEL_NAME=qwen-plus

# 安全配置
CODEPILOT_AUTO_APPROVE_HIGH_RISK=false
CODEPILOT_APPROVAL_LOG_PATH=data/governance/approvals.jsonl

# RAG 配置
CODEPILOT_RAG_BACKEND=chroma
CODEPILOT_RAG_CHROMA_PATH=data/rag/chroma
CODEPILOT_RAG_USE_BM25=true
CODEPILOT_RAG_USE_EMBEDDINGS=true
CODEPILOT_RAG_EMBEDDING_PROVIDER=aliyun
CODEPILOT_RAG_EMBEDDING_MODEL=text-embedding-v3
CODEPILOT_RAG_EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 评估配置
CODEPILOT_LIVE_HARD_CHECKS=false
CODEPILOT_COMMAND_TIMEOUT_SEC=20

# 指标数据库
CODEPILOT_METRICS_DB_PATH=data/codepilot.sqlite
```

#### 生产环境配置要点
```bash
# 使用生产级向量存储
CODEPILOT_RAG_BACKEND=chroma

# 启用严格模式
CODEPILOT_AUTO_APPROVE_HIGH_RISK=false
CODEPILOT_LIVE_HARD_CHECKS=true

# 调整超时时间
CODEPILOT_COMMAND_TIMEOUT_SEC=60
```

#### 离线开发配置（无需网络）
```bash
# 使用 stub 模式，无需 AI 服务
CODEPILOT_MODEL_PROVIDER=stub
CODEPILOT_JUDGE_MODEL_PROVIDER=stub

# 使用内存向量存储
CODEPILOT_RAG_BACKEND=memory
CODEPILOT_RAG_USE_EMBEDDINGS=false
```

### 环境变量详解

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CODEPILOT_WORKSPACE` | `.` | 工作目录，所有文件操作限制在此目录内 |
| `CODEPILOT_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARN/ERROR） |
| `CODEPILOT_MAX_STEPS` | `6` | 单个任务最大执行步数 |
| `CODEPILOT_MODEL_PROVIDER` | `stub` | AI 提供商（openai/stub） |
| `CODEPILOT_MODEL_NAME` | `gpt-4o-mini` | 模型名称 |
| `CODEPILOT_MODEL_API_KEY` | - | API Key（必填，使用真实模型时） |
| `CODEPILOT_MODEL_API_BASE` | - | API 端点 URL |
| `CODEPILOT_AUTO_APPROVE_HIGH_RISK` | `false` | 是否自动批准高风险操作（写文件等） |
| `CODEPILOT_RAG_BACKEND` | `memory` | 向量存储后端（memory/chroma） |
| `CODEPILOT_RAG_USE_BM25` | `true` | 是否启用 BM25 检索 |
| `CODEPILOT_RAG_USE_EMBEDDINGS` | `true` | 是否启用语义嵌入检索 |
| `CODEPILOT_RAG_EMBEDDING_PROVIDER` | `local` | 嵌入服务提供商（local/aliyun） |
| `CODEPILOT_LIVE_HARD_CHECKS` | `false` | 是否在运行时执行硬检查 |
| `CODEPILOT_COMMAND_TIMEOUT_SEC` | `20` | 命令执行超时时间（秒） |

### 配置验证

启动前验证配置：
```bash
# 检查配置是否正确加载
python -c "from src.infra.config import AppSettings; print(AppSettings().model_dump())"

# 测试 AI 连接（需要网络）
python -c "
from src.models.llm_gateway import LLMGateway
gw = LLMGateway(provider='openai', api_key='your-key', api_base='your-base')
print(gw.decide_action('test', []))
"
```

---

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 代码行数 | ~3000 LOC |
| 测试覆盖率 | 80%+ |
| 支持工具数 | 7 个 |
| 检索类型 | 2 种（BM25 + Embedding） |

---


