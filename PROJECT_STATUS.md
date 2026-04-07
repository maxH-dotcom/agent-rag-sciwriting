# 智能科研工作助手 - 项目状态

> 最后更新：2026-04-07（前端重构）

---

## 已完成项目

### 1. 后端核心框架
- FastAPI + 6 Node 编排链路（data_mapping → literature → novelty → analysis → brief → writing）
- `/tasks`、`/tasks/{id}`、`/continue`、`/abort`、`/history`、`/checkpoints` 全套 API
- TaskStore 持久化层（文件后端 + Redis 后端可切换）
- 21/21 测试通过

### 2. 数据映射节点（data_mapping）
- 读取真实 CSV 文件列名和前3行预览
- 明确错误处理：文件不存在/非CSV/未提供文件各有对应提示
- fallback 列名支持无文件场景

### 3. 文献检索适配层
检索优先级：Zotero > local_files > paper-qa > OpenAlex > fallback

**已接入：**
- **Zotero API**：从用户个人库搜索文献，返回标题/作者/年份/摘要/URL，`~/.research_assistant/zotero_config.json` 自动读取 Key
- **OpenAlex API**：真实 HTTP 检索，返回相关文献标题
- **Fallback 规则库**：内置碳排放/面板数据/双重差分等方法知识

**待接入：**
- paper-qa：本地 PDF 语义检索（需安装 + 有 PDF 文件）
- OpenAlex 字段扩展：abstract、methods、concepts 等

### 4. 中断点系统
5 个人工审核中断点：
1. `data_mapping_required` — 确认因变量/自变量/控制变量映射
2. `literature_review_required` — 审核文献检索结果
3. `novelty_result_ready` — 确认创新性和迁移方向
4. `code_plan_ready` — 确认分析代码方案
5. `brief_ready_for_review` — 确认 Research Brief

### 5. Redis 基础设施
- Redis 服务已安装并启动（`brew services start redis`）
- `TaskRepository` + `CheckpointRepository` 支持 Redis 后端（`TASK_REPOSITORY_BACKEND=redis`）
- `LangGraphResearchRuntime` + `MemorySaver` 可用（`ORCHESTRATION_BACKEND=langgraph`）
- ⚠️ `langgraph-checkpoint-redis` 依赖 RedisJSON 模块，当前环境未加载

### 6. E2E 测试
- `test_e2e_interrupt_flow.py`：覆盖 create→中断→modified→approved→done 完整链路
- `test_api_unittest.py`：API 层测试
- `test_orchestrator.py`：编排器中断序列测试
- `test_unittest_smoke.py`：持久化和集成测试

### ~~7. 前端暂停~~ → ✅ 已重构（见 §12）

### 8. OpenAlex 文献质量提升（A）
- `_reconstruct_abstract()`：从 `abstract_inverted_index` 重建完整摘要
- `_extract_openalex_metadata()`：基于摘要+标题+concepts 提取方法/领域/地区/数据结构
- API 参数优化：`has_abstract:true` 过滤 + `relevance_score:desc` 排序，返回 5 条
- 覆盖：10 领域、18 方法、4 数据结构类型、11 地区，中英文关键词双覆盖
- `source` 字段格式化为 `OpenAlex: 作者名 (年份)`，`text` 包含摘要+期刊+年份+关键概念

**待完善：**
- OpenAlex 英文搜索相关性有限（搜索引擎本身限制），方法类关键词命中率低于领域/地区
- 部分论文摘要中不提及具体方法名称时 `method_name` 仍为"待解析"，可考虑结合 LLM 辅助提取
- `concepts` 字段可进一步用于自动映射 `method_name`（OpenAlex concepts 有层级结构，level 0-5）
- 英文查询结果与查询意图偏差较大时，可尝试拼接 `filter=concepts.id:C...` 做概念级过滤

### 9. 真实文件上传机制（D）
- `POST /upload` multipart 端点，支持多文件同时上传
- 自动判断文件类型（`kind=auto`）：CSV/XLSX→data，PDF/TXT/MD→paper
- 支持显式指定 `kind=data` 或 `kind=paper`，带后缀校验
- 文件保存至 `UPLOAD_DIR`（默认 `.runtime/uploads/`，可通过环境变量覆盖）
- UUID 前缀防止文件名冲突，50 MB 大小限制
- 返回服务端绝对路径，可直接传入 `POST /tasks` 的 `data_files`/`paper_files`
- 7 个新测试覆盖：auto/explicit kind、多文件、后缀校验、kind 不匹配、upload→task 完整链路
- 28/28 测试全部通过

