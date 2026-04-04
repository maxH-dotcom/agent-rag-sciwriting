# 科研论文 RAG + 多 Agent 系统 MVP 实施计划

> **版本**：v0.1
> **日期**：2026-04-02
> **状态**：待审核

---

## 一、项目概述

### 1.1 目标定位

构建一个**面向真实科研工作流的、可控的、可追溯的科研助手 MVP**，帮助研究者完成：

1. 判断新选题是否与已有论文重复
2. 根据数据结构和研究目标推荐合适模型
3. 基于文献依据生成可执行分析代码
4. 输出论文提纲与方法/结果草稿
5. 给关键结论附上证据来源，支持人工审核

### 1.2 核心原则

| 原则 | 含义 |
|------|------|
| `LangGraph is the only orchestrator` | 整个系统只有一个主控，防止状态撕裂 |
| `paper-qa is only a tool layer` | 文献工具层不反客为主 |
| `No evidence, no code` | 任何关键公式、指标构造必须先有学术依据 |
| `No raw logs into writer` | 写作不被原始日志、错误信息污染 |

### 1.3 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 前端 | Next.js 14 (App Router) + Tailwind | 高效构建工作台界面 |
| 后端 | Python FastAPI + LangGraph | LangGraph 是核心编排层 |
| 核心编排 | LangGraph StateGraph + CheckpointSaver | 唯一主控 |
| 文献检索 | paper-qa + pyopenalex | 已有成熟工具，不重复造轮子 |
| 结构化数据 | DuckDB + pandas + Code Interpreter | 数据管理与执行 |
| 数据契约 | Research_Brief.json | 节点间唯一数据契约 |
| 状态持久化 | Redis (CheckpointSaver) | 生产级断点续跑支持 |

### 1.4 MVP 范围约束

为避免在 Phase 0/1 过早引入复杂解析逻辑，MVP 明确限定以下边界：

1. **研究问题解析**：当前只支持主效应导向的问题表达，默认模式为“单一因变量 + 少量自变量”。
   - 例如 `"GDP 对 CO2 的影响"`、`"FDI 对碳排放的影响"` 属于 MVP 支持范围。
   - 像 `"GDP and FDI jointly on CO2 controlling for trade openness"` 这类多自变量 + 控制变量的复合问题，暂不做自动变量角色拆解。
2. **数据文件范围**：MVP 仅保证单 sheet 的表格输入能稳定工作，推荐上传单 sheet CSV。
   - 多 sheet Excel 不做自动 sheet 选择，也不做跨 sheet 合并。
3. **变量类型推断**：连续变量 / 二值变量 / 计数变量的自动识别在 MVP 阶段不做强推断。
   - 当前依赖用户的自然语言描述、列名语义和人工确认。
4. **paper-qa 检索边界**：paper-qa 在系统中默认承担本地已上传文献的检索与问答。
   - 外部文献补充由 `pyopenalex` 完成，MVP 不额外定义 Semantic Scholar / arXiv 直连搜索策略。

---

## 二、系统架构

### 2.1 整体架构图

```
用户（上传文献/数据 + 提出任务）
           │
           ▼
┌─────────────────────────────────────────────┐
│           前端工作台 (Next.js)               │
│  任务入口 │ 状态展示 │ 中断审核 │ 结果查看   │
└─────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│         FastAPI 路由层 (Python)              │
│   POST /tasks │ GET /tasks/{id} │ SSE stream │
└─────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│       LangGraph 主控 (唯一编排器)             │
│         状态管理 + 路由 + 中断控制            │
└─────────────────────────────────────────────┘
           │
     ┌─────┼─────┬─────────┬─────────┐
     ▼     ▼     ▼         ▼         ▼
  ┌────┐┌────┐┌─────┐  ┌─────┐  ┌──────┐
  │Novel││Lit- ││Analy-│  │Brief│  │Writing│
  │ty   ││eratu││sis   │  │Buil-│  │      │
  │Node ││re   ││Node  │  │der  │  │Node  │
  │     ││Node ││      │  │     │  │      │
  └──┬──┘└──┬──┘└──┬───┘  └──┬──┘  └──┬───┘
     │      │       │         │        │
     ▼      ▼       ▼         ▼        ▼
  paper-  paper-  DuckDB   Research  Draft
  qa      qa      Code     Brief    Output
          +       Interp           + Evidence
       pyopenalex
```

