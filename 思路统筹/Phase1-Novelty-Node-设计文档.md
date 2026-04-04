# Phase 1：Novelty Node 技术设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `Phase0-最小可运行骨架-实施计划.md`
> - `科研多Agent系统MVP实施计划.md`

---

## 一、定位与职责

### 1.1 Novelty Node 定位

**调整说明（2026-04-04）**：Novelty Node 是系统的**决策节点**，负责**迁移/组合/调整可行性评估**。

在 Literature Node 提供方法元信息的基础上，Novelty Node 的核心职责是：
- **跨领域/跨地理迁移评估**：判断 A 领域/A 地区的方法能否迁移到用户的研究场景
- **组合可行性分析**：多个方法能否组合，以及组合后的优势
- **适应性调整评估**：方法需要做什么调整才能适应用户的数据和研究目标
- **方向建议**：综合以上分析，推荐可行的研究方向（含迁移逻辑）

### 1.2 职责

1. **文献检索**：检索本地 + 外部相关文献（复用 Literature Node 的 method_metadata）
2. **迁移/组合/调整评估**：LLM 综合分析，输出创新性评估（扩展）
3. **方向建议**：推荐可行的研究方向（含 transfer_context）
4. **中断确认**：向用户展示迁移评估结果，等待确认

### 1.3 与 Literature Node 的关系（调整后）

```
Literature Node ──▶ method_metadata ──▶ Novelty Node
                                             │
                                    ┌────────┴────────┐
                                    │ 迁移/组合/调整评估 │
                                    └────────┬────────┘
                                             │ 中断确认
                                             ▼
                                       Literature
```

---

## 二、关键设计决策（已调整，2026-04-04）

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 与 Literature 关系 | 串行：Literature → Novelty | Literature 先提取元信息，Novelty 做迁移评估 |
| 迁移评估逻辑 | LLM 综合判断 | 端到端理解上下文，而非简单规则匹配 |
| 迁移评估维度 | 跨领域迁移 + 跨地理迁移 + 组合 + 适应性调整 | 覆盖研究者的核心场景 |
| 创新性判断逻辑 | 基于迁移可行性的综合判断 | 不是"有没有人做过"，而是"这个方法能不能迁移/调整到我的场景" |
| 本地检索工具 | paper-qa | 已有封装，复用 |
| 外部检索工具 | pyopenalex | 已有封装，复用 |

### 2.1 迁移评估场景说明

**场景1：跨地理迁移**
- 研究者A在长江流域用过 STIRPAT 模型研究碳排放
- 研究者B在阿拉伯地区研究类似问题
- 核心问题：这个方法能否迁移？需要做什么调整？

**场景2：跨领域迁移**
- 研究者想用环境科学领域的分解分析方法研究经济问题
- 核心问题：这个方法在经济学场景下是否适用？变量如何映射？

**场景3：组合创新**
- 文献A用 DID 方法，文献B用 STIRPAT 模型
- 核心问题：两者能否组合？组合后的研究价值？

**场景4：适应性调整**
- 文献中使用的数据结构与用户数据不同（面板 vs 截面）
- 核心问题：需要做什么调整？风险点在哪里？

### 2.1 MVP 约束说明

Novelty Node 在 MVP 阶段存在以下显式约束：

1. 已有论文比对依赖 LLM 的理解能力，不做严格的引用网络分析。
2. 创新性评分是 LLM 的主观判断，不承诺与学术界的客观评价一致。
3. 推荐的题目方向仅供参考，用户有最终决定权。

---

## 三、数据结构

### 3.1 NoveltyState（子图状态）