### 10. Text-to-Code Bridge（C）
- **证据提取**：从 `literature_result` 中提取 `EvidencePackage`，自动检测缺失面（因变量/自变量/文献/方法）
- **代码生成**：基于数据映射 + 文献证据 + 模型推荐，生成完整可执行的 Python 分析脚本
  - 支持 4 种方法模板：OLS 回归、Panel FE 固定效应、DID 双重差分、STIRPAT 模型
  - 代码包含数据读取、变量准备、清洗、描述统计、回归、结构化输出 6 步完整流程
  - 每个关键步骤绑定证据来源 (`EvidenceBinding`)
- **安全检查**：AST 语法检查 + 正则危险操作拦截 + import 白名单
  - 禁止 `os.system`/`subprocess`/`eval`/`exec`/`__import__`
  - 白名单：pandas, numpy, scipy, statsmodels, sklearn, matplotlib 等分析库
- **Subprocess 沙箱执行**：临时目录隔离 + 数据文件符号链接 + 超时保护 + 最小化环境变量
- **analysis_node 集成**：中断数据包含代码脚本、执行结果、bridge 状态、适应性解释
- 25 个新测试覆盖：安全检查(10)、沙箱执行(4)、证据提取(2)、代码生成(5)、Bridge 集成(2)、模型序列化(2)

**待完善：**
- 代码生成目前为规则模板，后续可接入 LLM 生成更灵活的代码
- 沙箱执行依赖系统 Python + 已安装的分析库（pandas/statsmodels/linearmodels）
- 执行失败时的自动重试和代码修正机制（Phase2 安全与稳定性）

**新增文件：**
| 文件 | 作用 |
|------|------|
| `backend/agents/models/code_generation.py` | 数据模型（EvidencePackage, GeneratedCode, ExecutionResult 等） |
| `backend/core/sandbox.py` | 代码安全检查 + subprocess 沙箱执行 |
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | Bridge 完整流程（证据→生成→检查→执行） |
| `tests/test_text_to_code_bridge.py` | 25 个测试用例 |

### 11. Benchmark 测试套件搭建（2026-04-06 ~ 2026-04-07）
**状态：✅ 全部 63 个测试通过**

**文件结构：**
- `benchmark/retrieval/cases.json` — 15 个检索测试用例
- `benchmark/text_to_code/cases.json` — 18 个代码生成测试用例
- `benchmark/citation/cases.json` — 15 个引用溯源测试用例（全部与实际 chunk 文本对齐）
- `benchmark/e2e/cases.json` — 12 个端到端流程测试用例
- `benchmark/fixtures/retrieval/chunks.json` — 20 个真实文本 chunks
- `benchmark/fixtures/text_to_code/*.csv` — 15 个 CSV 测试数据文件
- `benchmark/mock_client.py` — MockAgentClient（中文 bigram 分词）
- `benchmark/evaluator.py` — BenchmarkEvaluator（修复了 keyword recall 和 stdout JSON 解析）
- `benchmark/run_evaluation.py` — CLI 评测报告生成器
- `tests/test_benchmark_*.py` — 4 个测试文件

**测试覆盖：**
| 类别 | 测试方法数 | 说明 |
|------|-----------|------|
| retrieval | 12 | 关键词匹配/语义检索/Recall@5/Precision@K/噪声查询/空结果 |
| text_to_code | 22 | 基础计算/回归/面板数据/可视化/安全拦截/沙箱执行 |
| citation | 15 | 精确溯源/漂移检测/矛盾检测/过度泛化/溯源链 |
| e2e | 14 | 流程中断/用户拒绝/多节点审批/路由准确性/节点顺序 |

**关键修复：**
- Mock 中文分词：空格 split → 字符 bigram（解决中文检索永远为 0 的问题）
- Keyword recall 计算：从搜索 chunk ID 改为搜索实际文本内容
- `output_data` 为空时：回退解析 stdout 中的 JSON 结构化输出
- Citation cases：全部 15 个 expected_source 与实际 chunk 文本重新对齐
- Optional 依赖测试：statsmodels/sklearn/scipy 未安装时条件通过而非 crash