### 2.2 五大任务节点（调整后，2026-04-04）

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **Literature Node** | 文献检索 + 方法元信息提取 | 研究问题 + 关键词 | method_metadata（含迁移上下文） |
| **Novelty Node** | 迁移/组合/调整可行性评估（决策节点） | Literature 的 method_metadata + 用户数据上下文 | transfer_assessments + 推荐方向（含迁移逻辑） |
| **Analysis Node** | 数据分析与模型匹配 | 结构化数据 + 研究目标 | 模型推荐 + 分析代码 + 结果 |
| **Brief Builder** | 汇总 Research_Brief（含 transfer_context） | 前4个节点结果 | 结构化研究卡片 |
| **Writing Node** | 生成论文提纲与草稿 | Research_Brief（含迁移上下文） | 提纲 + 方法草稿 + 结果草稿 |

### 2.3 四个中断审核点（调整后，2026-04-04）

系统在关键节点暂停，等待人工确认后再继续：

| 中断点 | 触发时机 | 用户决策 |
|--------|----------|----------|
| **数据映射中断（新增）** | 用户上传数据后自动解析 | 确认变量映射 / 修改映射 / 取消上传 |
| **Novelty 中断** | 迁移/组合/调整评估完成（调整后内涵） | 确认迁移方向 / 修改方向 / 拒绝（终止任务） |
| **Text-to-Code 中断** | 代码逻辑确认 + 适应性解释（新增） | 执行代码 / 修改代码 / 跳过此步 |
| **Brief Builder 中断** | Research_Brief 编辑（含 transfer_context） | 确认Brief / 直接修改JSON |
| **Writing 中断** | 草稿输出确认 | 接受草稿 / 修改 / 重新生成 |

### 2.4 项目目录结构

```
research-assistant/
├── backend/                      # Python 后端
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── main_graph.py     # LangGraph 主图
│   │   │   └── subgraphs/
│   │   │       ├── novelty_node.py
│   │   │       ├── literature_node.py
│   │   │       ├── analysis_node.py
│   │   │       ├── brief_builder_node.py
│   │   │       └── writing_node.py
│   │   ├── tools/
│   │   │   ├── paperqa_wrapper.py
│   │   │   ├── pyopenalex_wrapper.py
│   │   │   ├── duckdb_wrapper.py
│   │   │   ├── code_interpreter.py
│   │   │   └── text_to_code_bridge.py
│   │   └── models/
│   │       ├── state.py          # LangGraph State 定义
│   │       └── schemas.py        # Pydantic 模型
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py             # FastAPI 路由
│   │   └── schemas.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理
│   │   ├── llm_config.py        # LLM 配置（持久化，多 provider）
│   │   ├── mcp_config.py        # MCP Port 配置
│   │   ├── mcp_client.py        # MCP Client 实现
│   │   └── exceptions.py         # 异常定义
│   └── main.py                  # FastAPI 入口
│
├── frontend/                     # Next.js 前端
│   ├── src/app/
│   │   ├── page.tsx             # 工作台首页
│   │   ├── workspace/
│   │   │   ├── page.tsx         # 任务列表
│   │   │   └── [taskId]/
│   │   │       └── page.tsx     # 任务详情/执行页
│   │   └── api/
│   │       └── tasks/
│   │           └── route.ts     # API 路由
│   ├── components/
│   │   ├── task-console.tsx     # 任务控制台
│   │   ├── file-upload.tsx     # 文件上传组件
│   │   ├── brief-editor.tsx     # Research Brief 编辑器
│   │   ├── draft-viewer.tsx     # 草稿查看器
│   │   ├── evidence-panel.tsx   # 证据面板
│   │   ├── llm-config.tsx      # LLM 配置面板
│   │   ├── mcp-port-manager.tsx # MCP Port 管理
│   │   └── interrupt-manager.tsx # 中断管理器
│   └── tailwind.config.ts
│
├── benchmark/                    # 评测基准
│   ├── retrieval/               # 检索类测试
│   ├── text_to_code/            # 代码生成类测试
│   ├── citation_trace/           # 引用溯源类测试
│   └── end_to_end/              # 端到端测试
│
├── checkpoint/                   # 阶段检查点
│   └── README.md
│
├── requirements.txt              # Python 依赖
└── package.json                  # 前端依赖
```

