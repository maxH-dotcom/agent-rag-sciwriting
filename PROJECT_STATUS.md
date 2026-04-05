# 智能科研工作助手 - 项目状态

> 最后更新：2026-04-05

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

---

## 待完成项目（按优先级）

### 高优先级

#### A. OpenAlex 文献质量提升
**文件：** `backend/agents/tools/literature_search.py:164-193`
**现状：** `_openalex_chunks()` 只取 `title`/`id`，不提取方法名、摘要、领域
**目标：** 解析 OpenAlex 的 `abstract_inverted_index`、`concepts`、`methods` 等字段，提升 `method_name` 和 `data_structure` 提取质量
**前置：** 无，Python 纯逻辑修改

#### B. paper-qa 接入（需要条件）
**文件：** `backend/agents/tools/literature_search.py:114-162`
**现状：** `paper-qa` 未安装，`_paperqa_chunks()` 返回空
**目标：** `pip install paperqa`，验证 PDF 语义检索
**前置条件：** 需要有本地 PDF 论文文件才能测试解析效果
**注意：** paper-qa 对中文 PDF 支持有限（依赖 pdfminer/pygments）

#### C. Text-to-Code Bridge
**文件：** `backend/agents/orchestrator/subgraphs/analysis_node.py`
**现状：** `analysis_node` 只生成代码草稿字符串，不执行
**目标：** 实现代码执行沙箱（参考 `Phase1-Text-to-Code-Bridge-设计文档.md`）
**风险：** 较高，涉及代码执行安全隔离

#### D. 真实文件上传机制
**文件：** `backend/core/file_validation.py`
**现状：** 只接受绝对路径，没有 multipart 文件上传
**目标：** 实现文件上传 API，不再依赖用户手动填绝对路径

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

# 用 Zotero 真实检索测试
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type":"analysis","user_query":"碳排放 农业 面板数据","data_files":[],"paper_files":[]}'
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
| `思路统筹/*.md` | 各阶段设计文档 |