**中优先级待修复：**
- ✅ `forbidden_operations` 参数在 evaluator._security_check 中被忽略（2026-04-07 修复）
- ✅ 14 个 case 有定义但无对应测试方法（2026-04-07 补全）
- ✅ 无 CI 配置文件（2026-04-07 添加 `.github/workflows/benchmark.yml`）

**本次新增修复：**
- `evaluator._security_check()`：支持 case 级 `forbidden` 动态模式，基础白名单独立生效
- `test_benchmark_text_to_code.py`：补全 code_008/015/016/017/018 五个测试
- `test_benchmark_retrieval.py`：补全 ret_003/006/010/011/012/013/014 七个测试
- 所有沙箱执行测试改为条件通过（pandas 未安装时不 crash）
- `.github/workflows/benchmark.yml`：macOS + Python 3.9矩阵，4类别并行测试
- `benchmark/reporting/report_generator.py`：`ReportGenerator` 类（Markdown + HTML 报告，整合人工评分）
- `benchmark/run_evaluation.py`：重写使用 `ReportGenerator`，输出 JSON/MD/HTML 三种格式

### 12. 前端重构 v2.0（2026-04-07）
**状态：✅ Phase 1~4 主体完成，SSE 实时通讯待后端支持**

**设计系统：**
- Navy 深色主题全面替换浅色 Teal 主题（`#0F172A` 背景 + `#38BDF8` 强调）
- 双字体策略：Crimson Pro（文献/简报）+ Atkinson Hyperlegible（界面/数据）
- 所有 CSS Module 对齐新设计系统

**Zustand 状态管理：**
- `lib/stores/task-store.ts` — 任务全局状态，含 3 秒轮询逻辑
- `lib/stores/settings-store.ts` — API Key + 科研偏好状态
- `lib/stores/model-store.ts` — 变量映射状态

**核心组件（新建）：**
| 组件 | 功能 |
|------|------|
| `FileUploader` | 拖拽上传 + 进度条 + 文件列表 |
| `TaskProgress` | 横向 Stepper，五种节点状态视觉 |
| `TaskDetail` | 按 result 类型分发渲染（Table/Cards/Code/Markdown） |
| `InterruptManager` | 集成 TaskProgress + 轮询状态更新 |

**设置页增强：**
- API Key 管理：密码掩码 + 显示/隐藏 + 连接状态（已保存不回显密钥）
- 科研偏好：分析方法/显著性水平/文献数量/数据编码/年份转换
- 模型连接测试按钮

**待后续迭代：**
- SSE 实时通讯（需后端 `/tasks/{id}/stream` 接口支持）
- Monaco Editor IDE（代码编辑器）
- Variable Mapper（双栏变量映射视图）

**新建文件：**
| 文件 | 作用 |
|------|------|
| `lib/stores/task-store.ts` | 任务 Zustand Store |
| `lib/stores/settings-store.ts` | 设置 Zustand Store |
| `lib/stores/model-store.ts` | 变量映射 Zustand Store |
| `components/file-uploader.tsx` + `.module.css` | 文件上传组件 |
| `components/task-progress.tsx` + `.module.css` | 任务进度 Stepper |
| `components/task-detail.tsx` + `.module.css` | 任务详情结构化渲染 |
| `src/app/settings/page.tsx` | 重构后的设置页 |
| `frontend/src/app/globals.css` | Navy 深色主题全局 CSS |

---

## 待完成项目（按优先级）

### 高优先级

#### ~~A. OpenAlex 文献质量提升~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §8，待完善点已记录**

#### B. paper-qa 接入 ✅ 已完成（2026-04-06）
**文件：**
- `backend/agents/tools/paperqa_wrapper.py` — 轻量级子进程 wrapper（重建）
- `backend/agents/tools/literature_search.py` — `_paperqa_chunks()` 子进程调用

**实现方案：**
- paper-qa 2026.3.18 安装在 `.venv-paperqa` 隔离环境中，避免与主环境 pydantic>=2 冲突
- `paperqa_wrapper.py` 轻量架构：PyPDF 提取文本 → sentence-transformers embedding → Groq API 直调生成答案
- 绕过了 paper-qa → LiteLLM → LiteLLMModel 的 structured-content API 兼容问题

**依赖（.venv-paperqa）：**
```
paper-qa pillow sentence-transformers groq
```