---

## 三、实施路线图

### Phase 0：最小可运行骨架

**目标**：验证 LangGraph 核心编排能力，建立 API + 前端基础

**验收标准**：
- POST /tasks 创建任务返回 task_id
- 任务自动运行到 Novelty 节点并中断（状态 = "interrupted"）
- GET /tasks/{id} 返回当前节点名称和中断原因
- 前端展示中断状态并可继续/终止
- Redis Checkpoint 记录状态，进程重启后可恢复

#### Phase 0.1：项目初始化

- [ ] 创建项目目录结构
- [ ] 初始化 Python 后端（requirements.txt）
- [ ] 初始化 Next.js 前端
- [ ] 配置 Git

#### Phase 0.2：LangGraph 主图骨架

- [ ] 定义 `MainState`（任务ID、当前节点、任务类型、状态、中断标记）
- [ ] 主图 + 条件路由（route_next_node）
- [ ] `CheckpointSaver` 配置 Redis 持久化
- [ ] **仅实现 1 个子图**：Novelty Subgraph（选题查重）
- [ ] 第一个 `Interrupt`：Novelty 节点 → 用户确认选题方向

#### Phase 0.3：FastAPI 基础路由

- [ ] `POST /tasks` — 创建任务
- [ ] `GET /tasks/{task_id}` — 查询任务状态
- [ ] `POST /tasks/{task_id}/continue` — 继续执行（处理中断）
- [ ] `POST /tasks/{task_id}/abort` — 终止任务

#### Phase 0.4：前端骨架

- [ ] 任务创建表单（任务描述输入）
- [ ] 任务状态轮询展示（pending → running → interrupted → done/error）
- [ ] 中断时显示"请确认选题方向"并提供继续/终止按钮

---

### Phase 1：核心链路打通

**目标**：5 个节点全部实现，5 个中断点完整，数据流贯通

**前置条件**：Phase 0 验收通过

#### Phase 1.1：数据准备子图（新增）

- [ ] 数据文件解析（自动识别列名、数据类型）
- [ ] 面板结构检测（地区列 + 年份列识别）
- [ ] 变量映射 UI（用户选择因变量/自变量/控制变量）
- [ ] 数据映射中断（Interrupt 0）

#### Phase 1.2：完成剩余 4 个子图

- [ ] Literature Subgraph（文献检索 + method_metadata 提取）
- [ ] Novelty Subgraph（迁移/组合/调整评估）
- [ ] Analysis Subgraph（DuckDB + Code Interpreter）
- [ ] Writing Subgraph（生成提纲/草稿）

#### Phase 1.3：Text-to-Code Bridge

- [ ] 强制前置逻辑（无 evidence 则拒绝生成）
- [ ] 证据检索 → 代码生成 → 人工审核 → 执行
- [ ] 适应性解释输出（adaptation_explanation）

#### Phase 1.4：Research_Brief Schema + Builder

定义完整的数据契约格式，支持版本管理和人工编辑（含 transfer_context）。

