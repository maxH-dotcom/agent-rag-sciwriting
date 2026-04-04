# Phase 2：安全与稳定性设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `Phase1-Text-to-Code-Bridge-设计文档.md`
> - `科研多Agent系统MVP实施计划.md`

---

## 一、Phase 2 目标

**目标**：异常不污染状态，断点续跑可靠

四大组成部分：
1. **沙箱隔离**：Pyodide 代码执行环境
2. **持久化**：CheckpointSaver Redis 完整配置
3. **错误处理**：错误分类 + 重试机制
4. **链路追踪**：结构化日志

---

## 二、Pyodide 沙箱隔离

### 2.1 Pyodide 选择理由

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| Pyodide | 部署简单，WebAssembly 隔离 | 功能受限，无网络 | **MVP 选择** |
| Docker | 功能完整，隔离强 | 部署复杂，冷启动慢 | 后续版本 |

**Pyodide 限制**：
- 无网络访问
- 无文件系统访问（临时目录除外）
- 内存限制 ~2GB
- CPU 限制

### 2.2 沙箱架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pyodide Sandbox Architecture                    │
│                                                                  │
│  ┌──────────────────┐                                            │
│  │  Code Execution  │                                            │
│  │    Service       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│     ┌─────┴─────┐                                                │
│     ▼           ▼                                                │
│  ┌──────┐  ┌──────────┐                                          │
│  │前端  │  │  后端    │                                          │
│  │Pyodide│  │Pyodide  │                                          │
│  │(浏览器)│  │(Python) │                                          │
│  └──────┘  └──────────┘                                          │
│                                                                  │
│  数据传递：                                                       │
│  - 代码 → 通过 API 传递                                          │
│  - 结果 → JSON 返回                                              │
│  - 数据文件 → 路径传递，Pyodide 读取                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 后端 Pyodide 服务

```python
# backend/core/sandbox/pyodide_service.py

import asyncio
import tempfile
import os
import json
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    MEMORY_LIMIT = "memory_limit"

@dataclass
class ExecutionResult:
    status: ExecutionStatus
    output: any
    error_message: str | None
    execution_time_ms: int
    memory_usage_mb: float | None

class PyodideService:
    """
    Pyodide 沙箱服务
    支持代码执行、结果返回、超时控制
    """

    def __init__(self, timeout_ms: int = 30000, memory_limit_mb: int = 512):
        self.timeout_ms = timeout_ms
        self.memory_limit_mb = memory_limit_mb
        self._pyodide = None
        self._initialized = False

    async def initialize(self):
        """初始化 Pyodide 运行时"""
        if self._initialized:
            return

        import micropip
        # 初始化 Pyodide
        import pyodide

        self._pyodide = pyodide
        self._micropip = micropip

        # 预安装常用包
        await self._install_packages([
            "numpy", "pandas", "scipy", "statsmodels"
        ])

        self._initialized = True

    async def _install_packages(self, packages: List[str]):
        """安装 Python 包"""
        for pkg in packages:
            try:
                await self._micropip.install(pkg)
            except Exception as e:
                print(f"Warning: Failed to install {pkg}: {e}")

    async def execute(
        self,
        code: str,
        data_files: List[str],
        context: Dict | None = None
    ) -> ExecutionResult:
        """
        执行代码
        """
        if not self._initialized:
            await self.initialize()

        import time
        start_time = time.time()

        try:
            # 设置超时
            async def run_with_timeout():
                # 准备数据文件到临时目录
                prepared_files = await self._prepare_data_files(data_files)

                # 添加数据文件路径到 context
                exec_globals = {
                    "__file__": prepared_files,
                    **context or {}
                }

                # 执行代码
                result = await self._pyodide.runPythonAsync(
                    self._wrap_code(code, prepared_files),
                    gl=exec_globals
                )

                return result

            # 超时控制
            output = await asyncio.wait_for(
                run_with_timeout(),
                timeout=self.timeout_ms / 1000
            )

            execution_time = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=output,
                error_message=None,
                execution_time_ms=execution_time,
                memory_usage_mb=None
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output=None,
                error_message=f"执行超时（{self.timeout_ms}ms）",
                execution_time_ms=self.timeout_ms,
                memory_usage_mb=None
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                output=None,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                memory_usage_mb=None
            )

    def _wrap_code(self, code: str, data_files: Dict[str, str]) -> str:
        """
        包装代码，添加数据加载和错误处理
        """
        wrapped = f"""
import sys
import traceback
import json

# 数据文件映射
DATA_FILES = {json.dumps(data_files)}

# 用户代码
{code}
"""
        return wrapped

    async def _prepare_data_files(self, data_files: List[str]) -> Dict[str, str]:
        """准备数据文件到 Pyodide 可访问的位置"""
        prepared = {}
        for file_path in data_files:
            if os.path.exists(file_path):
                # 读取文件内容并存储到 Pyodide 的虚拟文件系统
                with open(file_path, 'rb') as f:
                    content = f.read()
                prepared[file_path] = content
        return prepared
```