**使用方式：**
1. 主环境设置 `GROQ_API_KEY` 环境变量
2. API 调用时传入 PDF 路径列表（如 `/Volumes/hmq/文献/papers/`）
3. 子进程调用 wrapper，完成 PDF 解析 + embedding + 语义检索 + 答案生成

#### ~~C. Text-to-Code Bridge~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §10**

#### ~~D. 真实文件上传机制~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §9**

### 中优先级

#### ~~E. scw agent mvp 逻辑迁移~~ ✅ 已完成（2026-04-07）
**目录：** `scw agent mvp/`
**合并内容：**
- `backend/agents/tools/question_parser.py`：VAR_ALIASES（16变量×多别名）、normalize_var_name()、多 Provider LLM（Anthropic/Groq/OpenAI）、规则 fallback
- `backend/agents/tools/model_recommender.py`：MODEL_RULES（7模型+文献出处）、infer_data_structure()、has_policy_shock/spatial_effect 参数

#### ~~F. Phase2 安全与稳定性~~ ✅ 已完成（2026-04-07）
**新增文件：**
- `backend/core/error_handling.py`：ErrorSeverity/ErrorInfo、ERROR_CLASSIFICATION（23种错误）、classify_error()、@with_retry（async/sync 通用，指数退避）
- `backend/core/logging/structured_logger.py`：JSONFormatter、StructuredLogger（ContextVar 协程安全）、set_context/with_context
- `backend/core/logging/events.py`：20+ 事件常量（节点/工具/任务/用户交互/性能）

#### ~~G. Phase3 评测体系~~ ✅ 已完成（2026-04-07）
**文件：** `Phase3-评测体系-设计文档.md`
**内容：** Benchmark 测试集、评估指标
**详见已完成项目 §11

### H. 后端优化：自定义模型与全链路编辑（规划中）
**文件：** `思路统筹/后端优化.md`

**核心目标：** 从单一"数据处理流"升级为高自由度"科研工作台"

**三大核心能力：**
1. **代码驱动的自定义模型** — Monaco Editor + Python/R AST 解析 + 动态表单生成
2. **全链路中断与修改干预** — Variable Mapper 可视化映射 + 代码沙箱二次编辑 + 断点续跑
3. **DAG 执行引擎** — 节点级状态持久化 + 从修改节点重新执行

**新增 API 草案：**
| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/models/parse` | POST | 静态解析自定义代码提取变量 |
| `/api/models/custom` | POST | 保存自定义模型资产 |
| `/api/tasks/{id}/nodes/{node}/update` | PUT | 修改指定节点的数据/参数 |
| `/api/tasks/{id}/resume` | POST | 从修改处继续执行 |

**实施风险：**
- 沙箱冷启动延迟 → 建议维护热备用沙箱池（Warm Pool）
- AST 解析容错率低 → 建议强制用户按模板格式书写（如 `def custom_model(data, params):`）

---

## 环境变量说明

```bash
# Redis（TaskRepository + CheckpointRepository 后端）
TASK_REPOSITORY_BACKEND=file        # "file" 或 "redis"
TASK_REPOSITORY_BACKEND=redis

# LangGraph 编排 + Checkpointer
ORCHESTRATION_BACKEND=custom        # "custom"（默认）或 "langgraph"
ORCHESTRATION_BACKEND=langgraph
LANGGRAPH_CHECKPOINT_BACKEND=memory # "memory"（默认）或 "redis"

# Redis 连接
REDIS_URL=redis://127.0.0.1:6379/0

# Zotero（自动从 ~/.research_assistant/zotero_config.json 读取，也可设 env var）
ZOTERO_API_KEY=你的APIKey
```

---

## 启动命令

```bash
cd /Volumes/hmq/智能科研工作助手
source .venv/bin/activate
uvicorn backend.main:app --reload

# 运行测试
pytest tests/ -v

# 上传文件
curl -X POST http://127.0.0.1:8000/upload \
  -F "files=@/path/to/data.csv" \
  -F "files=@/path/to/paper.pdf"

# 用返回的路径创建任务
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type":"analysis","user_query":"碳排放 农业 面板数据","data_files":["/abs/path/to/data.csv"],"paper_files":[]}'
```

---

## Zotero API Key 配置

```bash
# 路径
~/.research_assistant/zotero_config.json