#### Phase 1.5：完整 5 个中断点

所有中断点的前端 UI 和 API 处理（含数据映射中断）。

#### Phase 1.6：LLM 配置持久化

- [ ] LLM 配置层（支持多 provider：OpenAI/Groq/DeepSeek/Kimi/Minimax/智谱/百川/千帆/Gemini/Anthropic/Ollama）
- [ ] 配置文件持久化（~/.research_assistant/llm_config.json）
- [ ] 前端 LLM 配置 UI

#### Phase 1.7：MCP 集成

- [ ] MCP 配置层（MCPConfig + MCPPortConfig）
- [ ] MCP Client 实现
- [ ] 内置 MCP Ports（学术搜索、Wolfram、图表渲染、数据清洗、翻译）
- [ ] MCP 管理 API
- [ ] 前端 MCP 管理 UI

#### Phase 1.5：SSE 状态推送（替代轮询）

- [ ] `GET /tasks/{task_id}/stream` — SSE 实时推送状态变更
- [ ] 前端 SSE 订阅

---

### Phase 2：安全与稳定性

**目标**：异常不污染状态，断点续跑可靠

- [ ] Code Interpreter 沙箱隔离（Docker/Pyodide）
- [ ] CheckpointSaver Redis 持久化完整配置
- [ ] 工具层错误分类（可重试 vs 不可重试）+ 重试机制
- [ ] 链路追踪结构化日志

---

### Phase 3：评测体系建设

**目标**：每次变更可验证

- [ ] 黄金测试集（RET/CODE/CITE/E2E 各 10-20 条）
- [ ] 离线评测框架（自动计算指标）
- [ ] 人工评分 5 分制机制
- [ ] 评测报告自动化

---

## 四、核心数据结构

### 4.1 MainState（LangGraph 状态，调整后）

```python
class MainState(TypedDict):
    # 任务标识
    task_id: str
    task_type: str  # "topic_novelty_check" | "model_recommendation" | "analysis" | "writing"
    current_node: str  # "literature" | "novelty" | "analysis" | "brief" | "writing"
    status: str  # "pending" | "running" | "interrupted" | "done" | "error"

    # 各节点结果
    literature_result: dict | None  # 包含 method_metadata（新增）
    novelty_result: dict | None     # 包含 transfer_assessments（调整）
    analysis_result: dict | None
    brief_result: dict | None
    writing_result: dict | None

    # 中断相关
    interrupt_reason: str | None
    interrupt_data: dict | None

    # 用户确认数据
    human_decision: dict | None

    # Redis Checkpoint
    checkpoint_id: str
```

### 4.2 Research_Brief.json（数据契约，调整后）