```python
# backend/agents/orchestrator/subgraphs/novelty_state.py

from typing import TypedDict, Optional, List

class NoveltyState(TypedDict):
    task_id: str

    # 输入
    user_query: str                    # 用户的新选题描述
    user_data_context: dict | None     # 用户的数据上下文（新增）
    existing_papers: List[dict]         # 用户上传的已有论文
    uploaded_paper_ids: List[str]       # 用户上传论文的 ID 列表

    # 文献检索结果（从 Literature Node 获得）
    literature_chunks: List[dict]       # 合并后的文献片段
    method_metadata: List[dict]          # 方法元信息（新增，来自 Literature）
    literature_result: dict | None       # Literature Node 完整结果

    # 迁移/组合/调整评估（新增）
    transfer_assessments: List[dict]    # 每个方法的迁移评估结果
    combination_options: List[dict]     # 可组合的方法对
    recommended_direction: dict | None   # 最终推荐的迁移方向

    # 已有论文分析
    existing_paper_analysis: List[dict]  # 分析每篇已有论文与新选题的关系
    overlap_with_existing: List[str]     # 与已有工作的整体重复点

    # 创新性判断
    novelty_result: dict | None         # 最终创新性判断结果
    novelty_score: float                # 创新性评分 0-1
    differentiation_points: List[str]    # 区分点/创新点
    suggested_topic_directions: List[str]  # 推荐研究方向
    quality_warning: str | None         # 质量问题警告

    # 状态
    status: str  # "receiving_literature" | "assessing_transfer" | "judging" | "interrupted" | "done" | "error"
    interrupt_reason: str | None
    interrupt_data: dict | None
    human_decision: dict | None
    error_message: str | None
```

### 3.2 NoveltyResult（输出结构）

```python
# backend/agents/models/novelty.py

from pydantic import BaseModel, Field
from typing import List, Optional

class ExistingPaperMatch(BaseModel):
    """已有论文与新选题的比对结果"""
    paper_id: str
    paper_title: str
    overlap_aspects: List[str] = Field(
        default_factory=list,
        description="重叠的方面：方法/区域/数据/变量等"
    )
    differentiation_aspects: List[str] = Field(
        default_factory=list,
        description="区分的方面"
    )
    similarity_score: float = Field(
        ge=0.0, le=1.0,
        description="整体相似度"
    )


class TransferAssessment(BaseModel):
    """
    迁移评估结果（新增，2026-04-04）

    对每个候选方法的迁移/组合/调整可行性评估。
    """
    method_name: str = Field(description="方法名称")
    source_chunk_id: str = Field(description="来源文献 chunk_id")
    source: str = Field(description="来源描述，如 '长江流域碳排放研究（文献A）'")

    # 迁移可行性
    transfer_feasibility: str = Field(
        description="迁移可行性：'高' / '中' / '低' / '不可迁移'"
    )
    transfer_feasibility_reason: str = Field(
        description="可行性判断理由"
    )

    # 需要的调整
    required_adaptations: List[str] = Field(
        default_factory=list,
        description="需要做的适应性调整列表"
    )
    adaptation_risk: str | None = Field(
        default=None,
        description="调整风险点（如有）"
    )

    # 组合信息（如果适用）
    combinable_with: List[str] = Field(
        default_factory=list,
        description="可与哪些方法组合"
    )
    combination_benefit: str | None = Field(
        default=None,
        description="组合带来的研究价值"
    )

    # 变量映射（如果适用）
    variable_mapping: dict | None = Field(
        default=None,
        description="从原方法变量到用户变量的映射关系"
    )


class NoveltyResult(BaseModel):
    """Novelty Node 输出"""
    task_id: str

    # 迁移/组合/调整评估（新增核心字段）
    transfer_assessments: List[TransferAssessment] = Field(
        default_factory=list,
        description="各方法的迁移评估结果"
    )
    recommended_direction: dict = Field(
        default_factory=dict,
        description="最终推荐的迁移方向，包含 transfer_context"
    )

    # 已有论文比对
    existing_paper_matches: List[ExistingPaperMatch] = Field(
        default_factory=list,
        description="与每篇已有论文的比对结果"
    )
    overlap_with_existing: List[str] = Field(
        default_factory=list,
        description="与已有工作的整体重复点"
    )

    # 文献检索结果摘要
    total_local_hits: int = 0
    total_openalex_hits: int = 0

    # 创新性评估
    novelty_score: float = Field(
        ge=0.0, le=1.0,
        description="创新性评分"
    )
    differentiation_points: List[str] = Field(
        default_factory=list,
        description="可区分点/创新点"
    )
    suggested_topic_directions: List[str] = Field(
        default_factory=list,
        description="推荐的题目方向（含迁移逻辑说明）"
    )

    # 质量评估
    quality_warning: str | None = Field(
        default=None,
        description="质量问题警告"
    )

    # 元数据
    created_at: str
    human_approved: bool = Field(
        default=False,
        description="是否经过人工确认"
    )
    human_decision: dict | None = Field(
        default=None,
        description="人工决策详情"
    )
```

