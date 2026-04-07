# AI Agent 应用工程师学习指南

> 本文档旨在帮助读者从零开始理解 AI Agent 应用的核心概念、架构设计与工程实现，最终具备独立搭建 AI Agent 应用的能力。

**阅读说明**：本文档按照由浅入深的顺序组织，每个章节都会从"基础概念"讲起，逐步深入到高级主题。建议按顺序阅读，但也可以根据目录跳转到感兴趣的部分。

---

## 目录

### 第一部分：计算机基础与网络概念

1. [客户端与服务器：什么是 API？](#1-客户端与服务器什么是-api)
2. [HTTP 协议：API 如何通信](#2-http-协议api-如何通信)
3. [RESTful API：互联网的"邮局系统"](#3-restful-api互联网的邮局系统)
4. [JSON：数据的"标准化包装"](#4-json数据的标准化包装)
5. [同步与异步：排队还是叫号？](#5-同步与异步排队还是叫号)

### 第二部分：Python 核心概念

6. [Python 基础回顾](#6-python-基础回顾)
7. [Pydantic：Python 世界的"质检员"](#7-pydanticpython-世界的质检员)
8. [类型注解：Type Hint](#8-类型注解type-hint)
9. [上下文管理器与 with 语句](#9-上下文管理器与-with-语句)

### 第三部分：Web 框架：FastAPI

10. [FastAPI 是什么？](#10-fastapi-是什么)
11. [路由与端点：系统的前台接待](#11-路由与端点系统的前台接待)
12. [请求体与响应体：数据的进出口](#12-请求体与响应体数据的进出口)
13. [中间件：请求的"过滤器"](#13-中间件请求的过滤器)
14. [FastAPI 的自动文档](#14-fastapi-的自动文档)

### 第四部分：数据库与状态管理

15. [文件持久化：最简单的方式](#15-文件持久化最简单的方式)
16. [Redis：内存中的"高速缓存"](#16-redis内存中的高速缓存)
17. [Repository 模式：数据存储的抽象](#17-repository-模式数据存储的抽象)
18. [状态机：工作流的"交通灯"](#18-状态机工作流的交通灯)

### 第五部分：AI Agent 核心概念

19. [LLM：大语言模型是什么？](#19-llm大语言模型是什么)
20. [Prompt：与 AI 沟通的语言](#20-prompt与-ai-沟通的语言)
21. [Agent（智能体）：能自主行动的 AI](#21-agent智能体能自主行动的-ai)
22. [Chain（链）：把多个步骤串起来](#22-chain链把多个步骤串起来)
23. [State（状态）：Agent 的"记忆本"](#23-state状态agent-的记忆本)

### 第六部分：LangGraph 框架

24. [LangGraph 是什么？](#24-langgraph-是什么)
25. [StateGraph：构建工作流的核心](#25-stategraph构建工作流的核心)
26. [Node（节点）：工作流中的"工作岗位"](#26-节点工作流中的工作岗位)
27. [Edge（边）：节点之间的"流水线"](#27-边节点之间的流水线)
28. [Interrupt（中断）：人为干预的"暂停键"](#28-中断人为干预的暂停键)
29. [Checkpoint（检查点）：游戏的"存档点"](#29-检查点游戏的存档点)

### 第七部分：系统设计模式

30. [编排器模式：交通警察架构](#30-编排器模式交通警察架构)
31. [管道与过滤器：工业流水线模式](#31-管道与过滤器工业流水线模式)
32. [发布-订阅：消息的"广播站"](#32-发布-订阅消息的广播站)
33. [Human-in-the-Loop：人在环中](#33-human-in-the-loop人在环中)

### 第八部分：安全与沙箱

34. [代码注入：危险的"特洛伊木马"](#34-代码注入危险的特洛伊木马)
35. [AST 解析：代码的"X光机"](#35-ast-解析代码的-x光机)
36. [沙箱执行：危险的"隔离室"](#36-沙箱执行危险的隔离室)
37. [白名单机制：信任的"白名单"](#37-白名单机制信任的白名单)

### 第九部分：实战项目架构分析

38. [项目整体架构](#38-项目整体架构)
39. [数据流设计：从请求到响应](#39-数据流设计从请求到响应)
40. [中断点设计：人的决策权](#40-中断点设计人的决策权)
41. [可扩展性设计：未来的"插拔式"升级](#41-可扩展性设计未来的插拔式升级)

### 第十部分：工程实践

42. [环境变量与配置管理](#42-环境变量与配置管理)
43. [错误处理与日志](#43-错误处理与日志)
44. [测试驱动开发](#44-测试驱动开发)
45. [API 版本管理与文档](#45-api-版本管理与文档)

---

## 第一部分：计算机基础与网络概念

### 1. 客户端与服务器：什么是 API？

#### 基础概念

**客户端（Client）**：主动发起请求的一方。就像餐厅里点菜的顾客。

**服务器（Server）**：被动等待请求、处理请求的一方。就像厨房里的厨师。

**API（Application Programming Interface）**：应用程序编程接口。就像餐厅的"点菜单"，规定了顾客可以用什么方式向厨房点菜。

#### 生活类比

```
你（客户端）打开外卖APP
    ↓
APP 显示餐厅菜单（API 文档）
    ↓
你选择菜品，点击下单（发送请求）
    ↓
餐厅厨房（服务器）收到订单，开始做菜
    ↓
菜品做好，外卖小哥送到你手上（返回响应）
```

#### 在本项目中的应用

```
浏览器/前端（客户端）
    ↓ 发送 HTTP 请求
FastAPI 后端（服务器）
    ↓ 处理请求
LangGraph 编排器（业务逻辑）
    ↓
Redis/文件存储（数据持久化）
```

---

### 2. HTTP 协议：API 如何通信

#### 什么是 HTTP？

HTTP（HyperText Transfer Protocol）是互联网上数据传输的"语言"。它规定了客户端和服务器如何"说话"。

#### HTTP 方法

| 方法 | 含义 | 用途 |
|------|------|------|
| **GET** | 获取资源 | 查询数据，不修改服务器状态 |
| **POST** | 创建资源 | 提交新数据 |
| **PUT** | 更新资源 | 替换整个资源 |
| **PATCH** | 部分更新 | 只更新部分字段 |
| **DELETE** | 删除资源 | 删除数据 |

#### 请求与响应结构

**HTTP 请求**：
```http
POST /tasks HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
User-Agent: Mozilla/5.0

{
    "task_type": "analysis",
    "user_query": "碳排放 农业"
}
```

**HTTP 响应**：
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "task_id": "task_abc123",
    "status": "running"
}
```

#### 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 创建成功 |
| 400 | Bad Request | 请求格式错误 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

---

### 3. RESTful API：互联网的"邮局系统"

#### 什么是 REST？

REST（Representational State Transfer）是一种设计 API 的规范。就像"邮局协议"规定了你写信的格式。

#### RESTful 设计原则

1. **资源命名**：使用名词，不用动词
   - ✅ `/tasks`（任务集合）
   - ❌ `/getTasks`

2. **HTTP 方法对应操作**
   - GET `/tasks` - 获取所有任务
   - GET `/tasks/{id}` - 获取某个任务
   - POST `/tasks` - 创建任务
   - DELETE `/tasks/{id}` - 删除任务

3. **使用 HTTP 状态码**

#### 本项目的 API 设计

```
POST   /tasks           # 创建新任务
GET    /tasks           # 列出所有任务
GET    /tasks/{id}      # 获取特定任务
POST   /tasks/{id}/continue  # 继续中断的任务
POST   /tasks/{id}/abort     # 终止任务
POST   /upload              # 上传文件
GET    /system/runtime      # 获取运行时信息
```

---

### 4. JSON：数据的"标准化包装"

#### 什么是 JSON？

JSON（JavaScript Object Notation）是一种轻量级的数据交换格式。就像把货物打包成标准箱子，方便运输和拆解。

#### JSON vs 其他格式

| 格式 | 特点 | 应用场景 |
|------|------|----------|
| JSON | 轻量、人类可读、键值对 | Web API |
| XML | 重量、标签复杂 | 传统企业系统 |
| CSV | 简单、表格数据 | 数据导出 |
| Protocol Buffers | 二进制、高效 | Google 内部 |

#### JSON 语法

```json
{
    "name": "智能科研助手",
    "version": "1.0.0",
    "features": [
        "文献检索",
        "代码生成",
        "论文写作"
    ],
    "config": {
        "max_file_size": 52428800,
        "allowed_types": [".csv", ".pdf"]
    }
}
```

#### Python 与 JSON

```python
import json

# Python 对象 → JSON 字符串
data = {"name": "张三", "age": 25}
json_string = json.dumps(data)  # '{"name": "张三", "age": 25}'

# JSON 字符串 → Python 对象
data = json.loads(json_string)  # {"name": "张三", "age": 25}
```

---

### 5. 同步与异步：排队还是叫号？

#### 同步（Synchronous）

**概念**：像在银行排队，必须等前一个人办完，下一个人才能开始。

**特点**：
- 按顺序执行
- 一个任务完成后才能开始下一个
- 代码简单直观

**示例**：
```python
# 同步执行：必须等待每个请求完成
result1 = api_call_1()  # 等 2 秒
result2 = api_call_2()  # 等 3 秒
result3 = api_call_3()  # 等 1 秒
# 总计：6 秒
```

#### 异步（Asynchronous）

**概念**：像在餐厅用"叫号器"，取完号可以玩手机，等叫号再去。

**特点**：
- 并发执行
- 提高效率
- 代码稍复杂

**示例**：
```python
import asyncio

async def main():
    # 异步执行：同时发起所有请求
    result1, result2, result3 = await asyncio.gather(
        api_call_1(),  # 发起请求1
        api_call_2(),  # 发起请求2
        api_call_3()   # 发起请求3
    )
    # 总计：max(2, 3, 1) = 3 秒
```

#### 在本项目中的应用

FastAPI 默认支持异步：
```python
@router.post("/tasks")
async def create_task(request: CreateTaskRequest):
    # async def 表示这是一个异步函数
    # 可以用 await 等待其他异步操作
    task = await some_async_operation()
    return task
```

---

## 第二部分：Python 核心概念

### 6. Python 基础回顾

#### 列表推导式

```python
# 传统写法
squares = []
for i in range(10):
    squares.append(i ** 2)

# 列表推导式（更简洁）
squares = [i ** 2 for i in range(10)]
```

#### 字典操作

```python
# 字典推导式
word_lengths = {word: len(word) for word in ["apple", "banana", "cherry"]}

# 字典的 get 方法（安全获取）
data = {"name": "张三", "age": 25}
city = data.get("city", "未知")  # 默认值 "未知"
```

#### 解包操作

```python
# 元组解包
x, y, z = (1, 2, 3)

# 字典解包
config = {"host": "localhost", "port": 8000}
server = {**config, "debug": True}  # 合并字典

# 函数参数解包
args = (1, 2, 3)
func(*args)

kwargs = {"name": "张三", "age": 25}
func(**kwargs)
```

#### 异常处理

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"除数不能为零: {e}")
except Exception as e:
    print(f"其他错误: {e}")
else:
    print("没有异常时执行")
finally:
    print("无论是否有异常都执行")
```

---

### 7. Pydantic：Python 世界的"质检员"

#### 什么是 Pydantic？

Pydantic 是一个数据验证库，能在数据进入程序前进行"质检"，确保数据格式正确。

#### 基本用法

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str                    # 必须字段，字符串
    age: int                     # 必须字段，整数
    email: str | None = None     # 可选字段，有默认值
    score: float = Field(default=0.0, ge=0, le=100)  # 范围限制

# 创建用户实例
user = User(name="张三", age=25)

# 自动验证
try:
    invalid_user = User(name="李四", age="不是数字")  # 会报错
except ValidationError as e:
    print(e)
```

#### 字段验证器

```python
from pydantic import BaseModel, field_validator

class Product(BaseModel):
    name: str
    price: float

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("价格必须为正数")
        return v
```

#### 在本项目中的应用

```python
# backend/api/schemas.py

class CreateTaskRequest(BaseModel):
    task_type: str = Field(default="analysis")
    user_query: str = Field(min_length=1, description="用户研究问题")
    data_files: List[str] = Field(default_factory=list)
    paper_files: List[str] = Field(default_factory=list)
```

---

### 8. 类型注解：Type Hint

#### 为什么需要类型注解？

1. **提高代码可读性**：一看就知道变量是什么类型
2. ** IDE 支持**：自动补全和错误检查
3. **文档作用**：代替部分注释

#### 基础类型注解

```python
# 简单类型
name: str = "张三"
age: int = 25
score: float = 98.5
is_active: bool = True

# 复杂类型
names: list[str] = ["张三", "李四"]
scores: dict[str, int] = {"数学": 90, "语文": 85}
tuple_data: tuple[int, str, float] = (1, "hello", 3.14)

# 可选类型
result: str | None = None
```

#### TypedDict：带键名的字典类型

```python
from typing import TypedDict

class MainState(TypedDict, total=False):
    task_id: str
    current_node: str
    status: str
    interrupt_reason: str | None
    result: dict[str, Any] | None
```

#### Protocol：结构化子类型

```python
from typing import Protocol

class TaskRepository(Protocol):
    """定义数据存储的接口"""
    backend_name: str

    def load_all(self) -> dict[str, dict[str, Any]]:
        ...

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        ...
```

---

### 9. 上下文管理器与 with 语句

#### 什么是上下文管理器？

上下文管理器确保资源在使用完毕后正确清理，就像"用完厕所要冲水"一样。

#### 经典例子：文件操作

```python
# 手动管理（容易忘记关闭）
f = open("file.txt", "r")
content = f.read()
f.close()  # 容易忘记！

# 上下文管理器（自动清理）
with open("file.txt", "r") as f:
    content = f.read()
# 文件自动关闭
```

#### 自定义上下文管理器

```python
class Timer:
    def __enter__(self):
        import time
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = time.time() - self.start
        print(f"耗时: {elapsed:.2f}秒")
        return False  # 不吞掉异常

# 使用
with Timer() as t:
    result = expensive_operation()
```

#### @contextmanager 装饰器

```python
from contextlib import contextmanager

@contextmanager
def timer():
    import time
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"耗时: {elapsed:.2f}秒")

# 使用
with timer():
    result = expensive_operation()
```

#### 在本项目中的应用

```python
# 使用锁的上下文管理器
with self.lock:
    self._tasks[task_id] = response
    self._save()
# 锁自动释放
```

---

## 第三部分：Web 框架：FastAPI

### 10. FastAPI 是什么？

#### 框架简介

FastAPI 是一个现代、快速的 Python Web 框架，用于构建 API。它具有以下特点：

| 特点 | 说明 |
|------|------|
| 高性能 | 与 Node.js 和 Go 相当 |
| 快速开发 | 自动数据验证 |
| 类型安全 | 完全类型注解支持 |
| 自动文档 | Swagger UI 自动生成 |

#### 安装与基本结构

```bash
pip install fastapi uvicorn
```

```python
from fastapi import FastAPI

app = FastAPI(title="我的API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
```

#### 启动服务器

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload`：代码修改后自动重启
- `--host 0.0.0.0`：允许外部访问
- `--port 8000`：端口号

---

### 11. 路由与端点：系统的前台接待

#### 路由的基本概念

路由（Route）定义了 URL 路径与处理函数之间的映射，就像公司的"前台转接表"。

#### HTTP 方法装饰器

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/items")           # 获取资源列表
def list_items():
    return [{"id": 1}, {"id": 2}]

@router.get("/items/{item_id}")  # 获取单个资源
def get_item(item_id: int):
    return {"id": item_id}

@router.post("/items")           # 创建资源
def create_item(item: dict):
    return {"created": item}

@router.put("/items/{item_id}")  # 更新资源
def update_item(item_id: int, item: dict):
    return {"updated": item}

@router.delete("/items/{item_id}")  # 删除资源
def delete_item(item_id: int):
    return {"deleted": item_id}
```

#### 路由参数

```python
# 路径参数
@router.get("/users/{user_id}")
def get_user(user_id: int):  # 自动类型转换
    return {"user_id": user_id}

# 查询参数
@router.get("/users")
def list_users(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

# 可选查询参数
@router.get("/search")
def search(q: str | None = None, category: str | None = None):
    return {"q": q, "category": category}
```

#### 路由前缀与标签

```python
router = APIRouter(prefix="/api/v1", tags=["用户"])

@router.get("/users")
def list_users():
    ...

@router.post("/users")
def create_user():
    ...
```

---

### 12. 请求体与响应体：数据的进出口

#### Pydantic 模型作为请求体

```python
from pydantic import BaseModel, Field
from typing import List

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: float = Field(..., gt=0)  # 必须大于 0
    tags: List[str] = []

@router.post("/items")
def create_item(item: Item):
    return item
```

#### 嵌套模型

```python
class Address(BaseModel):
    street: str
    city: str
    zipcode: str

class User(BaseModel):
    name: str
    email: str
    address: Address

@router.post("/users")
def create_user(user: User):
    return user
```

#### 响应模型

```python
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return {"id": user_id, "name": "张三", "email": "zhang@example.com"}
```

#### 状态码

```python
from fastapi import status

@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item
```

---

### 13. 中间件：请求的"过滤器"

#### 中间件的概念

中间件是在请求处理前后执行的函数，像"安检门"，每个请求都要过一遍。

#### 自定义中间件

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

#### CORS 中间件

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)
```

#### 在本项目中的应用

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 14. FastAPI 的自动文档

#### Swagger UI

访问 `http://127.0.0.1:8000/docs` 可以看到自动生成的交互式 API 文档。

#### ReDoc

访问 `http://127.0.0.1:8000/redoc` 可以看到另一种风格的文档。

#### OpenAPI JSON

访问 `http://127.0.0.1:8000/openapi.json` 可以获取 OpenAPI 规范的 JSON 表示。

#### 文档自定义

```python
app = FastAPI(
    title="智能科研助手 API",
    description="面向科研工作流的多 Agent 工作台后端",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

---

## 第四部分：数据库与状态管理

### 15. 文件持久化：最简单的方式

#### JSON 文件存储

```python
import json
from pathlib import Path

class FileTaskRepository:
    def __init__(self, path: Path):
        self.path = path

    def load_all(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save_all(self, tasks: dict) -> None:
        self.path.write_text(json.dumps(tasks, indent=2))
```

#### 优缺点

| 优点 | 缺点 |
|------|------|
| 简单直观 | 并发写入有风险 |
| 易于调试 | 数据量大了性能差 |
| 无依赖 | 无索引，查询慢 |

#### 在本项目中的应用

```python
# backend/core/config.py
TASK_STORE_PATH = RUNTIME_DIR / "tasks.json"
CHECKPOINT_STORE_PATH = RUNTIME_DIR / "checkpoints.json"

# backend/core/task_repository.py
class FileTaskRepository:
    backend_name = "file"

    def load_all(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
```

---

### 16. Redis：内存中的"高速缓存"

#### Redis 简介

Redis 是一个开源的内存数据结构存储，可以用作数据库、缓存和消息队列。

**特点**：
- 数据存储在内存中，读写速度极快（微秒级）
- 支持多种数据结构（字符串、哈希、列表、集合等）
- 可以持久化到磁盘

#### Redis 的数据结构

```python
# 字符串
redis.set("name", "张三")
name = redis.get("name")

# 哈希（适合存储对象）
redis.hset("user:1", mapping={"name": "张三", "age": "25"})
user = redis.hgetall("user:1")

# 列表
redis.lpush("queue", "task1", "task2")
task = redis.rpop("queue")
```

#### 发布-订阅模式

```python
# 发布者
redis.publish("channel_name", "message")

# 订阅者
pubsub = redis.pubsub()
pubsub.subscribe("channel_name")
message = pubsub.get_message()
```

#### 在本项目中的应用

```python
# backend/core/config.py
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

# backend/core/task_repository.py
class RedisTaskRepository:
    backend_name = "redis"

    def __init__(self, redis_url: str) -> None:
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key = "research_assistant:tasks"

    def load_all(self) -> dict[str, dict[str, Any]]:
        payload = self.redis.get(self.key)
        return json.loads(payload) if payload else {}

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        self.redis.set(self.key, json.dumps(tasks))
```

---

### 17. Repository 模式：数据存储的抽象

#### 什么是 Repository 模式？

Repository 模式将数据存储的细节抽象到一个接口后面，让业务代码不需要关心数据是从哪里来的。

#### 接口定义

```python
from typing import Protocol

class TaskRepository(Protocol):
    """任务存储的抽象接口"""
    backend_name: str

    def load_all(self) -> dict[str, dict[str, Any]]:
        ...

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        ...
```

#### 具体实现

```python
class FileTaskRepository:
    backend_name = "file"
    # ... 文件存储实现

class RedisTaskRepository:
    backend_name = "redis"
    # ... Redis 存储实现
```

#### 工厂函数

```python
def create_task_repository() -> TaskRepository:
    if TASK_REPOSITORY_BACKEND == "redis":
        return RedisTaskRepository(REDIS_URL)
    return FileTaskRepository(TASK_STORE_PATH)
```

#### 好处

1. **可替换性**：可以随时切换存储方式
2. **可测试性**：可以注入 mock 实现
3. **关注分离**：业务代码不关心存储细节

---

### 18. 状态机：工作流的"交通灯"

#### 什么是状态机？

状态机定义了对象可能处于的状态，以及状态之间的转换规则。

#### 任务状态流转

```
                    ┌─────────────┐
                    │   pending   │  (初始状态)
                    └──────┬──────┘
                           │ 开始执行
                           ▼
                    ┌─────────────┐
          ┌────────│   running   │────────┐
          │        └──────┬──────┘        │
          │               │               │
    用户终止          中断/暂停         发生错误
          │               │               │
          ▼               ▼               ▼
    ┌───────────┐   ┌─────────────┐   ┌────────┐
    │ aborted   │   │ interrupted │   │ error  │
    └───────────┘   └──────┬──────┘   └────────┘
                           │          用户继续
                           ▼               │
                    ┌─────────────┐        │
                    │   running   │────────┘
                    └──────┬──────┘
                           │ 完成
                           ▼
                    ┌─────────────┐
                    │    done     │  (终态)
                    └─────────────┘
```

#### 状态定义

```python
# backend/api/schemas.py
TaskStatus = Literal["pending", "running", "interrupted", "done", "error", "aborted"]
```

#### 状态转换规则

```python
class TaskStore:
    def create_task(self, request):
        # pending → running
        state["status"] = "running"

    def continue_task(self, task_id, request):
        if task["status"] != "interrupted":
            raise ValueError("Task is not interrupted")
        # interrupted → running
        task["status"] = "running"

    def abort_task(self, task_id, reason):
        # any → aborted
        task["status"] = "aborted"
```

---

## 第五部分：AI Agent 核心概念

### 19. LLM：大语言模型是什么？

#### 什么是 LLM？

LLM（Large Language Model）大语言模型是一种基于深度学习的 AI 模型，通过海量文本训练，能够理解和生成人类语言。

#### 工作原理（简化版）

1. **输入编码**：把文字转换成数字向量
2. ** transformer 处理**：通过注意力机制理解上下文
3. **输出解码**：生成下一个 token（词元）

#### 主流 LLM Provider

| Provider | 代表模型 | 特点 |
|----------|----------|------|
| OpenAI | GPT-4, GPT-3.5 | 性能强，生态完善 |
| Anthropic | Claude | 安全对齐好 |
| Google | Gemini | 多模态强 |
| Meta | Llama | 开源可本地部署 |
| DeepSeek | DeepSeek Chat | 性价比高 |
| Groq | Llama on Groq | 推理速度快 |

#### API 调用方式

```python
# OpenAI 风格
from openai import OpenAI

client = OpenAI(api_key="your-api-key")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ]
)
print(response.choices[0].message.content)
```

---

### 20. Prompt：与 AI 沟通的语言

#### 什么是 Prompt？

Prompt（提示词）是用户向 LLM 发送的指令或问题。好的 Prompt 能获得更准确的回答。

#### Prompt 工程基本技巧

**1. 明确角色**
```
❌ 不好：帮我写一首诗
✅ 好：作为一个古风诗人，请为中秋节写一首七言绝句
```

**2. 结构化输出**
```
✅ 好：请用以下 JSON 格式返回结果：
{
    "姓名": "",
    "年龄": "",
    "职业": ""
}
```

**3. Few-shot 示例**
```
✅ 好：把"你好"翻译成英文
示例：
- "谢谢" → "Thank you"
- "再见" → "Goodbye"
- "你好" →
```

**4. 链式思考（Chain of Thought）**
```
✅ 好：请分步骤计算：
1. 首先计算 15 + 27
2. 然后乘以 3
3. 最后减去 10
```

#### 在本项目中的应用

文献检索时的 Prompt：
```
根据以下研究问题，搜索相关学术文献中的研究方法：
研究问题：{user_query}

请返回：
1. 推荐的研究方法
2. 方法的适用场景
3. 相关的经典文献
```

---

### 21. Agent（智能体）：能自主行动的 AI

#### 什么是 Agent？

Agent 是能够自主感知环境、做出决策、执行动作的 AI 系统。与简单的"输入-输出"不同，Agent 具有：

| 能力 | 说明 |
|------|------|
| 感知 | 接收外部信息（用户输入、工具返回） |
| 决策 | 根据状态决定下一步行动 |
| 行动 | 调用工具、执行操作 |
| 记忆 | 保存上下文、历史 |

#### Agent 的架构

```
┌─────────────────────────────────────────┐
│                 Agent                    │
│                                         │
│  ┌─────────────┐    ┌─────────────┐   │
│  │   Memory    │◄──►│   Brain     │   │
│  │  (记忆)     │    │  (LLM)      │   │
│  └─────────────┘    └──────┬──────┘   │
│                            │           │
│                    ┌───────▼───────┐   │
│                    │   Actions     │   │
│                    │  (工具调用)    │   │
│                    └───────────────┘   │
└─────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────┬─────────────┐
              │  Tool 1     │  Tool 2     │
              │ (搜索)      │ (代码执行)   │
              └─────────────┴─────────────┘
```

#### ReAct 模式

ReAct（Reasoning + Acting）是一种让 Agent 思考和行动交替进行的方法：

```
Thought: 我需要搜索相关文献
Action: search(query="碳排放 农业面板数据")
Observation: 找到10篇相关文献
Thought: 第一篇文献提到STIRPAT模型
Action: extract_method_details(chunk_id="1")
...
```

---

### 22. Chain（链）：把多个步骤串起来

#### 什么是 Chain？

Chain 把多个 LLM 调用或操作串联起来，形成一个完整的工作流。

#### LangChain Expression Language (LCEL)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{domain}专家"),
    ("user", "解释{topic}")
])

chain = prompt | ChatOpenAI(model="gpt-4")
result = chain.invoke({"domain": "物理学", "topic": "相对论"})
```

#### Chain 的类型

| 类型 | 说明 | 应用 |
|------|------|------|
| LLMChain | LLM + Prompt | 简单问答 |
| RetrievalChain | 检索 + 问答 | RAG |
| ConversationalChain | 对话 + 记忆 | 聊天机器人 |
| SequentialChain | 顺序执行 | 多步骤任务 |

#### Sequential Chain 示例

```python
from langchain.chains import SequentialChain

chain = SequentialChain(
    chains=[chain1, chain2, chain3],
    input_variables=["input"],
    output_variables=["final_result"]
)

result = chain.invoke({"input": "数据文件路径"})
```

---

### 23. State（状态）：Agent 的"记忆本"

#### 什么是 State？

State 是 Agent 工作流中的"共享黑板"，所有步骤都在上面读写数据。

#### 为什么需要 State？

1. **共享数据**：多个步骤需要访问相同的数据
2. **追踪进度**：记录工作流执行到哪里
3. **支持恢复**：中断后能从断点继续

#### State 的设计

```python
from typing import TypedDict

class MainState(TypedDict, total=False):
    # 任务标识
    task_id: str
    task_type: str

    # 执行状态
    current_node: str
    status: str

    # 各节点结果
    data_mapping_result: dict | None
    literature_result: dict | None
    novelty_result: dict | None
    analysis_result: dict | None

    # 中断相关
    interrupt_reason: str | None
    interrupt_data: dict | None

    # 用户决策
    human_decision: dict | None
```

#### State 的流转

```
初始 State
    │
    ▼
Node A 执行 ──► State 更新（写入 result_a）
    │
    ▼
Node B 执行 ──► State 更新（读取 result_a，写入 result_b）
    │
    ▼
Node C 执行 ──► State 更新（读取 result_b，写入 result_c）
    │
    ▼
最终结果
```

---

## 第六部分：LangGraph 框架

### 24. LangGraph 是什么？

#### 框架简介

LangGraph 是 LangChain 团队开发的开源框架，专门用于构建有状态、多步骤的 AI Agent 工作流。

**官网**：https://langchain-ai.github.io/langgraph/

#### 核心概念

| 概念 | 说明 |
|------|------|
| Graph | 由节点和边组成的有向图 |
| State | 贯穿整个图的共享状态 |
| Node | 图中的处理节点 |
| Edge | 节点之间的连接 |
| Checkpoint | 状态快照，支持断点恢复 |

#### 与 LangChain 的区别

| 特性 | LangChain | LangGraph |
|------|-----------|-----------|
| 适用场景 | 简单 Chain | 复杂多步骤 Agent |
| 状态管理 | 无内置 | 原生支持 |
| 循环支持 | 需要特殊处理 | 原生支持 |
| 中断支持 | 无 | 内置 interrupt |
| Checkpoint | 无 | 支持 |

---

### 25. StateGraph：构建工作流的核心

#### 基本结构

```python
from langgraph.graph import StateGraph, END

# 定义状态
class AgentState(TypedDict):
    messages: list

# 创建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("node_name", my_function)

# 设置入口
workflow.set_entry_point("node_name")

# 设置结束点
workflow.add_edge("node_name", END)

# 编译
graph = workflow.compile()
```

#### 编译后的图

```python
# 查看图的结构
print(graph.get_graph().draw_ascii())
```

---

### 26. Node（节点）：工作流中的"工作岗位"

#### Node 的定义

Node 是一个函数，接收当前状态，返回更新后的状态。

```python
def my_node(state: AgentState) -> AgentState:
    # 读取状态
    current_messages = state["messages"]

    # 处理
    new_message = {"role": "assistant", "content": "Hello!"}

    # 返回更新后的状态
    return {"messages": current_messages + [new_message]}
```

#### 添加到图

```python
workflow.add_node("my_node", my_node)
```

#### 在本项目中的应用

```python
# backend/agents/orchestrator/subgraphs/data_mapping_node.py

def run(state: MainState) -> MainState:
    # 读取输入
    data_files = state.get("data_files") or []

    # 处理
    columns = read_csv_columns(data_files[0])

    # 写入结果
    state["data_mapping_result"] = {"columns": columns}

    # 设置中断
    state["status"] = "interrupted"
    state["interrupt_reason"] = "data_mapping_required"

    return state
```

---

### 27. Edge（边）：节点之间的"流水线"

#### 边的基础

```python
# 直接边 - A 完成后直接去 B
workflow.add_edge("A", "B")

# 入口 - 从哪里开始
workflow.set_entry_point("A")

# 结束 - 到哪里结束
workflow.add_edge("B", END)
```

#### 条件边

根据状态决定下一步走哪个节点：

```python
def route_decision(state: AgentState) -> str:
    if state["confidence"] > 0.8:
        return "high_confidence_path"
    else:
        return "low_confidence_path"

workflow.add_conditional_edges(
    "evaluate",
    route_decision,
    {
        "high_confidence_path": "execute_action",
        "low_confidence_path": "ask_human"
    }
)
```

#### 在本项目中的应用

```python
# backend/agents/orchestrator/main_graph.py

def _next_node(self, current_node: str) -> str | None:
    """根据当前节点返回下一个节点"""
    try:
        index = NODE_SEQUENCE.index(current_node)
    except ValueError:
        return None
    next_index = index + 1
    return NODE_SEQUENCE[next_index] if next_index < len(NODE_SEQUENCE) else None

def run_until_pause(self, state: MainState, resume: bool = False) -> MainState:
    working = deepcopy(state)

    if resume:
        working = self._prepare_resume(working)

    while True:
        node_name = working["current_node"]
        handler = self.node_map[node_name]
        working = handler(working)

        # 检查是否需要暂停
        if working["status"] in {"interrupted", "done", "error", "aborted"}:
            return working

        # 移动到下一个节点
        next_node = self._next_node(node_name)
        if next_node is None:
            return working
        working["current_node"] = next_node
```

---

### 28. Interrupt（中断）：人为干预的"暂停键"

#### 什么是 Interrupt？

Interrupt 是 LangGraph 提供的中断机制，可以在节点执行后暂停工作流，等待人工确认后再继续。

#### 工作原理

```
Node A 执行 ──► 发现需要确认 ──► status="interrupted"
                                        │
                                        ▼
                                等待用户决策
                                        │
                                        ▼
用户确认 ──► 注入 human_decision ──► 继续执行
```

#### 在 LangGraph 中的实现

LangGraph 使用 `Command(interrupt=True)` 来暂停：

```python
from langgraph.types import Command

def my_node(state: AgentState) -> Command:
    # 处理逻辑...

    # 中断，等待确认
    return Command(
        interrupt=True,
        update={
            "status": "interrupted",
            "interrupt_reason": "need_approval",
            "interrupt_data": {"options": ["A", "B"]}
        }
    )
```

#### 在本项目中的实现

项目使用自定义的编排器，interrupt 通过状态标志实现：

```python
# backend/agents/orchestrator/subgraphs/data_mapping_node.py

def run(state: MainState) -> MainState:
    # ... 处理逻辑 ...

    # 状态设置为中断
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "data_mapping_required"
    state["interrupt_data"] = {
        "recommended_mapping": mapping,
        "message": "请先确认变量映射"
    }
    return state
```

---

### 29. Checkpoint（检查点）：游戏的"存档点"

#### 什么是 Checkpoint？

Checkpoint 是工作流状态的快照，保存后可以随时恢复，就像游戏的存档功能。

#### 为什么需要 Checkpoint？

1. **断点续跑**：任务中断后可以从断点继续
2. **故障恢复**：程序崩溃后能恢复到之前的状态
3. **并发支持**：同一个工作流可以有多个"存档"

#### LangGraph Checkpoint

```python
from langgraph.checkpoint.memory import MemorySaver

# 创建带 Checkpoint 的图
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# 执行并自动保存 Checkpoint
config = {"configurable": {"thread_id": "task_123"}}
for state in graph.stream(initial_state, config=config):
    # 每次状态变化都会自动保存
    pass

# 从 Checkpoint 恢复
for state in graph.stream(None, config=config):
    # 从上次中断的地方继续
    pass
```

#### 在本项目中的应用

```python
# backend/core/task_store.py

class TaskStore:
    def _append_checkpoint(self, task_id: str, state: dict, *, event: str) -> None:
        """保存检查点"""
        checkpoints = list(self._checkpoints.get(task_id) or [])
        checkpoints.append({
            "event": event,
            "timestamp": now_iso(),
            "current_node": state.get("current_node"),
            "status": state.get("status"),
            "interrupt_reason": state.get("interrupt_reason"),
        })
        self._checkpoints[task_id] = checkpoints

    def get_checkpoints(self, task_id: str) -> list[dict]:
        """获取所有检查点"""
        return list(self._checkpoints.get(task_id) or [])
```

---

## 第七部分：系统设计模式

### 30. 编排器模式：交通警察架构

#### 什么是编排器模式？

编排器（Orchestrator）是一个中心组件，负责协调其他组件的工作，决定执行顺序，处理异常。

#### 与直接调用的区别

| 直接调用 | 编排器模式 |
|----------|------------|
| A → B → C（硬编码） | Orchestrator → A/B/C |
| 耦合度高 | 解耦 |
| 逻辑分散 | 逻辑集中 |
| 难以修改顺序 | 顺序可配置 |

#### 类比

```
🚦 交通警察（编排器）🚦

交警指挥车辆（组件）
- 决定哪辆车先走（执行顺序）
- 处理交通事故（异常处理）
- 协调多方向车流（并发控制）

vs

🚗🚗🚗 直接行驶（直接调用）
- 每辆车自己决定什么时候走
- 容易堵车和事故
```

#### 在本项目中的应用

```python
# backend/agents/orchestrator/main_graph.py

class ResearchAssistantOrchestrator(BaseResearchRuntime):
    def __init__(self) -> None:
        self.node_map = {
            "data_mapping": data_mapping_node.run,
            "literature": literature_node.run,
            "novelty": novelty_node.run,
            "analysis": analysis_node.run,
            "brief": brief_builder_node.run,
            "writing": writing_node.run,
        }

    def run_until_pause(self, state: MainState, resume: bool = False) -> MainState:
        # 编排器决定执行顺序和流程
        while True:
            node_name = working["current_node"]
            handler = self.node_map[node_name]
            working = handler(working)

            if working["status"] in {"interrupted", "done", "error", "aborted"}:
                return working

            next_node = self._next_node(node_name)
            if next_node is None:
                return working
            working["current_node"] = next_node
```

---

### 31. 管道与过滤器：工业流水线模式

#### 什么是管道与过滤器？

数据像产品一样，在流水线上经过一系列"过滤器"处理，每个过滤器完成一个特定任务。

#### 架构图

```
原始数据 ──► [过滤器A] ──► [过滤器B] ──► [过滤器C] ──► 最终结果
              数据清洗      格式转换      数据验证
```

#### 优点

1. **单一职责**：每个过滤器只做一件事
2. **可组合**：可以自由组合过滤器
3. **可替换**：可以替换某个过滤器而不影响其他
4. **并行处理**：某些过滤器可以并行执行

#### 在本项目中的应用

```
用户数据
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph 主图                             │
│                                                              │
│  data_mapping ──► literature ──► novelty ──► analysis ──► ... │
│       │              │            │            │            │
│   CSV解析        文献检索      创新判断     代码生成          │
│       │              │            │            │            │
│   变量映射      证据提取      迁移评估     沙箱执行          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 32. 发布-订阅：消息的"广播站"

#### 什么是发布-订阅？

发布-订阅（Pub/Sub）是一种消息传递模式，发布者和订阅者不直接通信，而是通过一个"中间人"（消息代理）传递消息。

#### 架构图

```
    ┌─────────────┐
    │  Publisher  │  (发布者)
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   Broker    │  (消息代理/广播站)
    │  (Redis)    │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│Subscriber│ │Subscriber│  (订阅者)
│   A      │ │   B      │
└─────────┘ └─────────┘
```

#### Redis Pub/Sub

```python
# 发布者
redis.publish("task_events", json.dumps({"type": "status_update", "task_id": "123"}))

# 订阅者
pubsub = redis.pubsub()
pubsub.subscribe("task_events")
for message in pubsub.listen():
    print(message["data"])
```

#### 在本项目中的应用

当任务状态变化时，后端通过 Redis 发布消息，前端订阅获取实时更新：

```python
# SSE 端点（后端订阅 Redis 频道）
@router.get("/tasks/{task_id}/stream")
async def stream_task_status(task_id: str, request: Request):
    async def event_generator():
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"task:{task_id}:events")

        while True:
            message = await pubsub.get_message()
            if message:
                yield {"event": "update", "data": message["data"]}

            if await request.is_disconnected():
                break

    return StreamingResponse(event_generator())
```

---

### 33. Human-in-the-Loop：人在环中

#### 什么是 Human-in-the-Loop？

Human-in-the-Loop (HITL) 是一种让人类参与 AI 决策过程的方法，AI 生成结果，人类审核确认。

#### 为什么需要 HITL？

| 场景 | 没有 HITL | 有 HITL |
|------|-----------|--------|
| 错误发现 | 事后才发现 | 实时审核 |
| 纠错成本 | 高（可能要重来） | 低（中断即可修改） |
| 用户信任 | 低 | 高 |
| 责任明确 | 模糊 | 清晰 |

#### 在本项目中的应用

```
[中断0] 数据映射确认
用户选择：因变量(Y)、自变量(X)、控制变量

[中断1] 创新性确认
用户选择：接受/修改/拒绝迁移方向

[中断2] 代码审核
用户选择：执行/修改/跳过代码

[中断3] Research Brief 确认
用户编辑：修改研究目标、方法选择等

[中断4] 论文草稿确认
用户选择：接受/修改/重新生成
```

---

## 第八部分：安全与沙箱

### 34. 代码注入：危险的"特洛伊木马"

#### 什么是代码注入？

代码注入是将恶意代码通过输入字段植入程序的过程。

#### 常见注入类型

**1. SQL 注入**
```sql
-- 正常输入
SELECT * FROM users WHERE name = '张三'

-- 注入攻击
SELECT * FROM users WHERE name = ''; DROP TABLE users; --'
```

**2. Shell 注入**
```python
# 正常
os.system("ls -l /home/user")

# 注入攻击
# 用户输入: ; rm -rf /
os.system("ls -l /home/user; rm -rf /")
```

**3. Eval/Exec 注入**
```python
# 危险！
user_input = "os.system('rm -rf /')"
eval(user_input)  # 执行了恶意代码
```

#### 防御措施

1. **参数化查询**：使用预编译的语句
2. **输入验证**：白名单验证
3. **避免动态执行**：不用 eval/exec
4. **最小权限原则**：不给不必要的权限

---

### 35. AST 解析：代码的"X光机"

#### 什么是 AST？

AST（Abstract Syntax Tree，抽象语法树）是代码结构的树状表示。通过解析 AST 可以"看透"代码的真正意图。

#### AST 示例

```python
import ast

code = """
import os
result = os.system('ls')
"""

tree = ast.parse(code)

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        print(f"导入模块: {[alias.name for alias in node.names]}")
    elif isinstance(node, ast.Call):
        print(f"调用函数: {ast.unparse(node.func)}")
```

#### 在本项目中的应用

```python
# backend/core/sandbox.py

def check_code(code: str) -> CodeCheckResult:
    errors: list[str] = []

    # 1. 语法检查
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        errors.append(f"语法错误: {exc.msg}")
        return CodeCheckResult(passed=False, errors=errors)

    # 2. 遍历 AST，检查导入
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_import(alias.name, errors)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _check_import(node.module, errors)

    return CodeCheckResult(passed=len(errors) == 0, errors=errors)

FORBIDDEN_PATTERNS = [
    (r"\bos\.system\b", "禁止使用 os.system"),
    (r"\bsubprocess\b", "禁止使用 subprocess"),
    (r"\beval\s*\(", "禁止使用 eval()"),
    (r"\bexec\s*\(", "禁止使用 exec()"),
]
```

---

### 36. 沙箱执行：危险的"隔离室"

#### 什么是沙箱？

沙箱是一个隔离的执行环境，程序在沙箱里运行，对系统的影响被限制在沙箱内部。

#### 沙箱技术

| 技术 | 说明 |
|------|------|
| Docker 容器 | 操作系统级隔离 |
| VM | 完整虚拟机隔离 |
| Pyodide | WebAssembly 沙箱 |
| subprocess | 进程级隔离 |

#### 在本项目中的应用

```python
# backend/core/sandbox.py

def execute_in_sandbox(
    code: str,
    data_files: list[str] | None = None,
    timeout: int = 60,
) -> ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:
        # 1. 符号链接数据文件
        for fpath in data_files or []:
            dst = Path(tmpdir) / Path(fpath).name
            dst.symlink_to(Path(fpath).resolve())

        # 2. 写入脚本
        script_path = Path(tmpdir) / "_analysis.py"
        script_path.write_text(code)

        # 3. 限制环境变量
        env = {
            "PATH": "/usr/bin:/usr/local/bin",
            "HOME": tmpdir,
            "TMPDIR": tmpdir,
            "LANG": "en_US.UTF-8",
        }

        # 4. 执行（带有超时保护）
        proc = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            timeout=timeout,
            env=env,
        )

        return ExecutionResult(
            success=proc.returncode == 0,
            stdout=proc.stdout.decode(),
            stderr=proc.stderr.decode(),
        )
```

#### 沙箱安全措施

1. **临时目录**：在临时目录中运行，不影响原文件
2. **环境隔离**：最小化环境变量
3. **超时保护**：防止无限循环
4. **输出限制**：防止内存耗尽

---

### 37. 白名单机制：信任的"白名单"

#### 什么是白名单？

白名单是"只允许这些"的机制，与黑名单（"禁止这些"的机制）相对。

#### 在本项目中的应用

```python
# 允许的导入前缀
ALLOWED_IMPORT_PREFIXES = {
    "pandas", "numpy", "scipy", "statsmodels", "sklearn",
    "matplotlib", "seaborn", "linearmodels",
    "math", "statistics", "collections", "itertools",
    "json", "csv", "io", "typing", "dataclasses",
    "warnings", "functools", "operator", "decimal",
    "pathlib",
}

def _check_import(module_name: str, errors: list[str]) -> None:
    top_level = module_name.split(".")[0]
    if top_level not in ALLOWED_IMPORT_PREFIXES:
        errors.append(f"禁止导入模块: {module_name}")
```

#### 白名单 vs 黑名单

| 方面 | 白名单 | 黑名单 |
|------|--------|--------|
| 安全性 | 更高（默认拒绝） | 较低（可能遗漏） |
| 维护成本 | 较高（需要列举所有允许项） | 较低 |
| 适用场景 | 高安全要求 | 快速实现 |

---

## 第九部分：实战项目架构分析

### 38. 项目整体架构

#### 架构分层图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                            │
│    任务创建表单 │ 状态展示 │ 中断审核 UI │ 结果查看               │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI (Web 层)                            │
│         @router POST/GET │ SSE │ 文件上传 │ 中间件              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TaskStore (业务编排层)                        │
│     create_task │ continue_task │ abort_task │ 状态管理          │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Orchestrator    │ │ TaskRepository  │ │ CheckpointRepo  │
│ (LangGraph/自研)│ │ (File/Redis)   │ │ (File/Redis)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    6 个 Node (处理节点)                          │
│  data_mapping │ literature │ novelty │ analysis │ brief │ writing│
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      工具层 (Tools)                              │
│   文献检索 │ 问题解析 │ 代码生成 │ 沙箱执行 │ 模型推荐            │
└─────────────────────────────────────────────────────────────────┘
```

#### 目录结构

```
backend/
├── agents/                    # AI Agent 核心
│   ├── models/               # 数据模型（State, Schema）
│   ├── orchestrator/        # 编排器
│   │   ├── main_graph.py    # 主图/编排逻辑
│   │   └── subgraphs/       # 各个 Node 实现
│   └── tools/               # 工具层
│       ├── literature_search.py  # 文献检索
│       ├── question_parser.py    # 问题解析
│       └── paperqa_wrapper.py    # paper-qa 封装
├── api/                      # FastAPI 路由层
│   ├── routes.py            # API 端点
│   └── schemas.py           # 请求/响应模型
└── core/                     # 核心基础设施
    ├── config.py            # 配置管理
    ├── task_store.py        # 任务存储
    ├── task_repository.py   # Repository 模式
    ├── checkpoint_repository.py
    └── sandbox.py           # 代码沙箱
```

---

### 39. 数据流设计：从请求到响应

#### 完整请求流程

```
1. 用户发起请求
   POST /tasks
   {
       "task_type": "analysis",
       "user_query": "碳排放 农业 面板数据",
       "data_files": ["/path/to/data.csv"]
   }
       │
       ▼
2. FastAPI 路由层接收
   routes.py::create_task()
       │
       ▼
3. 创建 TaskStore
   验证请求 Schema
       │
       ▼
4. 生成唯一 task_id
   task_abc123def456
       │
       ▼
5. 调用 Orchestrator
   orchestrator.create_initial_state()
       │
       ▼
6. 执行第一个 Node
   data_mapping_node.run(state)
       │
       ├── 读取 CSV 文件
       ├── 解析列名
       ├── 识别面板结构
       │
       ▼
7. 状态设置为中断
   state["status"] = "interrupted"
   state["interrupt_reason"] = "data_mapping_required"
       │
       ▼
8. 保存到 Repository
   save_task_state(task_id, state)
       │
       ▼
9. 返回响应
   {
       "task_id": "task_abc123def456",
       "status": "interrupted",
       "interrupt_reason": "data_mapping_required",
       "interrupt_data": {...}
   }
```

#### continue_task 流程

```
1. 用户确认中断
   POST /tasks/{id}/continue
   {
       "decision": "approved",
       "payload": {"variable_mapping": {...}}
   }
       │
       ▼
2. 获取之前保存的状态
   state = get_task_state(task_id)
       │
       ▼
3. 注入用户决策
   state["human_decision"] = {...}
       │
       ▼
4. 恢复执行
   orchestrator.run_until_pause(state, resume=True)
       │
       ▼
5. 从下一个 Node 继续
   literature_node.run(state)
       │
       ▼
6. 依次执行后续 Node
   ...
       │
       ▼
7. 再次中断或完成
   state["status"] = "interrupted" | "done"
       │
       ▼
8. 保存状态，返回响应
```

---

### 40. 中断点设计：人的决策权

#### 5 个中断点详解

| 中断点 | 触发时机 | 用户操作 | 后续影响 |
|--------|----------|----------|----------|
| **数据映射** | 上传数据后 | 确认因变量/自变量/控制变量 | 所有分析基于此映射 |
| **文献审核** | 文献检索后 | 确认文献/方法 | 代码生成依据 |
| **创新判断** | 迁移评估后 | 确认迁移方向 | 后续方法选择 |
| **代码审核** | 代码生成后 | 确认/修改/执行代码 | 后续分析结果 |
| **Brief确认** | Brief 生成后 | 确认/修改研究卡 | 论文写作内容 |

#### 中断数据结构

```python
{
    "status": "interrupted",
    "interrupt_reason": "data_mapping_required",
    "interrupt_data": {
        "file_name": "carbon_data.csv",
        "detected_columns": ["地区", "年份", "碳排放", "农业产值"],
        "recommended_mapping": {
            "dependent_var": "碳排放",
            "independent_vars": ["农业产值"],
            "control_vars": [],
            "entity_column": "地区",
            "time_column": "年份"
        }
    },
    "next_action": "await_human_confirmation"
}
```

#### 用户决策处理

```python
# continue_task 中的决策处理
def continue_task(self, task_id: str, request: ContinueTaskRequest) -> dict:
    state = self.orchestrator.from_task_response(task)

    # approved：接受当前建议，继续
    if request.decision == "approved":
        pass  # 直接继续

    # modified：用户修改了参数
    elif request.decision == "modified":
        state = apply_human_payload(state, request.payload)

    # rejected：用户拒绝，终止任务
    elif request.decision == "rejected":
        state["status"] = "aborted"
        return state

    # 继续执行
    final_state = self.orchestrator.run_until_pause(state, resume=True)
    return self.orchestrator.to_task_response(final_state)
```

---

### 41. 可扩展性设计：未来的"插拔式"升级

#### LLM Provider 可切换

```python
# backend/core/llm_config.py

class LLMConfig:
    providers = {
        "openai": {"name": "OpenAI", "default_model": "gpt-4"},
        "groq": {"name": "Groq", "default_model": "llama-3.3-70b-versatile"},
        "deepseek": {"name": "DeepSeek", "default_model": "deepseek-chat"},
        # 未来可添加更多...
    }

    def get_llm(self):
        if self.current_provider == "groq":
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key
            )
        elif self.current_provider == "deepseek":
            return ChatOpenAI(
                base_url="https://api.deepseek.com",
                api_key=self.api_key
            )
        # ...
```

#### Repository 可切换

```python
# 配置文件
TASK_REPOSITORY_BACKEND=file  # 或 redis

# 工厂函数
def create_task_repository() -> TaskRepository:
    if TASK_REPOSITORY_BACKEND == "redis":
        return RedisTaskRepository(REDIS_URL)
    return FileTaskRepository(TASK_STORE_PATH)
```

#### Node 可扩展

```python
# 只需在 node_map 中添加新节点
class BaseResearchRuntime:
    def __init__(self) -> None:
        self.node_map: Dict[str, Callable] = {
            "data_mapping": data_mapping_node.run,
            "literature": literature_node.run,
            "novelty": novelty_node.run,
            "analysis": analysis_node.run,
            "brief": brief_builder_node.run,
            "writing": writing_node.run,
            # 新增节点，只需在这里添加
            # "new_feature": new_feature_node.run,
        }

# 在 NODE_SEQUENCE 中添加顺序
NODE_SEQUENCE = [
    "data_mapping",
    "literature",
    "novelty",
    "analysis",
    "brief",
    "writing",
    # "new_feature",  # 新增
]
```

---

## 第十部分：工程实践

### 42. 环境变量与配置管理

#### 为什么需要环境变量？

| 方面 | 硬编码 | 环境变量 |
|------|--------|----------|
| 安全性 | API Key 暴露在代码中 | 敏感信息不提交到 Git |
| 灵活性 | 修改需要改代码 | 换环境只需改配置 |
| 可移植性 | 只在开发环境工作 | 不同环境不同配置 |

#### .env 文件

```bash
# .env 文件（不要提交到 Git！）
DATABASE_URL=postgres://user:password@localhost/db
API_KEY=sk-xxxxxxxxxxxxx
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
```

#### Python 中读取环境变量

```python
import os

# 基本读取
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 必需变量（不存在则报错）
api_key = os.environ["API_KEY"]

# 布尔值
debug = os.getenv("DEBUG", "false").lower() == "true"
```

#### 在本项目中的应用

```python
# backend/core/config.py

import os
from pathlib import Path

# 文件路径配置
RUNTIME_DIR = Path(".runtime")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(RUNTIME_DIR / "uploads")))

# 后端配置
TASK_REPOSITORY_BACKEND = os.environ.get("TASK_REPOSITORY_BACKEND", "file")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

# Zotero 配置（从配置文件读取）
def _load_zotero_key() -> str:
    if api_key := os.environ.get("ZOTERO_API_KEY"):
        return api_key
    config_path = Path.home() / ".research_assistant" / "zotero_config.json"
    if config_path.exists():
        return json.loads(config_path.read_text()).get("api_key", "")
    return ""
```

---

### 43. 错误处理与日志

#### 错误处理原则

1. **不要暴露内部细节**：对外返回通用错误信息
2. **记录详细日志**：方便排查问题
3. **优雅降级**：部分功能坏了不影响其他功能
4. **区分可恢复/不可恢复错误**：决定是否重试

#### 异常分类

```python
# 用户输入错误（4xx）- 需要用户修改输入
raise HTTPException(status_code=400, detail="文件类型不支持")

# 资源不存在（404）
raise HTTPException(status_code=404, detail="Task not found")

# 服务器内部错误（500）- 需要修复代码
raise HTTPException(status_code=500, detail="内部错误，请联系管理员")
```

#### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("开始执行...")
    try:
        result = risky_operation()
        logger.info(f"执行成功: {result}")
        return result
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        raise
```

#### 在本项目中的应用

```python
# backend/api/routes.py

@router.post("/tasks/{task_id}/continue", response_model=TaskResponse)
def continue_task(task_id: str, request: ContinueTaskRequest) -> TaskResponse:
    try:
        task = store.continue_task(task_id, request)
    except KeyError as exc:
        # 资源不存在
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        # 业务逻辑错误
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskResponse.model_validate(task)
```

---

### 44. 测试驱动开发

#### 测试类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 单元测试 | 测试单个函数 | 测试 add(1, 2) = 3 |
| 集成测试 | 测试组件交互 | 测试 API 端点 |
| E2E 测试 | 测试完整流程 | 测试创建任务到完成的整个流程 |

#### pytest 基本用法

```python
# tests/test_example.py
import pytest

def add(a, b):
    return a + b

def test_add_integers():
    assert add(1, 2) == 3

def test_add_strings():
    assert add("a", "b") == "ab"

# 运行
pytest tests/test_example.py -v
```

#### Fixture（测试固件）

```python
import pytest

@pytest.fixture
def sample_task():
    return {
        "task_id": "task_123",
        "status": "pending",
        "user_query": "测试查询"
    }

def test_task_creation(sample_task):
    assert sample_task["task_id"] == "task_123"
    assert sample_task["status"] == "pending"
```

#### 在本项目中的应用

```python
# tests/test_e2e_interrupt_flow.py

def test_full_flow():
    # 1. 创建任务
    response = client.post("/tasks", json={
        "task_type": "analysis",
        "user_query": "碳排放 农业"
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 2. 验证中断状态
    response = client.get(f"/tasks/{task_id}")
    assert response.json()["status"] == "interrupted"

    # 3. 确认继续
    response = client.post(f"/tasks/{task_id}/continue", json={
        "decision": "approved"
    })
    assert response.status_code == 200
```

---

### 45. API 版本管理与文档

#### 为什么要版本管理？

API 是服务器和客户端之间的"契约"，修改 API 时需要考虑向后兼容。

#### 版本策略

**URL 路径版本**（本项目采用）
```
/api/v1/tasks
/api/v2/tasks
```

**Header 版本**
```
Accept: application/vnd.api.v2+json
```

#### OpenAPI 文档

```python
from fastapi import FastAPI

app = FastAPI(
    title="智能科研助手 API",
    version="1.0.0",
    description="""
    智能科研助手后端 API。

    ## 功能
    - 任务管理
    - 文件上传
    - 实时状态推送

    ## 认证
    当前版本无需认证。
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)
```

#### 响应文档字符串

```python
@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="获取任务详情",
    description="根据 task_id 获取任务的完整信息，包括当前状态和中断数据。"
)
def get_task(task_id: str) -> TaskResponse:
    """
    获取指定任务的详细信息。

    - **task_id**: 任务的唯一标识符
    - **returns**: 任务对象，包含所有状态和结果数据

    > 注意：已终止的任务仍可查询其历史记录
    """
    ...
```

---

## 附录

### A. 术语表

| 术语 | 英文 | 解释 |
|------|------|------|
| API | Application Programming Interface | 应用程序编程接口 |
| HTTP | HyperText Transfer Protocol | 超文本传输协议 |
| REST | Representational State Transfer | 表现层状态转换 |
| JSON | JavaScript Object Notation | JavaScript 对象表示法 |
| LLM | Large Language Model | 大语言模型 |
| Agent | Intelligent Agent | 智能体 |
| State | State | 状态 |
| Node | Node | 节点 |
| Edge | Edge | 边 |
| Checkpoint | Checkpoint | 检查点 |
| Interrupt | Interrupt | 中断 |
| Sandbox | Sandbox | 沙箱 |
| Repository | Repository | 仓库/存储库 |
| Middleware | Middleware | 中间件 |
| FastAPI | FastAPI | Python Web 框架 |
| Redis | Redis | 内存数据库 |
| Pydantic | Pydantic | Python 数据验证库 |
| TypedDict | Typed Dictionary | 类型字典 |
| Protocol | Protocol | 协议/接口定义 |
| Pub/Sub | Publish/Subscribe | 发布-订阅模式 |
| HITL | Human-in-the-Loop | 人在环中 |
| AST | Abstract Syntax Tree | 抽象语法树 |

### B. 推荐学习资源

#### Python
- 官方文档：https://docs.python.org/
- 《Fluent Python》- 进阶必读

#### FastAPI
- 官方文档：https://fastapi.tiangolo.com/
- FastAPI 教程：https://fastapi.tiangolo.com/tutorial/

#### LangGraph
- 官方文档：https://langchain-ai.github.io/langgraph/
- LangChain Academy

#### 系统设计
- 《Designing Data-Intensive Applications》- 数据系统设计
- 《System Design Interview》- 系统设计面试

#### AI Agent
- LangChain Agent 文档
- OpenAI Agent 文档
- Anthropic Claude Agent 最佳实践

### C. 下一步学习路径

```
阶段1：打牢基础
├── Python 进阶（类型注解、异步编程）
├── FastAPI 完整学习
├── 数据库基础（SQL + Redis）
└── API 设计与文档

阶段2：AI Agent 入门
├── LLM API 使用
├── Prompt 工程
├── LangChain 基础
└── 简单的 RAG 应用

阶段3：复杂 Agent 系统
├── LangGraph 深度学习
├── 状态管理与中断机制
├── 多 Agent 编排
└── 安全与沙箱

阶段4：工程化
├── 测试驱动开发
├── Docker 容器化
├── CI/CD 流程
└── 监控与日志
```

---

*本文档由 AI 生成，如有错误欢迎指正。*