### 2.4 前端 Pyodide 集成

```typescript
// frontend/lib/pyodide-worker.ts

import { loadPyodide, PyodideInterface } from "pyodide";

let pyodide: PyodideInterface | null = null;

export async function initializePyodide() {
  if (pyodide) return pyodide;

  pyodide = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/",
  });

  // 预加载常用包
  await pyodide.loadPackage(["numpy", "pandas", "scipy"]);

  return pyodide;
}

export async function executeCode(
  code: string,
  dataFiles: Record<string, ArrayBuffer>
): Promise<{
  output: any;
  error?: string;
}> {
  const py = await initializePyodide();

  // 将数据文件写入 Pyodide 文件系统
  for (const [path, buffer] of Object.entries(dataFiles)) {
    const bytes = new Uint8Array(buffer);
    py.FS.writeFile(path, bytes);
  }

  try {
    const output = await py.runPythonAsync(code);
    return { output };
  } catch (error) {
    return { output: null, error: String(error) };
  }
}
```

### 2.5 安全检查清单

```python
# backend/core/sandbox/security.py

import re

class SecurityChecker:
    """
    代码安全检查
    """

    FORBIDDEN_PATTERNS = [
        # 文件系统
        (r"open\s*\([^)]*['\"][wr]", "禁止直接读写文件"),
        (r"os\.system", "禁止使用 os.system"),
        (r"subprocess", "禁止使用 subprocess"),
        (r"__import__", "禁止使用 __import__"),
        (r"import\s+os", "禁止导入 os 模块"),
        (r"import\s+sys", "禁止导入 sys 模块"),

        # 网络
        (r"urllib", "禁止使用网络请求"),
        (r"requests", "禁止使用网络请求"),
        (r"http", "禁止使用网络请求"),
        (r"socket", "禁止使用 socket"),

        # 代码执行
        (r"eval", "禁止使用 eval"),
        (r"exec", "禁止使用 exec"),
        (r"compile", "禁止使用 compile"),

        # 环境
        (r"os\. environ", "禁止访问环境变量"),
        (r"os\. getcwd", "禁止获取当前目录"),
        (r"os\. chdir", "禁止切换目录"),
    ]

    @classmethod
    def check(cls, code: str) -> tuple[bool, list[str]]:
        """
        检查代码安全性
        返回: (是否通过, 违规列表)
        """
        violations = []

        for pattern, message in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(message)

        return len(violations) == 0, violations
```

---

## 三、CheckpointSaver Redis 持久化

### 3.1 Redis 配置

