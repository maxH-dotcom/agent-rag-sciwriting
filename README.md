# 智能科研工作助手

面向中文科研场景的多 Agent 科研工作台，把科研流程拆成一条可中断、可审核、可扩展、可测试的产品链路。

## 核心流程

1. 上传数据和参考文献
2. 解析研究问题 → 数据映射
3. 文献检索与方法证据整理
4. 创新性与迁移可行性判断
5. 代码方案生成与人工确认
6. 结构化 `Research Brief`
7. 论文提纲与方法/结果草稿

## 适合谁

- 有研究问题和数据，想系统化科研流程的研究者
- 想把"脚本原型"升级成"可维护产品"的开发者
- 需要保留人工审核节点的科研团队

---

## 快速启动

### 1. 后端

```bash
cd /Volumes/hmq/智能科研工作助手
source .venv/bin/activate
uvicorn backend.main:app --reload
```

- API 文档: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/healthz

### 2. 前端

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

访问 http://localhost:3000

### 3. 配置 Zotero API（可选）

不配置也能用，系统会降级到 OpenAlex + fallback 规则库。

1. 登录 https://www.zotero.org → 设置 → Feeds/API → 创建 API Key
2. 写入配置：

```bash
mkdir -p ~/.research_assistant
cat > ~/.research_assistant/zotero_config.json << 'EOF'
{
  "api_key": "你的API Key",
  "note": "Zotero API Key for 智能科研工作助手"
}
EOF
```

---

## 使用流程

### 第一步：准备数据

推荐 CSV 文件，至少包含：

- 一个地区列，如 `地区`
- 一个时间列，如 `年份`
- 因变量（结果变量），如 `碳排放`
- 自变量（解释变量），如 `农业产值`

### 第二步：创建任务

在工作台输入研究问题，例如：

> 我想分析农业产值对碳排放的影响，同时控制农药使用量

可选填数据文件路径和参考论文路径。

### 第三步：人工审核

系统在 5 个关键节点暂停等待确认：

| 中断点 | 内容 |
|--------|------|
| `data_mapping_required` | 确认因变量/自变量/控制变量映射 |
| `literature_review_required` | 审核文献检索结果 |
| `novelty_result_ready` | 确认创新性和迁移方向 |
| `code_plan_ready` | 确认分析代码方案 |
| `brief_ready_for_review` | 确认 Research Brief |

每个节点可选择「继续任务」或「终止任务」。

### 第四步：查看结果

任务完成后，在任务详情页查看完整输出，包括数据映射结果、文献证据、推荐模型、代码脚本和论文草稿。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/tasks` | 创建新任务 |
| `GET` | `/tasks` | 任务列表 |
| `GET` | `/tasks/{id}` | 任务详情 |
| `POST` | `/tasks/{id}/continue` | 继续任务（带决策） |
| `POST` | `/tasks/{id}/abort` | 终止任务 |
| `GET` | `/tasks/{id}/history` | 任务历史 |
| `GET` | `/tasks/{id}/checkpoints` | 中断点记录 |
| `POST` | `/upload` | 上传数据/论文文件 |
| `GET` | `/system/runtime` | 运行时信息 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 (App Router) |
| 后端 | FastAPI + LangGraph 编排层 |
| 存储 | File backend / Redis（可切换） |
| 文献 | Zotero API / OpenAlex API / paper-qa |
| 代码执行 | Subprocess 沙箱 + AST 安全检查 |

---

## 目录结构

```
backend/
  agents/
    models/           # State、Research Brief、数据契约
    orchestrator/     # 主编排器 + 6 个 Node
    tools/            # 问题解析、文献检索、模型推荐
  api/                # FastAPI 路由 + Schema
  core/               # TaskStore、配置、错误处理、沙箱
frontend/
  src/app/            # Next.js App Router 页面
  components/         # TaskConsole、InterruptManager、TaskList
  lib/                # API 调用封装
tests/                 # 单元测试 + E2E 测试
benchmark/             # 检索/代码生成/引用溯源/端到端评测套件
```

---

## 测试

```bash
# 全部测试
pytest tests/ -v

# Benchmark 评测
python benchmark/run_evaluation.py

# 特定类别
pytest tests/test_benchmark_retrieval.py -v
pytest tests/test_benchmark_text_to_code.py -v
pytest tests/test_benchmark_citation.py -v
pytest tests/test_benchmark_e2e.py -v
```

---

## 环境变量

```bash
# 存储后端（file 或 redis）
TASK_REPOSITORY_BACKEND=file

# LangGraph 编排（custom 或 langgraph）
ORCHESTRATION_BACKEND=custom

# Redis（可选）
REDIS_URL=redis://127.0.0.1:6379/0

# Zotero
ZOTERO_API_KEY=你的APIKey

# 前端（可选）
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```
