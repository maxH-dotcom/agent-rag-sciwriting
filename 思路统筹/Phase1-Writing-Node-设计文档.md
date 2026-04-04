# Phase 1：Writing Node 技术设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `Phase0-最小可运行骨架-实施计划.md`
> - `Phase1-Research-Brief-Schema-设计文档.md`
> - `Phase1-Analysis-Node-设计文档.md`

---

## 一、定位与职责

### 1.1 Writing Node 定位

Writing Node 是系统的**论文写作中心**，负责：
- 基于 Research_Brief 生成论文提纲
- 生成方法部分草稿
- 生成结果部分草稿
- 生成摘要草稿

**核心原则**：`No raw logs into writer`
- Writing Node 只接收 Research_Brief
- 不接收原始检索日志、代码错误等

### 1.2 与其他节点的关系

```
                    ┌──────────────────┐
                    │    Brief Builder │
                    │                  │
                    └────────┬─────────┘
                             │
                             │ Research_Brief
                             ▼
                    ┌──────────────────┐
                    │    Writing       │
                    │     Node         │
                    └────────┬─────────┘
                             │
                      ┌──────┴──────┐
                      │ 中断确认    │  ← Writing Interrupt
                      └──────┬──────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   最终论文草稿    │
                    └──────────────────┘
```

---

## 二、关键设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 输入来源 | 只从 Brief Builder 接收 Research_Brief | 保证数据一致性 |
| 写作范围 | 提纲 + 摘要 + 方法 + 结果 | MVP 不做完整论文 |
| 生成方式 | LLM 分段生成 | 控制长度，保证质量 |
| 中断点 | 草稿确认 | 用户可修改后继续 |
| 引用格式 | 从 evidence_map 提取 | 保证可追溯性 |

### 2.1 MVP 约束说明

1. Writing Node 只生成**提纲、方法草稿、结果草稿、摘要**，不做完整论文。
2. 引用的论断必须有 evidence_map 支持，否则不能生成正式引用稿。
3. 参考文献列表从 Literature Node 的 `references` 字段获取。

---

## 三、数据结构

### 3.1 WritingState（子图状态）

```python
# backend/agents/orchestrator/subgraphs/writing_state.py

from typing import TypedDict, Optional, List

class WritingState(TypedDict):
    task_id: str
    brief_id: str

    # Research_Brief 输入
    research_brief: dict | None

    # 生成内容
    outline: str | None
    abstract: str | None
    introduction: str | None
    methods: str | None
    results: str | None
    references: List[dict] | None

    # 当前生成阶段
    current_section: str | None  # "outline" | "abstract" | "methods" | "results"
    generated_sections: List[str]

    # 质量控制
    quality_warnings: List[str]
    missing_evidence_sections: List[str]

    # 状态
    status: str  # "reading_brief" | "generating" | "interrupted" | "done" | "error"
    interrupt_reason: str | None
    interrupt_data: dict | None
    human_decision: dict | None
    error_message: str | None
```

### 3.2 WritingResult（输出结构）

```python
# backend/agents/models/writing.py

from pydantic import BaseModel, Field
from typing import List, Optional

class WritingResult(BaseModel):
    """Writing Node 输出"""
    task_id: str
    brief_id: str

    # 生成内容
    outline: str = Field(default="", description="论文提纲")
    abstract: str = Field(default="", description="摘要草稿")
    introduction: str = Field(default="", description="引言草稿")
    methods: str = Field(default="", description="方法部分草稿")
    results: str = Field(default="", description="结果部分草稿")
    discussion: str = Field(default="", description="讨论部分草稿")
    references: str = Field(default="", description="参考文献列表")

    # 引用追踪
    evidence_bindings: dict = Field(
        default_factory=dict,
        description="各段落引用的 evidence chunk"
    )

    # 质量信息
    quality_warnings: List[str] = Field(default_factory=list)
    completeness_score: float = Field(
        ge=0.0, le=1.0,
        description="草稿完整度评分"
    )

    # 元数据
    created_at: str
    human_approved: bool = Field(default=False)
    human_feedback: dict | None = Field(default=None)
```

---

## 四、Writing Node 子图设计

### 4.1 子图流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Writing Node 子图                              │
│                                                                  │
│  ┌──────────────┐                                                │
│  │    start    │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────┐                                            │
│  │ read_brief       │  ← 读取 Research_Brief                      │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ check_evidence   │  ← 检查 evidence_map 完整性                  │
│  │ (质量门禁)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ generate_outline  │  ← 生成论文提纲                             │
│  │ (LLM 生成)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ generate_methods   │  ← 生成方法部分草稿                         │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ generate_results  │  ← 生成结果部分草稿                         │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ generate_abstract │  ← 生成摘要草稿                             │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ interrupt        │────▶│ human_feedback  │  ← 草稿确认中断  │
│  │ (Writing 中断)   │     └─────────────────┘                   │
│  └──────────────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │      end        │                                            │
│  └──────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 节点详细设计