```python
# backend/core/checkpoint/redis_checkpointer.py

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint import Checkpoint
import redis
import json
from datetime import datetime

class RedisCheckpointer(BaseCheckpointSaver):
    """
    Redis Checkpoint Saver
    实现 LangGraph 的 CheckpointSaver 接口
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.prefix = "langgraph:checkpoint"

    def _key(self, thread_id: str, checkpoint_id: str | None = None) -> str:
        """生成 Redis key"""
        if checkpoint_id:
            return f"{self.prefix}:{thread_id}:{checkpoint_id}"
        return f"{self.prefix}:{thread_id}:current"

    async def put(
        self,
        thread_id: str,
        checkpoint: Checkpoint,
        metadata: dict | None = None
    ) -> str:
        """
        保存 checkpoint
        """
        checkpoint_id = checkpoint.get("id", datetime.utcnow().isoformat())

        # 序列化 checkpoint
        data = {
            "checkpoint": checkpoint,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }

        # 存储 checkpoint
        key = self._key(thread_id, checkpoint_id)
        self.redis.set(key, json.dumps(data, default=str))

        # 更新 current 指针
        current_key = self._key(thread_id)
        self.redis.set(current_key, checkpoint_id)

        # 设置过期时间（7天）
        self.redis.expire(key, 7 * 24 * 3600)

        return checkpoint_id

    async def get(self, thread_id: str, checkpoint_id: str) -> Checkpoint | None:
        """
        获取指定 checkpoint
        """
        key = self._key(thread_id, checkpoint_id)
        data = self.redis.get(key)

        if not data:
            return None

        return json.loads(data).get("checkpoint")

    async def get_latest(self, thread_id: str) -> tuple[Checkpoint, str] | None:
        """
        获取最新的 checkpoint
        """
        current_key = self._key(thread_id)
        checkpoint_id = self.redis.get(current_key)

        if not checkpoint_id:
            return None

        checkpoint = await self.get(thread_id, checkpoint_id)
        if checkpoint:
            return checkpoint, checkpoint_id

        return None

    async def list(
        self,
        thread_id: str,
        limit: int = 10
    ) -> list[dict]:
        """
        列出 checkpoint 历史
        """
        pattern = f"{self.prefix}:{thread_id}:*"
        keys = self.redis.keys(pattern)

        checkpoints = []
        for key in keys[:limit]:
            data = self.redis.get(key)
            if data:
                parsed = json.loads(data)
                checkpoints.append({
                    "checkpoint_id": key.decode().split(":")[-1],
                    "created_at": parsed.get("created_at"),
                    "metadata": parsed.get("metadata", {})
                })

        return sorted(checkpoints, key=lambda x: x["created_at"], reverse=True)
```

### 3.2 LangGraph 集成

```python
# backend/agents/orchestrator/main_graph.py

from langgraph.graph import StateGraph
from langgraph.checkpoint import CheckpointConfig
from backend.core.checkpoint.redis_checkpointer import RedisCheckpointer

def build_main_graph():
    """构建主图"""
    workflow = StateGraph(MainState)

    # 添加节点和边...

    # Redis Checkpoint 配置
    checkpointer = RedisCheckpointer(redis_url="redis://localhost:6379")

    config = CheckpointConfig(
        checkpointer=checkpointer,
        checkpoint_policy="end_of_run",  # 每个节点执行后保存
    )

    return workflow.compile(checkpointer=config)
```

### 3.3 断点续跑 API

```python
# backend/api/routes.py

@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    """
    从 checkpoint 恢复任务
    """
    checkpointer = RedisCheckpointer()

    # 获取最新的 checkpoint
    result = await checkpointer.get_latest(task_id)

    if not result:
        raise HTTPException(status_code=404, detail="No checkpoint found")

    checkpoint, checkpoint_id = result

    # 使用 checkpoint 恢复图执行
    resumed_graph = build_main_graph()

    async for state in resumed_graph.astream(
        None,  # 输入为 None，使用 checkpoint 中的状态
        config={
            "configurable": {
                "thread_id": task_id,
                "checkpoint_id": checkpoint_id
            }
        }
    ):
        # 继续执行...
        pass

    return {"status": "resumed", "checkpoint_id": checkpoint_id}
```

---

## 四、错误分类与重试机制

### 4.1 错误分类

```python
# backend/core/error_classification.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorSeverity(str, Enum):
    RETRYABLE = "retryable"        # 可重试
    NON_RETRYABLE = "non_retryable"  # 不可重试
    FATAL = "fatal"              # 致命错误

@dataclass
class ErrorInfo:
    severity: ErrorSeverity
    category: str
    message: str
    retry_after_ms: int | None = None

ERROR_CLASSIFICATION = {
    # 网络错误 - 可重试
    "ConnectionError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="网络连接失败",
        retry_after_ms=1000
    ),
    "TimeoutError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="请求超时",
        retry_after_ms=2000
    ),
    "HTTPError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="HTTP 请求失败",
        retry_after_ms=1000
    ),

    # LLM 错误 - 可重试
    "RateLimitError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="llm",
        message="LLM 速率限制",
        retry_after_ms=5000
    ),
    "APIError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="llm",
        message="LLM API 错误",
        retry_after_ms=2000
    ),

    # 资源错误 - 可重试（有冷却时间）
    "MemoryError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="resource",
        message="内存不足",
        retry_after_ms=10000
    ),

    # 代码错误 - 不可重试
    "SyntaxError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="代码语法错误"
    ),
    "NameError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="变量未定义"
    ),

    # 沙箱错误 - 不可重试
    "SandboxTimeout": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="sandbox",
        message="沙箱执行超时"
    ),
    "SandboxMemoryLimit": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="sandbox",
        message="沙箱内存超限"
    ),

    # 致命错误 - 任务终止
    "FatalError": ErrorInfo(
        severity=ErrorSeverity.FATAL,
        category="system",
        message="系统致命错误"
    ),
}

def classify_error(error: Exception) -> ErrorInfo:
    """分类错误"""
    error_type = type(error).__name__

    if error_type in ERROR_CLASSIFICATION:
        return ERROR_CLASSIFICATION[error_type]

    # 默认：未知错误，标记为可重试一次
    return ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="unknown",
        message=str(error),
        retry_after_ms=1000
    )
```

