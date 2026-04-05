# 智能科研助手

一个面向中文科研场景的多 Agent 科研工作台。

它不是“只会吐代码的脚本”，而是把科研流程拆成一条可中断、可审核、可扩展、可测试的产品链路：

1. 上传数据和参考文献
2. 解析研究问题
3. 文献检索与方法证据整理
4. 创新性与迁移可行性判断
5. 代码方案生成与人工确认
6. 结构化 `Research Brief`
7. 论文提纲与方法/结果草稿

## 适合谁

- 不会编程，但有研究问题和数据的小白用户
- 想把“脚本原型”升级成“可维护产品”的开发者
- 需要保留人工审核点的科研团队

## 现在仓库里有什么

- `backend/`：FastAPI + 编排层 + 节点 + Schema
- `frontend/`：Next.js 工作台骨架
- `tests/`：核心流程的基础测试
- `思路统筹/`：设计文档与实施计划
- `scw agent mvp/`：旧脚本原型，作为参考，不再作为主产品目录

## 第一次启动，按这个来

### 1. 安装 Python 依赖

```bash
cd /Volumes/hmq/智能科研工作助手
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 Zotero API（可选）

Zotero 个人库检索需要 API Key：

1. 登录 https://www.zotero.org → 设置 → Feeds/API → 创建 API Key
2. 将 Key 写入配置：

```bash
mkdir -p ~/.research_assistant
cat > ~/.research_assistant/zotero_config.json << 'EOF'
{
  "api_key": "你的API Key",
  "note": "Zotero API Key for 智能科研工作助手"
}
EOF
```

不配置 Zotero 也能用（跳过 Zotero 检索，降级到 OpenAlex + fallback）。

### 3. 启动后端

```bash
uvicorn backend.main:app --reload
```

启动后访问：

- API 文档: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查: [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)

### 4. 前端说明

前端开发已暂时冻结，当前代码已经被整理到单独目录：

`/Volumes/hmq/智能科研工作助手/paused-work/frontend-workbench-paused`

相关说明见：

- [前端暂停说明](/Volumes/hmq/智能科研工作助手/paused-work/FRONTEND_PAUSED.md)

所以当前主线请先专注后端联调。

### 5. 如果未来要恢复前端

```bash
cd /Volumes/hmq/智能科研工作助手/paused-work/frontend-workbench-paused
npm install
npm run dev
```

启动后访问：

- 工作台: [http://127.0.0.1:3000](http://127.0.0.1:3000)

如果你的后端不是跑在 `127.0.0.1:8000`，先这样指定：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 小白怎么用

### 第一步：准备数据

建议先用一个 CSV 文件。第一版最稳的是单表数据，至少包含：

- 一个地区列，比如 `地区`
- 一个时间列，比如 `年份`
- 你关心的结果变量，比如 `碳排放`
- 你想研究的解释变量，比如 `农业产值`

### 第二步：新建任务

当前版本建议先走后端 API，等前端恢复后再切回工作台。

你可以先在 `/docs` 页面测试接口，或者用 `curl`/Postman 调：

- `POST /tasks`
- `GET /tasks/{id}`
- `GET /tasks/{id}/history`
- `GET /tasks/{id}/checkpoints`
- `POST /tasks/{id}/continue`
- `POST /tasks/{id}/abort`
- `GET /system/runtime`

前端恢复后，再在工作台里填写：

- 研究问题，比如“我想分析农业产值对碳排放的影响，同时控制农药使用量”
- 数据文件路径
- 已有参考论文路径（可选）

### 第三步：一路确认中断点

系统不会偷偷往下跑到底。它会在关键地方停下来让你确认：

1. 数据映射对不对
2. 创新性和迁移方向对不对
3. 代码方案能不能执行
4. Research Brief 要不要改
5. 草稿能不能接受

这就是产品的核心，不是多此一举。科研里最贵的不是“生成慢”，而是“生成错了你还没发现”。

## 当前版本的边界

第一版故意收住了范围，先把主链路做稳：

- 单用户、本地优先
- 单表数据优先
- 主效应研究问题优先
- 文献检索：Zotero 个人库 + OpenAlex API + paper-qa（本地 PDF）+ fallback 规则库，按优先级排序
- 代码执行目前输出的是可审核分析脚本，不直接做高风险自动写文件

## 目录说明

```text
backend/
  agents/
    models/         # State、Research Brief、节点数据契约
    orchestrator/   # 主编排器与子节点
    tools/          # 问题解析、文献检索、模型推荐等工具层
  api/              # 请求响应 Schema、路由
  core/             # 配置与任务存储
paused-work/
  frontend-workbench-paused/  # 暂停中的前端代码
tests/              # 基础测试
```

## 后续怎么扩展

如果你后面要加功能，优先沿着这个顺序：

1. 先在 `backend/agents/models/` 补数据契约
2. 再在 `backend/agents/orchestrator/subgraphs/` 补节点逻辑
3. 然后在 `backend/api/schemas.py` 暴露给 API
4. 最后才补 `frontend/components/` 的 UI

别反过来。先把状态和契约钉住，后面改起来才不会散。

## 测试

```bash
cd /Volumes/hmq/智能科研工作助手
pytest tests
```

如果本地还没装 `pytest`，先跑一个不依赖额外包的 smoke test：

```bash
python3 tests/test_unittest_smoke.py
```

## 给维护者的话

这个仓库现在已经从“能跑的脚本”切到了“可维护的产品骨架”。

下一步最值得做的不是继续堆功能，而是把三件事做实：

1. 接入真实 LangGraph 持久化和 Redis
2. 把文献检索从 fallback 升级成真实 paper-qa/OpenAlex 适配器
3. 给每个中断点补端到端测试

现在第 2 条已经做到了“适配层 ready”，第 1 条也已经做到“运行时探测 + 存储后端抽象 + checkpoint 仓库”，所以后续真正接 LangGraph 时，不需要再推倒重来。