---

## 四、Novelty Node 子图设计

### 4.1 子图流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Novelty Node 子图                              │
│  （调整后：2026-04-04）                                            │
│                                                                  │
│  ┌──────────────┐                                                │
│  │    start    │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────┐                                            │
│  │ receive_literature│  ← 接收 Literature Node 的 method_metadata │
│  │                  │     + literature_chunks                       │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ analyze_existing  │  ← 分析用户已有论文与新选题的关系          │
│  │ (LLM 比对)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ assess_transfer   │  ← 迁移/组合/调整可行性评估（核心新增）     │
│  │ (LLM 分析)       │     基于 method_metadata + user_data_context │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ judge_novelty     │  ← 综合判断创新性 + 生成推荐方向           │
│  │ (LLM 分析)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ interrupt        │────▶│ human_decision  │  ← 中断等待确认  │
│  │ (Novelty 中断)   │     └─────────────────┘                   │
│  └──────────────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │      end        │                                            │
│  └──────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**调整说明（2026-04-04）**：
- 新增 `receive_literature` 节点：接收 Literature Node 的输出
- 新增 `assess_transfer` 节点：基于 method_metadata 做迁移/组合/调整评估（这是核心新增逻辑）
- 调整 `judge_novelty`：现在输出包含 transfer_context 的推荐方向
- 数据流：`Literature → Novelty（迁移评估）→ 中断确认 → 后续节点`

### 4.2 节点详细设计

#### 4.2.1 analyze_existing 节点

```python
async def analyze_existing_papers_node(state: NoveltyState) -> NoveltyState:
    """
    分析用户已有论文与新选题的关系
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    existing_papers = state.get("existing_papers", [])
    user_query = state["user_query"]

    if not existing_papers:
        state["existing_paper_analysis"] = []
        state["overlap_with_existing"] = []
        state["similar_papers"] = []
        return state

    # 对每篇已有论文进行比对分析
    paper_matches = []
    all_overlaps = []
    similar_papers = []

    for paper in existing_papers:
        paper_content = extract_paper_summary(paper)

        comparison_prompt = f"""
        用户新选题：{user_query}

        已有论文信息：
        标题：{paper.get('title', '未知')}
        摘要：{paper.get('abstract', '')}

        任务：分析这篇已有论文与用户新选题的关系。

        分析维度：
        1. 重叠方面：方法、区域、数据类型、变量、研究问题等
        2. 区分方面：与新选题相比有什么不同
        3. 整体相似度 (0-1)

        返回JSON格式：
        {{
            "overlap_aspects": ["重叠点列表"],
            "differentiation_aspects": ["区分点列表"],
            "similarity_score": 0.0-1.0,
            "is_similar": true/false (如果 similarity > 0.5)
        }}
        """

        response = await llm.ainvoke(comparison_prompt)
        result = json.loads(response.content)

        paper_match = {
            "paper_id": paper.get("paper_id"),
            "paper_title": paper.get("title", "未知"),
            "overlap_aspects": result.get("overlap_aspects", []),
            "differentiation_aspects": result.get("differentiation_aspects", []),
            "similarity_score": result.get("similarity_score", 0.0)
        }
        paper_matches.append(paper_match)
        all_overlaps.extend(result.get("overlap_aspects", []))

        if result.get("is_similar"):
            similar_papers.append(paper)

    state["existing_paper_analysis"] = paper_matches
    state["overlap_with_existing"] = list(set(all_overlaps))
    state["similar_papers"] = similar_papers
    state["status"] = "searching"

    return state
```

#### 4.2.2 search_local 节点