### 4.2 重试装饰器

```python
# backend/core/retry.py

import asyncio
import functools
from typing import Callable, TypeVar, ParamSpec
from backend.core.error_classification import classify_error, ErrorSeverity

P = ParamSpec('P')
T = TypeVar('T')

def with_retry(
    max_attempts: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 30000
):
    """
    带重试的装饰器

    使用示例：
    @with_retry(max_attempts=3, base_delay_ms=1000)
    async def my_function():
        ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e
                    error_info = classify_error(e)

                    # 不可重试的错误，直接抛出
                    if error_info.severity in (
                        ErrorSeverity.NON_RETRYABLE,
                        ErrorSeverity.FATAL
                    ):
                        raise

                    # 达到最大重试次数
                    if attempt >= max_attempts - 1:
                        break

                    # 计算延迟时间（指数退避）
                    delay = error_info.retry_after_ms or base_delay_ms
                    delay = min(delay * (2 ** attempt), max_delay_ms)

                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}ms...")

                    await asyncio.sleep(delay / 1000)

            # 所有重试都失败
            raise last_error

        return wrapper
    return decorator
```

### 4.3 各工具层集成

```python
# backend/agents/tools/paperqa_wrapper.py

from backend.core.retry import with_retry

class PaperQATool:
    @with_retry(max_attempts=3, base_delay_ms=2000)
    async def retrieve(self, query: str, top_k: int = 5):
        """检索（带重试）"""
        # 实现...
        pass

    @with_retry(max_attempts=2, base_delay_ms=1000)
    async def index_paper(self, file_path: str):
        """索引（带重试）"""
        # 实现...
        pass


# backend/agents/tools/openalex_wrapper.py

class OpenAlexTool:
    @with_retry(max_attempts=3, base_delay_ms=1000)
    async def search_works(self, query: str, top_k: int = 10):
        """搜索（带重试）"""
        # 实现...
        pass


# backend/core/sandbox/pyodide_service.py

class PyodideService:
    @with_retry(max_attempts=2, base_delay_ms=5000)
    async def execute(self, code: str, data_files: List[str]):
        """执行代码（沙箱错误不重试）"""
        # 实现...
        pass
```

---

## 五、链路追踪结构化日志

### 5.1 日志架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Structured Logging Architecture               │
│                                                                  │
│  各 Node/工具 ──▶ Logger ──▶ JSON Formatter ──▶ 输出            │
│                                              │                   │
│                                              ▼                   │
│                                    ┌───────────────┐            │
│                                    │  Console      │            │
│                                    │  File         │            │
│                                    │  Redis        │            │
│                                    │  (可选)        │            │
│                                    └───────────────┘            │
│                                                                  │
│  日志格式：                                                      │
│  {                                                               │
│    "timestamp": "2026-04-04T10:00:00Z",                         │
│    "level": "INFO",                                             │
│    "task_id": "task_abc123",                                    │
│    "node": "novelty",                                           │
│    "event": "node_started",                                     │
│    "message": "Novelty node started",                           │
│    "duration_ms": 1234,                                         │
│    "metadata": {...}                                            │
│  }                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 日志配置

