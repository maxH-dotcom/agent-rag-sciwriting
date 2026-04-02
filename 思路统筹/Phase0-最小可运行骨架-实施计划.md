# Phase 0：最小可运行骨架

> **版本**：v0.1
> **日期**：2026-04-02
> **前置文档**：`科研多Agent系统MVP实施计划.md`

---

## 一、目标与验收标准

### 1.1 目标

验证 LangGraph 核心编排能力，建立 API + 前端基础。

### 1.2 验收标准

- POST /tasks 创建任务返回 task_id
- 任务在后台异步运行，自动执行到 Novelty 节点并中断（状态 = "interrupted"）
- GET /tasks/{id} 返回当前节点名称和中断原因
- SSE 流实时推送状态变更
- 前端展示中断状态并提供继续/终止按钮
- Redis Checkpoint 记录状态，进程重启后可恢复

---

## 二、关键设计决策（已确认）

| 决策项 | 选择 | 理由 |
|--------|------|------|
| SSE 状态推送 | Phase 0 直接实现 | 避免后续重写 |
| Novelty Subgraph | 单一 LangGraph 节点 | 快速验证主图骨架 |
| 任务执行模型 | 后台异步 | 提交后立即返回 task_id |
| CheckpointSaver | Redis + 内存双缓冲 | 兼顾持久化和性能 |
| 任务元数据存储 | Redis Hash | 简单、原子操作、适合 SSE |

---

## 三、实施步骤

### Phase 0.1：项目初始化

#### 3.1.1 目录结构

```
research-assistant/
├── backend/
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── main_graph.py      # 主图 + 路由
│   │   │   └── subgraphs/
│   │   │       └── novelty_node.py # Novelty 单一节点
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── state.py           # MainState 定义
│   │   └── tools/
│   │       └── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # 路由
│   │   └── schemas.py             # Pydantic models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Redis + LLM 配置
│   │   └── task_store.py          # Redis Hash 任务存储
│   ├── runner.py                  # LangGraph 异步运行器
│   └── main.py                    # FastAPI 入口
├── frontend/
│   └── src/app/
│       ├── page.tsx               # 工作台首页
│       └── workspace/[taskId]/
│           └── page.tsx           # 任务详情页
├── requirements.txt
└── package.json
```

#### 3.1.2 requirements.txt

```txt
langgraph>=0.0.20
langgraph[langchain]>=0.0.20
redis>=5.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sse-starlette>=2.0.0
python-multipart>=0.0.9
pydantic>=2.0.0
```

#### 3.1.3 Redis 配置（backend/core/config.py）

```python
import os
from redis import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def get_redis() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=True)

def get_checkpoint_saver():
    """Redis + Memory 双缓冲 CheckpointSaver"""
    from langgraph.checkpoint.redis import RedisSaver
    from langgraph.checkpoint.memory import MemorySaver

    redis_saver = RedisSaver(get_redis())
    # 双缓冲：写入Redis，同时保留内存缓存加速读取
    return MemorySaver(redis_saver)
```

---

### Phase 0.2：LangGraph 主图骨架

#### 3.2.1 MainState 定义（backend/agents/models/state.py）

```python
from typing import TypedDict, Optional
from datetime import datetime

class MainState(TypedDict):
    # ===== 任务标识 =====
    task_id: str
    task_type: str  # "topic_novelty_check" | "model_recommendation" | "analysis" | "writing"

    # ===== 执行状态 =====
    status: str  # "pending" | "running" | "interrupted" | "done" | "error"
    current_node: str  # "novelty" | "literature" | "analysis" | "brief" | "writing"
    error_message: Optional[str]

    # ===== 各节点结果 =====
    novelty_result: Optional[dict]  # {"overlap": [], "differentiation": [], "suggestions": []}
    literature_result: Optional[dict]
    analysis_result: Optional[dict]
    brief_result: Optional[dict]
    writing_result: Optional[dict]

    # ===== 中断相关 =====
    interrupt_reason: Optional[str]  # "novelty_result_ready" | "code_review" | etc
    interrupt_data: Optional[dict]  # 中断时展示给用户的数据

    # ===== 用户决策 =====
    human_decision: Optional[dict]  # {"decision": "approved", "modified_data": {...}}

    # ===== 元数据 =====
    created_at: str
    updated_at: str
```