#### 4.2.1 read_brief 节点

```python
async def read_brief_node(state: WritingState) -> WritingState:
    """
    读取 Research_Brief
    """
    from backend.core.brief_version import BriefVersionManager
    from backend.core.redis import get_redis

    brief_id = state.get("brief_id")
    if not brief_id:
        state["error_message"] = "未提供 brief_id"
        state["status"] = "error"
        return state

    # 从 Redis 读取当前版本的 Brief
    version_manager = BriefVersionManager(get_redis())
    brief = version_manager.get_current(brief_id)

    if not brief:
        state["error_message"] = f"Brief {brief_id} 不存在"
        state["status"] = "error"
        return state

    state["research_brief"] = brief.model_dump()
    state["status"] = "generating"

    return state
```

#### 4.2.2 check_evidence 节点

```python
async def check_evidence_node(state: WritingState) -> WritingState:
    """
    检查 evidence_map 完整性
    质量门禁：缺少关键证据的论断不能生成正式引用稿
    """
    from langchain_openai import ChatOpenAI

    brief = state.get("research_brief", {})
    evidence_map = brief.get("evidence_map", {})
    claims = evidence_map.get("claims", [])

    if not claims:
        state["quality_warnings"] = ["evidence_map 为空，生成内容将不包含引用"]
        state["missing_evidence_sections"] = ["methods", "results"]
    else:
        # 检查每条论断是否有 evidence 支持
        missing = []
        for claim in claims:
            if not claim.get("source_chunk_ids"):
                missing.append(claim.get("claim_id", "unknown"))

        state["missing_evidence_sections"] = missing
        if missing:
            state["quality_warnings"] = [
                f"以下论断缺少证据支持: {', '.join(missing)}"
            ]

    # 设置 evidence_bindings 映射
    state["evidence_bindings"] = {
        claim.get("claim_id"): claim.get("source_chunk_ids", [])
        for claim in claims
    }

    state["status"] = "generating"

    return state
```

#### 4.2.3 generate_outline 节点

```python
async def generate_outline_node(state: WritingState) -> WritingState:
    """
    生成论文提纲
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    brief = state.get("research_brief", {})
    research_goal = brief.get("research_goal", "")
    novelty = brief.get("novelty_position", {})
    method = brief.get("method_decision", {})

    outline_prompt = f"""
    基于以下信息，生成论文提纲。

    研究目标：{research_goal}

    创新性定位：
    - 重复点：{novelty.get('overlap_with_existing', [])}
    - 区分点：{novelty.get('differentiation_points', [])}
    - 推荐方向：{novelty.get('suggested_topic_directions', [])}

    方法决策：
    - 推荐模型：{method.get('recommended_models', [])}
    - 推荐理由：{method.get('reasoning', '')}

    任务：生成学术论文提纲。

    要求：
    1. 提纲应包含：引言、数据与方法、结果、讨论、结论
    2. 各部分用简短描述，说明要写什么
    3. 使用学术论文标准结构

    返回JSON格式：
    {{
        "outline": "完整的论文提纲（Markdown格式）",
        "section_summary": {{
            "引言": "引言要点",
            "数据与方法": "方法要点",
            "结果": "结果要点",
            "讨论": "讨论要点",
            "结论": "结论要点"
        }}
    }}
    """

    response = await llm.ainvoke(outline_prompt)
    result = json.loads(response.content)

    state["outline"] = result.get("outline", "")
    state["section_summary"] = result.get("section_summary", {})
    state["current_section"] = "outline"
    state["generated_sections"] = ["outline"]

    return state
```

#### 4.2.4 generate_methods 节点

```python
async def generate_methods_node(state: WritingState) -> WritingState:
    """
    生成方法部分草稿
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    brief = state.get("research_brief", {})
    evidence_map = brief.get("evidence_map", {})
    claims = evidence_map.get("claims", [])
    method = brief.get("method_decision", {})
    analysis = brief.get("analysis_outputs", {})

    # 格式化证据供写作参考
    evidence_context = format_evidence_for_writing(claims)

    methods_prompt = f"""
    基于以下信息，生成论文方法部分草稿。

    研究目标：{brief.get('research_goal', '')}

    数据摘要：{brief.get('data_summary', {})}

    方法决策：
    - 推荐模型：{method.get('recommended_models', [])}
    - 推荐理由：{method.get('reasoning', '')}
    - 模型参数：{method.get('model_parameters', {})}

    分析输出：
    - 代码：{analysis.get('code_script', 'N/A')[:500]}...
    - 数值结果：{analysis.get('numerical_results', {})}

    证据引用：
    {evidence_context}

    任务：生成方法部分草稿。

    要求：
    1. 使用学术写作风格
    2. 包含：数据来源、变量定义、模型选择、稳健性检验
    3. 每项陈述需附带引用，使用 [chunk_id] 格式
    4. 不要包含原始代码

    返回JSON格式：
    {{
        "methods": "方法部分完整草稿（Markdown格式）",
        "evidence_usage": ["使用的 evidence chunk_id 列表"]
    }}
    """

    response = await llm.ainvoke(methods_prompt)
    result = json.loads(response.content)

    state["methods"] = result.get("methods", "")
    state["current_section"] = "methods"
    state["generated_sections"].append("methods")

    # 更新 evidence_bindings
    state["evidence_bindings"]["methods"] = result.get("evidence_usage", [])

    return state
```