```json
{
  "version": "1.1.0",
  "task_type": "topic_novelty_check",
  "research_goal": "判断中东地区农业碳排放研究是否与已有论文重复",

  "novelty_position": {
    "overlap_with_existing": ["使用STIRPAT模型", "长江流域碳排放研究"],
    "differentiation_points": ["研究区域不同", "加入适应性调整"],
    "suggested_topic_directions": [
      "基于STIRPAT的中东地区农业碳排放预测（从长江流域迁移）"
    ]
  },

  "transfer_context": {
    "source_method": "STIRPAT模型",
    "source": "长江流域碳排放研究（文献A）",
    "transfer_feasibility": "高",
    "transfer_feasibility_reason": "数据结构相似（均为面板数据），研究问题类型相同",
    "required_adaptations": [
      "变量映射：FDI → 能源消耗强度",
      "控制变量调整：加入地形因素、灌溉方式"
    ],
    "adaptation_risk": "时间序列长度不足可能影响模型稳定性",
    "variable_mapping": {"FDI": "能源消耗强度", "GDP": "农业产值"}
  },

  "data_summary": {
    "file_name": "middle_east_agriculture.csv",
    "rows": 300,
    "columns": ["region", "year", "agri_output", "energy_consumption", "co2"],
    "diagnostic_notes": "面板数据，2000-2023年，15个地区"
  },

  "method_decision": {
    "recommended_model": "STIRPAT + LMDI组合",
    "reason": "STIRPAT用于驱动因素分析，LMDI用于分解量化",
    "evidence_sources": ["chunk_101", "chunk_145"],
    "rejected_models": ["LSTM黑箱预测", "单一Geodetector"],
    "transfer_context": { ... },
    "transfer_assessments": [ ... ]
  },

  "analysis_outputs": {
    "code_script": "...",
    "execution_result": {},
    "charts": ["carbon_trend.png"],
    "numerical_results": {},
    "adaptation_explanation": "本代码将STIRPAT模型从长江流域迁移到中东地区..."
  },

  "evidence_map": {
    "claim_001": {
      "text": "STIRPAT模型适用于碳排放驱动因素分析",
      "source_chunk_id": "chunk_101",
      "source_file": "参考文献01.pdf"
    }
  },

  "draft_sections": {
    "outline": "1.引言 2.数据与方法 3.结果 4.讨论",
    "methods": "...",
    "results": "...",
    "abstract": "..."
  },

  "audit_trail": [
    {
      "node": "novelty",
      "action": "human_approved",
      "timestamp": "2026-04-02T10:00:00Z",
      "human_approval": true
    }
  ],

  "created_at": "2026-04-02T09:00:00Z",
  "updated_at": "2026-04-04T12:00:00Z"
}
```

---

## 五、API 设计

### 5.1 任务管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks` | 创建新任务 |
| GET | `/tasks/{task_id}` | 查询任务状态和结果 |
| POST | `/tasks/{task_id}/continue` | 继续执行（附带用户决策） |
| POST | `/tasks/{task_id}/abort` | 终止任务 |
| GET | `/tasks/{task_id}/stream` | SSE 流式状态推送 |

### 5.2 请求/响应示例

**POST /tasks** (创建任务)
```json
// Request
{
  "task_type": "topic_novelty_check",
  "user_query": "判断浙江省农业碳排放趋势预测是否与已有论文重复",
  "files": ["old_paper.docx", "zhejiang_panel_data.xlsx"]
}

// Response
{
  "task_id": "task_abc123",
  "status": "running",
  "current_node": "novelty",
  "created_at": "2026-04-02T10:00:00Z"
}
```

**GET /tasks/{task_id}** (查询状态 - 中断时)
```json
{
  "task_id": "task_abc123",
  "status": "interrupted",
  "current_node": "novelty",
  "interrupt_reason": "novelty_result_ready",
  "interrupt_data": {
    "overlap": ["C-F-E耦合模型"],
    "differentiation": ["趋势预测", "情景模拟"],
    "suggestions": ["ARIMA", "Holt指数平滑"]
  },
  "checkpoint_id": "ckpt_xyz789"
}
```

**POST /tasks/{task_id}/continue** (继续执行)
```json
// Request
{
  "decision": "approved",
  "modified_data": {
    "accepted_directions": ["ARIMA"],
    "rejected_directions": ["Holt指数平滑"]
  }
}

// Response
{
  "task_id": "task_abc123",
  "status": "running",
  "current_node": "literature"
}
```

---

## 六、评测指标

### 6.1 核心指标

| 指标 | 阈值 | 说明 |
|------|------|------|
| RAG Recall@5 | > 0.9 | 关键证据召回率 |
| RAG Precision@10 | > 0.7 | 检索精度 |
| Text-to-Code 执行成功率 | > 0.85 | 代码能跑通 |
| Text-to-Code 结果准确率 | > 0.8 | 结果经验证正确 |
| 引用溯源 Trace Success Rate | > 0.9 | 论断能绑定来源 |
| 引用漂移 Drift Rate | < 0.05 | 引用准确性 |
| 风险拦截率 | > 0.95 | 高风险操作被拦截 |
| 路由准确率 | > 0.9 | 任务正确分发 |
| 端到端任务完成率 | > 0.7 | 5类任务中完成3类 |
| 端到端人工采纳率 | > 0.6 | 用户愿意使用输出 |