```python
# backend/core/logging/structured_logger.py

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for task_id
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)
node_var: ContextVar[str | None] = ContextVar("node", default=None)

class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),

            # Task context
            "task_id": task_id_var.get(),
            "node": node_var.get(),

            # Extra fields
            **getattr(record, "extra", {})
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    结构化日志记录器
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)

    def set_context(self, task_id: str, node: str | None = None):
        """设置日志上下文"""
        task_id_var.set(task_id)
        node_var.set(node)

    def clear_context(self):
        """清除日志上下文"""
        task_id_var.set(None)
        node_var.set(None)

    def log(self, level: str, event: str, message: str, **metadata):
        """记录日志"""
        extra = {"extra": {"event": event, **metadata}}
        getattr(self.logger, level.lower())(message, extra=extra)

    def info(self, event: str, message: str, **metadata):
        self.log("INFO", event, message, **metadata)

    def warning(self, event: str, message: str, **metadata):
        self.log("WARNING", event, message, **metadata)

    def error(self, event: str, message: str, **metadata):
        self.log("ERROR", event, message, **metadata)

    def debug(self, event: str, message: str, **metadata):
        self.log("DEBUG", event, message, **metadata)
```

### 5.3 各节点日志集成

```python
# backend/agents/orchestrator/subgraphs/novelty_node.py

from backend.core.logging.structured_logger import StructuredLogger

logger = StructuredLogger("novelty_node")

async def novelty_node(state: MainState) -> MainState:
    task_id = state["task_id"]
    logger.set_context(task_id, "novelty")

    try:
        logger.info("node_started", "Novelty node started", user_query=state["user_query"])

        # ... 节点逻辑 ...

        logger.info("node_completed", "Novelty node completed",
                   duration_ms=1234,
                   novelty_score=result["novelty_score"])

        return result

    except Exception as e:
        logger.error("node_failed", str(e), error_type=type(e).__name__)
        raise

    finally:
        logger.clear_context()
```

### 5.4 日志事件类型

```python
# backend/core/logging/events.py

# 节点事件
NODE_STARTED = "node_started"
NODE_COMPLETED = "node_completed"
NODE_FAILED = "node_failed"
NODE_INTERRUPTED = "node_interrupted"

# 工具事件
TOOL_CALLED = "tool_called"
TOOL_COMPLETED = "tool_completed"
TOOL_FAILED = "tool_failed"

# 任务事件
TASK_CREATED = "task_created"
TASK_STARTED = "task_started"
TASK_COMPLETED = "task_completed"
TASK_FAILED = "task_failed"
TASK_INTERRUPTED = "task_interrupted"
TASK_RESUMED = "task_resumed"

# 用户交互事件
HUMAN_DECISION = "human_decision"
HUMAN_FEEDBACK = "human_feedback"

# 性能事件
LATENCY_WARNING = "latency_warning"
MEMORY_WARNING = "memory_warning"
```

---

## 六、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/core/sandbox/pyodide_service.py` | Pyodide 沙箱服务 |
| `backend/core/sandbox/security.py` | 安全检查 |
| `backend/core/checkpoint/redis_checkpointer.py` | Redis Checkpoint |
| `backend/core/error_classification.py` | 错误分类 |
| `backend/core/retry.py` | 重试装饰器 |
| `backend/core/logging/structured_logger.py` | 结构化日志 |
| `backend/core/logging/events.py` | 日志事件类型 |
| `frontend/lib/pyodide-worker.ts` | 前端 Pyodide Worker |

---

## 七、部署配置

### 7.1 Redis 配置

```yaml
# docker-compose.yml

redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes

volumes:
  redis_data:
```

### 7.2 环境变量

```bash
# .env

REDIS_URL=redis://localhost:6379
PYODIDE_TIMEOUT_MS=30000
PYODIDE_MEMORY_LIMIT_MB=512
LOG_LEVEL=INFO
```

---

## 八、实施检查清单

### 沙箱隔离
- [ ] PyodideService 后端服务
- [ ] SecurityChecker 安全检查
- [ ] 前端 Pyodide Worker
- [ ] 沙箱测试用例

### Checkpoint 持久化
- [ ] RedisCheckpointer 实现
- [ ] LangGraph 集成
- [ ] 断点续跑 API
- [ ] Checkpoint 清理机制

### 错误处理
- [ ] ErrorClassification 分类
- [ ] @with_retry 装饰器
- [ ] 各工具层集成
- [ ] 错误监控

### 日志追踪
- [ ] StructuredLogger
- [ ] 各节点日志集成
- [ ] 日志查看工具
- [ ] 性能监控