#### 4.2.5 generate_results 节点

```python
async def generate_results_node(state: WritingState) -> WritingState:
    """
    生成结果部分草稿
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    brief = state.get("research_brief", {})
    analysis = brief.get("analysis_outputs", {})
    evidence_map = brief.get("evidence_map", {})
    claims = evidence_map.get("claims", [])

    # 格式化数值结果
    numerical_results = analysis.get("numerical_results", {})
    charts = analysis.get("charts", [])

    results_context = format_results_for_writing(numerical_results, charts)
    evidence_context = format_evidence_for_writing(claims)

    results_prompt = f"""
    基于以下分析结果，生成论文结果部分草稿。

    研究目标：{brief.get('research_goal', '')}

    分析结果：
    {results_context}

    证据引用：
    {evidence_context}

    任务：生成结果部分草稿。

    要求：
    1. 使用学术写作风格
    2. 以文字描述为主，避免堆砌数字
    3. 描述趋势、关系、显著性
    4. 每项陈述需附带引用，使用 [chunk_id] 格式
    5. 提及关键图表

    返回JSON格式：
    {{
        "results": "结果部分完整草稿（Markdown格式）",
        "key_findings": ["关键发现列表"],
        "evidence_usage": ["使用的 evidence chunk_id 列表"]
    }}
    """

    response = await llm.ainvoke(results_prompt)
    result = json.loads(response.content)

    state["results"] = result.get("results", "")
    state["key_findings"] = result.get("key_findings", [])
    state["current_section"] = "results"
    state["generated_sections"].append("results")

    # 更新 evidence_bindings
    state["evidence_bindings"]["results"] = result.get("evidence_usage", [])

    return state
```

#### 4.2.6 generate_abstract 节点

```python
async def generate_abstract_node(state: WritingState) -> WritingState:
    """
    生成摘要草稿
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    brief = state.get("research_brief", {})

    abstract_prompt = f"""
    基于以下信息，生成论文摘要草稿。

    研究目标：{brief.get('research_goal', '')}

    提纲：{state.get('outline', '')}

    方法：{state.get('methods', '')[:500]}...

    结果：{state.get('results', '')[:500]}...

    关键发现：{state.get('key_findings', [])}

    任务：生成 200-300 字的标准学术论文摘要。

    要求：
    1. 包含：研究背景、目的、方法、结果、结论
    2. 使用学术写作风格
    3. 不使用缩写，第一次使用时需写出全称

    返回JSON格式：
    {{
        "abstract": "摘要草稿（200-300字）"
    }}
    """

    response = await llm.ainvoke(abstract_prompt)
    result = json.loads(response.content)

    state["abstract"] = result.get("abstract", "")
    state["current_section"] = "abstract"
    state["generated_sections"].append("abstract")

    return state
```

#### 4.2.7 handle_human_feedback 节点

```python
async def handle_human_feedback_node(state: WritingState) -> WritingState:
    """
    处理用户对草稿的反馈
    """
    human_feedback = state.get("human_feedback", {})
    feedback_type = human_feedback.get("type", "approved")

    if feedback_type == "approved":
        # 用户确认草稿
        state["status"] = "done"
        state["human_approved"] = True

    elif feedback_type == "modified":
        # 用户修改了某些部分
        modified_sections = human_feedback.get("modified_sections", {})

        if "outline" in modified_sections:
            state["outline"] = modified_sections["outline"]
        if "methods" in modified_sections:
            state["methods"] = modified_sections["methods"]
        if "results" in modified_sections:
            state["results"] = modified_sections["results"]
        if "abstract" in modified_sections:
            state["abstract"] = modified_sections["abstract"]

        state["status"] = "done"
        state["human_approved"] = True
        state["human_feedback"] = human_feedback

    elif feedback_type == "regenerate":
        # 用户要求重新生成
        sections_to_regenerate = human_feedback.get("sections", ["methods", "results"])

        if "methods" in sections_to_regenerate:
            # 重新生成方法部分（使用用户提供的额外指导）
            extra_guidance = human_feedback.get("guidance", "")
            state = await regenerate_section(state, "methods", extra_guidance)

        if "results" in sections_to_regenerate:
            state = await regenerate_section(state, "results", "")

        state["status"] = "done"

    return state
```