#### 3.2.2 主图条件路由（backend/agents/orchestrator/main_graph.py）

```python
from langgraph.graph import StateGraph, END
from .models.state import MainState

def route_next_node(state: MainState) -> str:
    """根据当前状态决定下一个节点"""

    # 1. 检查是否中断
    if state["status"] == "interrupted":
        return "__interrupt__"  # LangGraph 内置中断节点

    # 2. 检查错误
    if state["status"] == "error":
        return END

    # 3. 节点路由
    current = state["current_node"]

    if current == "novelty":
        if state.get("novelty_result"):
            return "literature"
        return END

    if current == "literature":
        return "analysis"

    if current == "analysis":
        return "brief"

    if current == "brief":
        return "writing"

    if current == "writing":
        return END

    return END
```

#### 3.2.3 Novelty 节点实现

```python
def novelty_node(state: MainState) -> MainState:
    """
    Novelty 节点：选题查重与创新判断
    单一节点，内部不做子图细分（Phase 0 快速验证）
    """
    # TODO: 调用 paper-qa 进行文献检索
    # TODO: 比对已有论文，判断重复点和区分点
    # TODO: 生成推荐方向

    # 模拟输出（后续替换为真实逻辑）
    result = {
        "overlap": ["C-F-E耦合协调模型", "驱动机制分析"],
        "differentiation": ["趋势预测", "情景模拟"],
        "suggestions": ["基于ARIMA的短期预测", "Holt指数平滑法"]
    }

    # 中断：等待用户确认选题方向
    return {
        **state,
        "status": "interrupted",
        "interrupt_reason": "novelty_result_ready",
        "interrupt_data": result,
        "novelty_result": result,
        "updated_at": datetime.utcnow().isoformat()
    }
```

#### 3.2.4 图编译

```python
# 构建图
workflow = StateGraph(MainState)
workflow.add_node("novelty", novelty_node)
workflow.set_entry_point("novelty")
workflow.add_conditional_edges("novelty", route_next_node)
workflow.add_edge(END, END)

# 编译（带 CheckpointSaver）
checkpointer = get_checkpoint_saver()
graph = workflow.compile(checkpointer=checkpointer)
```

#### 3.2.5 Interrupt 处理机制

```
当状态为 interrupted 时，LangGraph 自动停在 __interrupt__ 节点
  → API 层检测到 status == "interrupted" 后，返回中断信息给前端
  → 用户点击"继续"后，API 调用 continue 端点，注入 human_decision
  → LangGraph 读取状态，根据 human_decision 决定下一步
```

---

### Phase 0.3：FastAPI 路由

#### 3.3.1 任务存储（backend/core/task_store.py）

```python
import json
from .config import get_redis

TASK_KEY_PREFIX = "task:"

def save_task_state(task_id: str, state: dict):
    """保存任务状态到 Redis Hash"""
    r = get_redis()
    key = f"{TASK_KEY_PREFIX}{task_id}"
    r.hset(key, mapping={
        "task_id": task_id,
        "status": state.get("status", "pending"),
        "current_node": state.get("current_node", ""),
        "interrupt_reason": state.get("interrupt_reason") or "",
        "updated_at": state.get("updated_at", ""),
    })
    # 完整状态存入 JSON 字段
    r.hset(key, "full_state", json.dumps(state))

def get_task_state(task_id: str) -> dict | None:
    """从 Redis Hash 读取任务状态"""
    r = get_redis()
    key = f"{TASK_KEY_PREFIX}{task_id}"
    data = r.hgetall(key)
    if not data:
        return None
    if data.get("full_state"):
        return json.loads(data["full_state"])
    return data
```

#### 3.3.2 API 路由（backend/api/routes.py）

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid
import json

router = APIRouter(prefix="/tasks", tags=["tasks"])

class CreateTaskRequest(BaseModel):
    task_type: str
    user_query: str
    files: list[str] = []

class ContinueTaskRequest(BaseModel):
    decision: str  # "approved" | "rejected" | "modified"
    modified_data: dict | None = None