### 6.2 黄金测试集

| 类别 | 数量 | 说明 |
|------|------|------|
| 检索类 (RET) | 10-20条 | 特定方法文献、公式出处、同区域研究等 |
| Text-to-Code 类 (CODE) | 10-20条 | 指标构造、面板清洗、回归分析、预测建模 |
| 引用溯源类 (CITE) | 10-20条 | 方法综述、结果分析段落 |
| 端到端类 (E2E) | 10-15条 | 从原始数据到方法草稿的完整流程 |

---

## 七、风险控制

### 7.1 风险场景与应对

| 风险场景 | 闸门策略 |
|----------|----------|
| 无文献依据生成关键代码 | Text-to-Code Bridge 拒绝生成 |
| 高风险操作（删除数据/覆盖文件） | 必须人工确认 |
| 路由死循环 | 计数器上限 → 报错退出 |
| 引用漂移（drift > 0.05） | 拒绝输出正式引用稿 |
| 工具调用失败 | 节点失败分支 + 降级策略 |
| 进程崩溃 | Redis Checkpoint 断点续跑 |

### 7.2 Checkpoint 机制

每次完成 Phase 后保存：
1. Git commit: "phase-X: 完成说明"
2. Checkpoint 文件: `checkpoint/phase-X-{date}.json`
   - 已完成的任务状态
   - 关键代码快照
   - 配置快照
3. 进度报告: `PHASE_X_REPORT.md`

---

## 八、依赖技术

| 技术 | 用途 | 安装方式 |
|------|------|----------|
| `langgraph` | 主控编排 | `pip install langgraph` |
| `langgraph[langchain]` | LangChain 集成 | `pip install langgraph[langchain]` |
| `paper-qa` | 文献问答 | `pip install paper-qa` |
| `pyopenalex` | 外部文献 | `pip install pyopenalex` |
| `duckdb` | 数据管理 | `pip install duckdb` |
| `fastapi` | API层 | `pip install fastapi uvicorn` |
| `redis` | 状态持久化 | `pip install redis` |
| `sse-starlette` | SSE 支持 | `pip install sse-starlette` |
| `next.js` | 前端 | `npx create-next-app@14 frontend` |

---

## 九、下一步行动

### 待确认事项

1. [ ] **前端技术栈**：Next.js 14 是否符合预期？是否有其他偏好？
2. [ ] **项目路径**：代码是否放在当前目录 `/Volumes/hmq/智能科研工作助手/思路统`？
3. [ ] **Redis 配置**：是否已有 Redis 服务？需要我安装配置吗？
4. [ ] **paper-qa 集成方式**：本地部署还是 API 调用？
5. [ ] **Code Interpreter 执行方式**：Docker 沙箱还是 Pyodide？

### 审核后实施计划

确认上述事项后，按以下顺序实施：

1. **Phase 0.1** — 项目初始化（30分钟）
2. **Phase 0.2** — LangGraph 主图 + Redis（1-2小时）
3. **Phase 0.3** — FastAPI 路由（1小时）
4. **Phase 0.4** — 前端骨架（1-2小时）
5. **验收测试** — 端到端流程验证

每步完成后提供 checkpoint 和进度报告。

---

## 附录：相关文档索引

| 文档 | 路径 |
|------|------|
| MVP 设计文档 | `/Users/hemengqian/Documents/New project/research-rag-multi-agent-mvp-design.md` |
| 评测基准文档 | `/Users/hemengqian/Documents/New project/research-agent-evaluation-benchmark.md` |
| 实施计划 | `/Users/hemengqian/.claude/plans/steady-toasting-melody.md` |