```python
async def search_local_literature_node(state: NoveltyState) -> NoveltyState:
    """
    检索本地文献
    """
    from backend.agents.tools.paperqa_wrapper import PaperQATool

    paperqa = PaperQATool()

    query = build_novelty_search_query(
        user_query=state["user_query"],
        existing_papers=state.get("existing_papers", [])
    )

    try:
        local_chunks = await paperqa.search(
            query=query,
            top_k=10,
            filters={"file_types": [".pdf", ".docx"]}
        )
        state["local_chunks"] = local_chunks
    except Exception as e:
        state["local_chunks"] = []
        state["error_message"] = f"本地检索失败: {str(e)}"

    state["status"] = "searching"
    return state


def build_novelty_search_query(user_query: str, existing_papers: list) -> str:
    """构建检索查询"""
    existing_keywords = []
    for paper in existing_papers:
        existing_keywords.extend(extract_keywords(paper))

    query_parts = [user_query]
    if existing_keywords:
        unique_keywords = list(set(existing_keywords))[:5]
        query_parts.append(" ".join(unique_keywords))

    return " ".join(query_parts)
```

#### 4.2.3 search_external 节点

```python
async def search_external_literature_node(state: NoveltyState) -> NoveltyState:
    """
    检索外部文献（OpenAlex）
    """
    from backend.agents.tools.openalex_wrapper import OpenAlexTool

    openalex = OpenAlexTool()

    try:
        openalex_chunks = await openalex.search_works(
            query=state["user_query"],
            top_k=10
        )
        state["openalex_chunks"] = openalex_chunks
    except Exception as e:
        state["openalex_chunks"] = []
        state["error_message"] = f"外部检索失败: {str(e)}"

    state["status"] = "judging"
    return state
```

#### 4.2.4 assess_transfer 节点（新增，2026-04-04）

```python
async def assess_transfer_node(state: NoveltyState) -> NoveltyState:
    """
    迁移/组合/调整可行性评估

    基于 Literature Node 提供的 method_metadata，结合用户数据上下文，
    评估每个方法能否迁移/组合/调整到用户的研究场景。
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    method_metadata = state.get("method_metadata", [])
    user_query = state["user_query"]
    user_data_context = state.get("user_data_context", {})

    if not method_metadata:
        state["transfer_assessments"] = []
        state["status"] = "judging"
        return state

    transfer_prompt = f"""
    用户研究目标：{user_query}

    用户数据上下文：
    - 研究区域/领域：{user_data_context.get('region', '未指定')}
    - 数据类型：{user_data_context.get('data_structure', '未指定')}
    - 变量：{user_data_context.get('variables', {})}

    文献中提取的方法元信息：
    {format_method_metadata_for_assessment(method_metadata)}

    任务：对每个方法，评估其迁移/组合/调整到用户研究场景的可行性。

    评估维度：
    1. 迁移可行性（高/中/低/不可迁移）及理由
    2. 需要的适应性调整（变量映射、控制变量修改、时间范围调整等）
    3. 调整的风险点
    4. 可组合性（能与哪些方法组合，组合价值）
    5. 变量映射关系（如适用）

    返回JSON格式：
gee
    {{
        "transfer_assessments": [
            {{
                "method_name": "方法名",
                "source_chunk_id": "来源chunk_id",
                "source": "来源描述",
                "transfer_feasibility": "高/中/低/不可迁移",
                "transfer_feasibility_reason": "判断理由",
                "required_adaptations": ["调整1", "调整2"],
                "adaptation_risk": "风险描述或null",
                "combinable_with": ["可组合方法1"],
                "combination_benefit": "组合价值或null",
                "variable_mapping": {{"原变量": "用户变量"}}或null
            }}
        ]
    }}
    """

    response = await llm.ainvoke(transfer_prompt)
    result = json.loads(response.content)

    state["transfer_assessments"] = result.get("transfer_assessments", [])
    state["status"] = "judging"

    return state
```

#### 4.2.5 judge_novelty 节点（调整，2026-04-04）