@router.post("")
async def create_task(req: CreateTaskRequest):
    """创建新任务，立即返回 task_id，任务在后台异步运行"""
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # 初始化状态
    initial_state = {
        "task_id": task_id,
        "task_type": req.task_type,
        "status": "pending",
        "current_node": "novelty",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # 保存到 Redis
    save_task_state(task_id, initial_state)

    # 触发后台异步运行
    from backend.runner import run_task_async
    run_task_async(task_id, req.user_query, req.files)

    return {
        "task_id": task_id,
        "status": "running",
        "current_node": "novelty",
        "created_at": initial_state["created_at"]
    }

@router.get("/{task_id}")
async def get_task(task_id: str):
    """查询任务状态"""
    state = get_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")
    return state

@router.post("/{task_id}/continue")
async def continue_task(task_id: str, req: ContinueTaskRequest):
    """继续执行（处理中断）"""
    state = get_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")

    if state.get("status") != "interrupted":
        raise HTTPException(status_code=400, detail="Task is not interrupted")

    # 注入用户决策，更新状态继续执行
    state["human_decision"] = {
        "decision": req.decision,
        "modified_data": req.modified_data
    }
    state["status"] = "running"
    save_task_state(task_id, state)

    # 触发后续执行
    from backend.runner import resume_task_async
    resume_task_async(task_id)

    return {"task_id": task_id, "status": "running"}

@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    """SSE 流式状态推送"""
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        r = get_redis()
        pubsub = r.pubsub()
        channel = f"task_stream:{task_id}"
        pubsub.subscribe(channel)

        try:
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    yield {"event": "status", "data": message["data"]}

                # 检查任务是否结束
                state = get_task_state(task_id)
                if state and state.get("status") in ("done", "error"):
                    yield {"event": "done", "data": ""}
                    break
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return EventSourceResponse(event_generator())
```

#### 3.3.3 异步任务运行器（backend/runner.py）

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from .core.task_store import save_task_state, get_task_state, get_redis
from .agents.orchestrator.main_graph import graph

_executor = ThreadPoolExecutor(max_workers=4)

def run_task_async(task_id: str, user_query: str, files: list[str]):
    """在新线程中异步运行 LangGraph"""
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 初始化状态
            initial_state = {
                "task_id": task_id,
                "task_type": "topic_novelty_check",
                "status": "running",
                "current_node": "novelty",
                "novelty_result": None,
                "literature_result": None,
                "analysis_result": None,
                "brief_result": None,
                "writing_result": None,
                "interrupt_reason": None,
                "interrupt_data": None,
                "human_decision": None,
                "error_message": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # LangGraph 在后台线程中运行
            for state in graph.stream(
                initial_state,
                config={"configurable": {"thread_id": task_id}}
            ):
                # 每次状态变更都保存到 Redis
                save_task_state(task_id, state)
                # 通过 Redis Pub/Sub 推送 SSE
                r = get_redis()
                r.publish(f"task_stream:{task_id}", json.dumps(state))

                # 如果中断，停止等待
                if state.get("status") == "interrupted":
                    break
        finally:
            loop.close()

    _executor.submit(_run)

def resume_task_async(task_id: str):
    """从中断点恢复任务"""
    def _resume():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            state = get_task_state(task_id)
            if not state:
                return

            # 继续执行
            for new_state in graph.stream(
                state,
                config={"configurable": {"thread_id": task_id}}
            ):
                save_task_state(task_id, new_state)
                r = get_redis()
                r.publish(f"task_stream:{task_id}", json.dumps(new_state))

                if new_state.get("status") == "interrupted":
                    break
        finally:
            loop.close()

    _executor.submit(_resume)
```

---

### Phase 0.4：前端骨架

#### 3.4.1 任务详情页（frontend/src/app/workspace/[taskId]/page.tsx）

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

interface TaskState {
  task_id: string;
  status: "pending" | "running" | "interrupted" | "done" | "error";
  current_node: string;
  interrupt_reason: string | null;
  interrupt_data: {
    overlap: string[];
    differentiation: string[];
    suggestions: string[];
  } | null;
}

export default function WorkspacePage() {
  const params = useParams();
  const taskId = params.taskId as string;
  const [task, setTask] = useState<TaskState | null>(null);

  // SSE 连接
  useEffect(() => {
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`);

    eventSource.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      setTask(data);
    });

    eventSource.addEventListener("done", () => {
      eventSource.close();
    });

    return () => eventSource.close();
  }, [taskId]);

  // 继续执行
  const handleContinue = async (
    decision: "approved" | "rejected",
    modifiedData?: object
  ) => {
    await fetch(`/api/tasks/${taskId}/continue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, modified_data: modifiedData }),
    });
  };

  if (!task) return <div>Loading...</div>;

  return (
    <div className="p-6">
      {/* 状态展示 */}
      <div className="mb-4">
        <span className="px-3 py-1 rounded bg-blue-100 text-blue-800">
          {task.status}
        </span>
        <span className="ml-2 text-gray-600">
          当前节点: {task.current_node}
        </span>
      </div>

      {/* 中断时展示决策UI */}
      {task.status === "interrupted" &&
        task.interrupt_reason === "novelty_result_ready" && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="font-bold mb-2">请确认选题方向</h3>

            <div className="mb-4">
              <p className="font-semibold">与已有工作的重复点:</p>
              <ul className="list-disc pl-5">
                {task.interrupt_data?.overlap.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="mb-4">
              <p className="font-semibold">可区分点:</p>
              <ul className="list-disc pl-5">
                {task.interrupt_data?.differentiation.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="mb-4">
              <p className="font-semibold">推荐方向:</p>
              <ul className="list-disc pl-5">
                {task.interrupt_data?.suggestions.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => handleContinue("approved")}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                接受推荐方向
              </button>
              <button
                onClick={() => handleContinue("rejected")}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                拒绝（终止任务）
              </button>
            </div>
          </div>
        )}

      {/* 任务完成 */}
      {task.status === "done" && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="font-bold text-green-800">任务完成</h3>
          <p className="mt-2">
            novelty_result: {JSON.stringify(task.interrupt_data)}
          </p>
        </div>
      )}
    </div>
  );
}
```

#### 3.4.2 工作台首页（frontend/src/app/page.tsx）

```typescript
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);

  const handleCreateTask = async () => {
    const res = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: "topic_novelty_check",
        user_query: query,
        files: [],
      }),
    });
    const data = await res.json();
    setTaskId(data.task_id);
    router.push(`/workspace/${data.task_id}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6">科研多Agent助手</h1>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            研究问题或选题
          </label>
          <textarea
            className="w-full p-3 border rounded-lg"
            rows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例如：判断浙江省农业碳排放趋势预测是否与已有论文重复"
          />
        </div>

        <button
          onClick={handleCreateTask}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          创建任务
        </button>
      </div>
    </div>
  );
}
```

---

## 四、验收测试用例

| 测试编号 | 场景 | 预期结果 |
|----------|------|----------|
| TC-01 | POST /tasks 创建任务 | 返回 task_id，状态为 running |
| TC-02 | 任务运行后立即查询 | 状态应为 interrupted，interrupt_reason 应为 novelty_result_ready |
| TC-03 | SSE 连接 | 能接收到状态变更事件 |
| TC-04 | POST continue (approved) | 任务继续运行（后续节点待实现） |
| TC-05 | POST continue (rejected) | 任务终止，状态为 done |
| TC-06 | Redis 进程重启后 | 能通过 GET /tasks/{id} 恢复任务状态 |
| TC-07 | 无效 task_id 查询 | 返回 404 |

---

## 五、待实现内容（Phase 1+）

- [ ] paper-qa 真实调用替代模拟输出
- [ ] Literature Node 实现
- [ ] Analysis Node 实现
- [ ] Brief Builder Node 实现
- [ ] Writing Node 实现
- [ ] Text-to-Code Bridge
- [ ] Research_Brief Schema
- [ ] 完整 4 个中断点
- [ ] Code Interpreter 沙箱
- [ ] 评测基准建设

---

## 六、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/core/config.py` | Redis 连接 + CheckpointSaver 配置 |
| `backend/core/task_store.py` | Redis Hash 任务存储 |
| `backend/agents/models/state.py` | MainState 类型定义 |
| `backend/agents/orchestrator/main_graph.py` | LangGraph 主图 + 路由 |
| `backend/agents/orchestrator/subgraphs/novelty_node.py` | Novelty 节点 |
| `backend/api/routes.py` | FastAPI 路由 |
| `backend/api/schemas.py` | Pydantic 请求/响应模型 |
| `backend/runner.py` | 异步任务运行器 |
| `backend/main.py` | FastAPI 入口 |
| `frontend/src/app/page.tsx` | 工作台首页 |
| `frontend/src/app/workspace/[taskId]/page.tsx` | 任务详情页 |
| `requirements.txt` | Python 依赖 |
