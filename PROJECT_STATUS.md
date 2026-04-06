# 智能科研工作助手 - 项目状态

> 最后更新：2026-04-06

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

### 7. 前端暂停
- 前端代码已移至 `paused-work/frontend-workbench-paused/`
- 暂停原因：后端链路尚不稳定，不适合同时推进前后端

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

#### E. scw agent mvp 逻辑迁移
**目录：** `scw agent mvp/`
**现状：** 旧原型独立运行，逻辑未迁移到新架构
**目标：** 合并有价值组件到新架构，避免双轨维护

#### F. Phase2 安全与稳定性
**文件：** `Phase2-安全与稳定性-设计文档.md`
**内容：** 重试逻辑、错误分类、沙箱隔离

#### G. Phase3 评测体系
**文件：** `Phase3-评测体系-设计文档.md`
**内容：** Benchmark 测试集、评估指标

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

## 关键文件路径

| 文件 | 作用 |
|------|------|
| `backend/agents/tools/literature_search.py` | 文献检索适配层（含 Zotero/OpenAlex/paper-qa/fallback） |
| `backend/agents/orchestrator/subgraphs/` | 6 个 Node 实现 |
| `backend/core/task_store.py` | TaskStore 编排逻辑 |
| `backend/core/config.py` | 所有环境变量配置 |
| `backend/core/redis_checkpointer.py` | Redis String Checkpointer（待完善） |
| `tests/test_e2e_interrupt_flow.py` | 端到端中断流测试 |
| `backend/agents/models/code_generation.py` | Text-to-Code Bridge 数据模型 |
| `backend/core/sandbox.py` | 代码安全检查 + subprocess 沙箱 |
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | Bridge 完整流程 |
| `思路统筹/*.md` | 各阶段设计文档 |
| `backend/api/routes.py` | API 路由（含 /upload 文件上传端点） |