```python
async def judge_novelty_node(state: NoveltyState) -> NoveltyState:
    """
    LLM 综合判断创新性 + 生成推荐方向（含迁移逻辑）
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    user_query = state["user_query"]
    literature_context = format_literature_for_judgment(state.get("literature_chunks", [])[:10])
    existing_analysis = format_existing_paper_analysis(
        state.get("existing_paper_analysis", [])
    )
    transfer_assessments = state.get("transfer_assessments", [])

    judgment_prompt = f"""
    用户新选题：{user_query}

    已有论文分析：
    {existing_analysis}

    相关文献：
    {literature_context}

    迁移/组合/调整评估结果：
    {format_transfer_assessments(transfer_assessments)}

    任务：综合评估用户新选题的创新性，并推荐研究方向。

    评估标准：
    - novelty_score: 0.0-1.0，1.0 表示完全创新
    - differentiation_points: 新选题与已有工作的区分点
    - suggested_topic_directions: 推荐的题目方向（每个方向需包含迁移逻辑说明）

    返回JSON格式：
    {{
        "novelty_score": 0.0-1.0,
        "overlap_with_existing": ["重复点列表"],
        "differentiation_points": ["区分点/创新点列表"],
        "suggested_topic_directions": [
            {{
                "direction": "推荐方向描述",
                "source_method": "来源方法",
                "transfer_logic": "迁移逻辑说明（为什么适合用户、如何调整）",
                "risk_notes": "风险提示（如有）"
            }}
        ],
        "recommended_direction": {{...}},  # 最推荐的单一方向
        "quality_warning": "警告信息或null"
    }}
    """

    response = await llm.ainvoke(judgment_prompt)
    result = json.loads(response.content)

    state["novelty_score"] = result.get("novelty_score", 0.0)
    state["overlap_with_existing"] = result.get("overlap_with_existing", [])
    state["differentiation_points"] = result.get("differentiation_points", [])
    state["suggested_topic_directions"] = result.get("suggested_topic_directions", [])
    state["recommended_direction"] = result.get("recommended_direction", {})
    state["quality_warning"] = result.get("quality_warning")

    # 中断等待用户确认
    state["status"] = "interrupted"
    state["interrupt_reason"] = "novelty_result_ready"
    state["interrupt_data"] = {
        "novelty_score": state["novelty_score"],
        "overlap_with_existing": state["overlap_with_existing"],
        "differentiation_points": state["differentiation_points"],
        "suggested_topic_directions": state["suggested_topic_directions"],
        "transfer_assessments": transfer_assessments,
        "recommended_direction": state["recommended_direction"],
        "existing_paper_matches": state.get("existing_paper_analysis", []),
        "quality_warning": state["quality_warning"]
    }

    return state
```

#### 4.2.5 handle_human_decision 节点

```python
async def handle_human_decision_node(state: NoveltyState) -> NoveltyState:
    """
    处理用户对创新性判断的确认/修改
    """
    human_decision = state.get("human_decision", {})
    decision = human_decision.get("decision", "approved")

    if decision == "approved":
        state["status"] = "done"
        state["novelty_result"] = {
            "task_id": state["task_id"],
            "existing_paper_matches": state.get("existing_paper_analysis", []),
            "overlap_with_existing": state["overlap_with_existing"],
            "total_local_hits": len(state.get("local_chunks", [])),
            "total_openalex_hits": len(state.get("openalex_chunks", [])),
            "novelty_score": state["novelty_score"],
            "differentiation_points": state["differentiation_points"],
            "suggested_topic_directions": state["suggested_topic_directions"],
            "quality_warning": state["quality_warning"],
            "created_at": datetime.utcnow().isoformat(),
            "human_approved": True,
            "human_decision": human_decision
        }

    elif decision == "modified":
        modified_data = human_decision.get("modified_data", {})
        state["overlap_with_existing"] = modified_data.get(
            "overlap_with_existing", state["overlap_with_existing"]
        )
        state["differentiation_points"] = modified_data.get(
            "differentiation_points", state["differentiation_points"]
        )
        state["suggested_topic_directions"] = modified_data.get(
            "suggested_topic_directions", state["suggested_topic_directions"]
        )
        state["status"] = "done"
        # ... 构建 novelty_result

    elif decision == "rejected":
        state["status"] = "done"
        state["novelty_result"] = {
            "task_id": state["task_id"],
            "human_approved": False,
            "human_decision": human_decision
        }

    return state
```