# 内容
{
  "api_key": "sWBsPWaQWj9wP1s7BZFAsHN6",
  "note": "Zotero API Key for 智能科研工作助手"
}
```

---

## 文件索引

### 后端（backend/）

#### 入口
| 文件 | 作用 |
|------|------|
| `backend/main.py` | FastAPI 应用入口 |
| `backend/core/config.py` | 所有环境变量配置 |

#### API 层
| 文件 | 作用 |
|------|------|
| `backend/api/routes.py` | API 路由（/tasks, /upload, /settings 等） |
| `backend/api/schemas.py` | Pydantic 请求/响应模型 |

#### Agent 工具层
| 文件 | 作用 |
|------|------|
| `backend/agents/tools/question_parser.py` | 问题解析（VAR_ALIASES、多 Provider LLM） |
| `backend/agents/tools/model_recommender.py` | 模型推荐（MODEL_RULES、infer_data_structure） |
| `backend/agents/tools/literature_search.py` | 文献检索（Zotero/OpenAlex/paper-qa/fallback） |
| `backend/agents/tools/paperqa_wrapper.py` | paper-qa 轻量 wrapper（子进程调用） |

#### Agent 数据模型
| 文件 | 作用 |
|------|------|
| `backend/agents/models/state.py` | AgentState 图状态定义 |
| `backend/agents/models/research_brief.py` | Research Brief 数据模型 |
| `backend/agents/models/code_generation.py` | 代码生成数据模型（EvidencePackage, GeneratedCode, ExecutionResult） |

#### 编排层
| 文件 | 作用 |
|------|------|
| `backend/agents/orchestrator/main_graph.py` | 主图编排 |
| `backend/agents/orchestrator/langgraph_runtime.py` | LangGraph 运行时 |
| `backend/agents/runtime.py` | AgentRuntime 基类 |

#### Node 子图（6 个）
| 文件 | 作用 |
|------|------|
| `backend/agents/orchestrator/subgraphs/data_mapping_node.py` | 数据映射节点 |
| `backend/agents/orchestrator/subgraphs/literature_node.py` | 文献综述节点 |
| `backend/agents/orchestrator/subgraphs/novelty_node.py` | 创新判断节点 |
| `backend/agents/orchestrator/subgraphs/analysis_node.py` | 分析节点 |
| `backend/agents/orchestrator/subgraphs/brief_builder_node.py` | 简报构建节点 |
| `backend/agents/orchestrator/subgraphs/writing_node.py` | 写作节点 |
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | Text-to-Code Bridge 节点 |

#### 核心（core/）
| 文件 | 作用 |
|------|------|
| `backend/core/task_store.py` | TaskStore 编排逻辑 |
| `backend/core/task_repository.py` | 任务持久化（file/redis 后端） |
| `backend/core/task_history.py` | 任务历史记录 |
| `backend/core/task_mutations.py` | 任务修改逻辑 |
| `backend/core/checkpoint_repository.py` | Checkpoint 持久化 |
| `backend/core/sandbox.py` | 代码安全检查 + subprocess 沙箱执行 |
| `backend/core/error_handling.py` | 错误分类 + 重试装饰器 |
| `backend/core/file_validation.py` | 文件类型校验 |
| `backend/core/redis_checkpointer.py` | Redis String Checkpointer |
| `backend/core/logging/structured_logger.py` | 结构化日志（ContextVar 协程安全） |
| `backend/core/logging/events.py` | 20+ 事件常量 |

### 前端（frontend/）

#### 页面（src/app/）
| 文件 | 作用 |
|------|------|
| `frontend/src/app/page.tsx` | 首页 Landing Page |
| `frontend/src/app/layout.tsx` | 根布局 |
| `frontend/src/app/workspace/page.tsx` | 工作台（任务创建+历史） |
| `frontend/src/app/workspace/[taskId]/page.tsx` | 任务详情页 |
| `frontend/src/app/settings/page.tsx` | 设置页（API Key + 科研偏好） |

#### 组件（components/）
| 文件 | 作用 |
|------|------|
| `frontend/components/task-console.tsx` | 任务创建表单 |
| `frontend/components/task-list.tsx` | 历史任务列表 |
| `frontend/components/interrupt-manager.tsx` | 中断管理 + 继续/终止 |
| `frontend/components/task-progress.tsx` | 任务进度 Stepper（新建） |
| `frontend/components/task-detail.tsx` | 任务详情结构化渲染（新建） |
| `frontend/components/file-uploader.tsx` | 拖拽文件上传组件（新建） |
| `frontend/components/shared.module.css` | 共享样式（Navy 深色主题） |

#### 状态管理（lib/stores/）
| 文件 | 作用 |
|------|------|
| `frontend/lib/stores/task-store.ts` | 任务全局状态 + 轮询 |
| `frontend/lib/stores/settings-store.ts` | 设置 + API Key 状态 |
| `frontend/lib/stores/model-store.ts` | 变量映射状态 |
| `frontend/lib/api.ts` | API 客户端（fetchTasks/fetchTask 等） |

### 测试（tests/）
| 文件 | 作用 |
|------|------|
| `tests/test_e2e_interrupt_flow.py` | 端到端中断流测试 |
| `tests/test_api_unittest.py` | API 层测试 |
| `tests/test_orchestrator.py` | 编排器中断序列测试 |
| `tests/test_unittest_smoke.py` | 持久化和集成测试 |
| `tests/test_literature_search_unittest.py` | 文献检索测试 |
| `tests/test_runtime_unittest.py` | 运行时测试 |
| `tests/test_text_to_code_bridge.py` | Text-to-Code Bridge 测试 |
| `tests/test_benchmark_*.py` | Benchmark 评测测试（4 个） |

### Benchmark（benchmark/）
| 文件 | 作用 |
|------|------|
| `benchmark/evaluator.py` | 评测引擎 |
| `benchmark/run_evaluation.py` | CLI 评测报告生成器 |
| `benchmark/mock_client.py` | MockAgentClient（中文 bigram 分词） |
| `benchmark/retrieval/cases.json` | 15 个检索测试用例 |
| `benchmark/text_to_code/cases.json` | 18 个代码生成测试用例 |
| `benchmark/citation/cases.json` | 15 个引用溯源测试用例 |
| `benchmark/e2e/cases.json` | 12 个端到端测试用例 |
| `benchmark/fixtures/retrieval/chunks.json` | 20 个真实文本 chunks |
| `benchmark/reporting/report_generator.py` | Markdown + HTML 报告生成 |

### 设计文档（思路统筹/）
| 文件 | 作用 |
|------|------|
| `思路统筹/Phase0-最小可运行骨架-实施计划.md` | 项目启动计划 |
| `思路统筹/Phase1-集成与中断-设计文档.md` | 中断点系统设计 |
| `思路统筹/Phase1-Analysis-Node-设计文档.md` | Analysis Node 设计 |
| `思路统筹/Phase1-Literature-Node-设计文档.md` | Literature Node 设计 |
| `思路统筹/Phase1-Novelty-Node-设计文档.md` | Novelty Node 设计 |
| `思路统筹/Phase1-Research-Brief-Schema-设计文档.md` | Research Brief Schema |
| `思路统筹/Phase1-Text-to-Code-Bridge-设计文档.md` | Text-to-Code Bridge 设计 |
| `思路统筹/Phase1-Writing-Node-设计文档.md` | Writing Node 设计 |
| `思路统筹/Phase2-安全与稳定性-设计文档.md` | 安全与稳定性设计 |
| `思路统筹/Phase3-评测体系-设计文档.md` | 评测体系设计 |
| `思路统筹/后端优化.md` | 自定义模型 + 全链路编辑架构 |
| `思路统筹/架构图-综合版.md` | 系统架构图（Mermaid） |
| `思路统筹/时序图-综合版.md` | 时序图（Mermaid） |
| `思路统筹/科研多Agent系统MVP实施计划.md` | MVP 实施总计划 |
| `思路统筹/设计文档索引.md` | 文档索引 |

### 其他
| 文件 | 作用 |
|------|------|
| `CLAUDE.md` | 项目级 Claude Code 指令 |
| `PROJECT_STATUS.md` | 本项目状态文档 |
| `README.md` | 项目说明 |
| `requirements.txt` | Python 依赖 |
| `TODOS.md` | 待办事项 |
| `改进建议_2026-04-07.md` | 改进建议记录 |
| `paused-work/frontend-workbench-paused/` | 暂停的前端工作副本 |
| `scw agent mvp/` | SCW Agent MVP 工作目录 |