### 4.3 子图编译

```python
def build_writing_graph():
    """编译 Writing Node 子图"""

    workflow = StateGraph(WritingState)

    workflow.add_node("read_brief", read_brief_node)
    workflow.add_node("check_evidence", check_evidence_node)
    workflow.add_node("generate_outline", generate_outline_node)
    workflow.add_node("generate_methods", generate_methods_node)
    workflow.add_node("generate_results", generate_results_node)
    workflow.add_node("generate_abstract", generate_abstract_node)
    workflow.add_node("handle_feedback", handle_human_feedback_node)

    workflow.set_entry_point("read_brief")
    workflow.add_edge("read_brief", "check_evidence")
    workflow.add_edge("check_evidence", "generate_outline")
    workflow.add_edge("generate_outline", "generate_methods")
    workflow.add_edge("generate_methods", "generate_results")
    workflow.add_edge("generate_results", "generate_abstract")

    # 中断条件边
    workflow.add_conditional_edges(
        "generate_abstract",
        lambda s: "interrupt",
        {"interrupt": "__interrupt__"}
    )

    workflow.add_edge("handle_feedback", END)

    return workflow.compile()
```

---

## 五、中断处理

### 5.1 Writing 中断数据结构

```json
{
  "status": "interrupted",
  "interrupt_reason": "draft_ready",
  "interrupt_data": {
    "outline": "# 论文提纲\n\n## 1. 引言\n...",
    "abstract": "本研究旨在分析...",
    "methods": "## 数据来源\n\n本研究使用...",
    "results": "## 主要结果\n\n如图1所示...",
    "evidence_bindings": {
      "methods": ["chunk_101", "chunk_145"],
      "results": ["chunk_201"]
    },
    "quality_warnings": [],
    "completeness_score": 0.85
  }
}
```

### 5.2 前端 Writing 中断 UI

```tsx
<div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
  <h3 className="font-bold text-purple-800 mb-2">论文草稿已生成</h3>

  <div className="mb-4">
    <p className="text-sm text-gray-600">
      完整度评分：{completenessScore}/1.0
    </p>
    <div className="w-full bg-purple-200 rounded-full h-3 mt-1">
      <div
        className="bg-purple-600 h-3 rounded-full"
        style={{ width: `${completenessScore * 100}%` }}
      />
    </div>
  </div>

  <Tabs>
    <Tab label="提纲">{outline}</Tab>
    <Tab label="摘要">{abstract}</Tab>
    <Tab label="方法">{methods}</Tab>
    <Tab label="结果">{results}</Tab>
  </Tabs>

  <div className="flex gap-3 mt-4">
    <button
      onClick={() => handleContinue("approved")}
      className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
    >
      确认草稿
    </button>
    <button
      onClick={() => handleModify()}
      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
    >
      修改草稿
    </button>
    <button
      onClick={() => handleRegenerate()}
      className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
    >
      重新生成
    </button>
  </div>
</div>
```

---

## 六、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/models/writing.py` | WritingResult 数据模型 |
| `backend/agents/orchestrator/subgraphs/writing_state.py` | 子图状态定义 |
| `backend/agents/orchestrator/subgraphs/writing_node.py` | Writing Node 主逻辑 |
| `frontend/components/writing-interrupt.tsx` | Writing 中断 UI 组件 |

---

## 七、依赖与输出

### 7.1 依赖

```
Writing Node 依赖：
├── backend/core/brief_version.py              # BriefVersionManager
├── backend/agents/models/research_brief.py     # ResearchBrief Schema
└── Research_Brief from Brief Builder
```

### 7.2 输出

```
Writing Node 输出 → 最终结果：
├── outline                    # 论文提纲
├── abstract                   # 摘要草稿
├── methods                    # 方法草稿
├── results                    # 结果草稿
├── evidence_bindings          # 引用追踪
└── human_approved             # 用户确认状态
```

---

## 八、实施检查清单

- [ ] WritingResult 数据模型
- [ ] WritingState 状态定义
- [ ] read_brief 节点
- [ ] check_evidence 节点（质量门禁）
- [ ] generate_outline 节点
- [ ] generate_methods 节点
- [ ] generate_results 节点
- [ ] generate_abstract 节点
- [ ] 中断处理逻辑
- [ ] 前端 WritingInterrupt UI 组件
- [ ] 端到端集成测试

---

## 九、下一步

Phase 1 剩余内容：
1. **Brief Builder** - 完善汇总逻辑
2. **4 个中断点的完整实现** - 前后端联调
3. **SSE 状态推送** - 实时状态更新