### 4.3 子图编译（调整后）

```python
def build_novelty_graph():
    """编译 Novelty Node 子图（调整后，2026-04-04）"""

    workflow = StateGraph(NoveltyState)

    workflow.add_node("receive_literature", receive_literature_node)  # 新增
    workflow.add_node("analyze_existing", analyze_existing_papers_node)
    workflow.add_node("assess_transfer", assess_transfer_node)  # 新增核心节点
    workflow.add_node("judge_novelty", judge_novelty_node)
    workflow.add_node("handle_decision", handle_human_decision_node)

    workflow.set_entry_point("receive_literature")
    workflow.add_edge("receive_literature", "analyze_existing")
    workflow.add_edge("analyze_existing", "assess_transfer")
    workflow.add_edge("assess_transfer", "judge_novelty")

    workflow.add_conditional_edges(
        "judge_novelty",
        lambda s: "interrupt",
        {"interrupt": "__interrupt__"}
    )

    workflow.add_edge("handle_decision", END)

    return workflow.compile()
```

**节点说明**：
- `receive_literature`：接收 Literature Node 的 method_metadata 和 literature_chunks
- `analyze_existing`：分析用户已有论文与新选题的关系
- `assess_transfer`：基于方法元信息做迁移/组合/调整可行性评估（核心新增）
- `judge_novelty`：综合判断 + 生成推荐方向

---

## 五、中断处理

### 5.1 Novelty 中断数据结构（调整后，2026-04-04）

```json
{
  "status": "interrupted",
  "interrupt_reason": "novelty_result_ready",
  "interrupt_data": {
    "novelty_score": 0.65,
    "overlap_with_existing": [
      "使用 STIRPAT 模型",
      "研究浙江省碳排放",
      "面板数据分析"
    ],
    "differentiation_points": [
      "加入农业碳排放细分",
      "预测时间范围扩展到2035"
    ],
    "suggested_topic_directions": [
      {
        "direction": "基于STIRPAT模型的中东地区农业碳排放预测",
        "source_method": "STIRPAT模型（长江流域碳排放研究）",
        "transfer_logic": "将长江流域的STIRPAT框架迁移到中东农业碳排放场景，需将FDI变量替换为能源消耗强度，加入地形和灌溉方式控制变量",
        "risk_notes": "时间序列长度可能不足，建议补充数据"
      }
    ],
    "transfer_assessments": [
      {
        "method_name": "STIRPAT模型",
        "source": "长江流域碳排放研究（文献A）",
        "transfer_feasibility": "高",
        "transfer_feasibility_reason": "数据结构相似（均为面板数据），研究问题类型相同",
        "required_adaptations": [
          "变量映射：FDI → 能源消耗强度",
          "控制变量调整：加入地形因素、灌溉方式"
        ],
        "adaptation_risk": "时间序列长度不足可能影响模型稳定性",
        "combinable_with": ["LMDI分解法"],
        "combination_benefit": "STIRPAT用于驱动因素分析，LMDI用于分解量化，两者结合增强研究深度",
        "variable_mapping": {"FDI": "能源消耗强度", "GDP": "农业产值"}
      }
    ],
    "recommended_direction": {
      "direction": "基于STIRPAT+LMDI组合的中东地区农业碳排放研究",
      "source_method": "STIRPAT + LMDI",
      "transfer_logic": "从长江流域迁移，需做变量映射和控制变量调整",
      "risk_notes": "数据长度风险，建议做稳健性检验"
    },
    "existing_paper_matches": [
      {
        "paper_id": "paper_001",
        "paper_title": "浙江省碳排放驱动机制研究",
        "overlap_aspects": ["区域:浙江", "对象:碳排放", "方法:STIRPAT"],
        "similarity_score": 0.72
      }
    ],
    "quality_warning": null
  }
}
```

### 5.2 前端 Novelty 中断 UI

```tsx
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <h3 className="font-bold text-blue-800 mb-2">选题创新性评估</h3>

  <div className="mb-4">
    <p className="text-sm text-gray-600">
      创新性评分：{noveltyScore}/1.0
    </p>
    <div className="w-full bg-blue-200 rounded-full h-3 mt-1">
      <div
        className="bg-blue-600 h-3 rounded-full"
        style={{ width: `${noveltyScore * 100}%` }}
      />
    </div>
  </div>

  {overlapWithExisting.length > 0 && (
    <div className="mb-3">
      <p className="font-semibold text-red-700 text-sm">⚠️ 与已有工作重复：</p>
      <ul className="list-disc pl-5 text-sm">
        {overlapWithExisting.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  )}

  {differentiationPoints.length > 0 && (
    <div className="mb-3">
      <p className="font-semibold text-green-700 text-sm">✓ 创新点：</p>
      <ul className="list-disc pl-5 text-sm">
        {differentiationPoints.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  )}

  {suggestedDirections.length > 0 && (
    <div className="mb-3">
      <p className="font-semibold text-blue-700 text-sm">推荐研究方向：</p>
      <ul className="list-disc pl-5 text-sm">
        {suggestedDirections.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  )}

  <div className="flex gap-3 mt-4">
    <button
      onClick={() => handleContinue("approved")}
      className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
    >
      确认选题方向
    </button>
    <button
      onClick={() => handleModify()}
      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
    >
      修改研究方向
    </button>
    <button
      onClick={() => handleContinue("rejected")}
      className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
    >
      终止任务
    </button>
  </div>
</div>
```

---

## 六、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/models/novelty.py` | NoveltyResult 数据模型 |
| `backend/agents/orchestrator/subgraphs/novelty_state.py` | 子图状态定义 |
| `backend/agents/orchestrator/subgraphs/novelty_node.py` | Novelty Node 主逻辑 |
| `frontend/components/novelty-interrupt.tsx` | Novelty 中断 UI 组件 |

---

## 七、依赖与输出

### 7.1 依赖

```
Novelty Node 依赖：
├── backend/agents/tools/paperqa_wrapper.py     # 本地文献检索（已实现）
├── backend/agents/tools/openalex_wrapper.py   # 外部文献检索（已实现）
├── backend/agents/tools/openalex_wrapper.py   # 外部文献检索（已实现）
└── backend/agents/models/novelty.py           # NoveltyResult + TransferAssessment 模型
```

### 7.2 输出到后续节点（调整后，2026-04-04）

```
Literature Node ──method_metadata──▶ Novelty Node：
│                                         │
│                        ┌────────────────┴────────────────┐
│                        │  迁移/组合/调整评估               │
│                        │  assess_transfer 节点            │
│                        └────────────────┬────────────────┘
│                                         │
└─────────────────────────────────────────┼─────────────────┘
                                          │
                                          ▼
                              Novelty Node 输出 ──▶ Brief Builder：
                              ├── novelty_result.novelty_position
                              ├── novelty_result.transfer_assessments
                              └── novelty_result.recommended_direction
                                  （含 transfer_context → 填入 Research_Brief.transfer_context）
```

---

## 八、实施检查清单

- [ ] NoveltyResult + TransferAssessment Pydantic 模型
- [ ] NoveltyState 状态定义（含 method_metadata, transfer_assessments）
- [ ] receive_literature 节点（新增）
- [ ] analyze_existing 节点
- [ ] assess_transfer 节点（新增核心节点）
- [ ] judge_novelty 节点（调整：输出含 transfer_context 的推荐方向）
- [ ] 中断处理逻辑
- [ ] 前端 NoveltyInterrupt UI 组件（含 transfer_assessments 展示）
- [ ] 端到端集成测试

---

## 九、下一步（调整后）

1. **Literature Node 调整**：确保 method_metadata 输出格式与本设计一致
2. **Research_Brief Schema 调整**：新增 transfer_context 字段（见调整3）
3. **Text-to-Code Bridge 调整**：输出适应性解释（见调整4）
4. **Analysis Node**（数据分析节点：调用 Text-to-Code Bridge 执行分析）
5. **Writing Node**（写作节点：基于 Research_Brief 生成论文提纲和草稿）
6. **Brief Builder**（汇总逻辑完善，含 transfer_context）
7. **4 个中断点的完整实现**
8. **SSE 状态推送**
