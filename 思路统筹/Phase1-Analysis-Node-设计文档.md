# Phase 1：Analysis Node 技术设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `Phase0-最小可运行骨架-实施计划.md`
> - `Phase1-Text-to-Code-Bridge-设计文档.md`

---

## 一、定位与职责

### 1.1 Analysis Node 定位

Analysis Node 是系统的**数据分析与模型匹配中心**，负责：
- 数据诊断与理解
- 模型选择与推荐
- 调用 Text-to-Code Bridge 生成并执行分析代码
- 产出分析结果（图表、数值结果）

### 1.2 与其他节点的关系

```
                    ┌──────────────────┐
                    │    Literature     │
                    │     Node         │
                    └────────┬─────────┘
                             │
                             │ method_decision
                             ▼
┌──────────────┐    ┌──────────────────┐
│    Novelty   │    │    Analysis      │
│     Node     │───▶│     Node         │
└──────────────┘    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   Text-to-   │ │   Brief     │ │  分析结果    │
    │   Code       │ │   Builder    │ │  (图表/数值) │
    │   Bridge     │ │             │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
```

**数据流向**：
- Literature Node 提供 `method_decision`（推荐模型）
- Novelty Node 提供 `novelty_result`（研究方向）
- Analysis Node 基于上述信息，结合数据，执行分析
- 调用 Text-to-Code Bridge 生成并执行代码
- 输出 `analysis_result` 到 Brief Builder

---

## 二、关键设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Bridge 调用方式 | 作为子图调用 | 保持 Bridge 独立复用性 |
| 数据传递方式 | 文件路径 | Bridge 需要读取数据文件 |
| 分析类型 | 主效应优先 | MVP 只支持单一因变量 + 少量自变量 |
| 中断处理 | 透传 Bridge 中断 | Bridge 的 quality_warning 中断直接透传 |
| 数据来源 | 用户上传 | MVP 仅支持单 sheet CSV |

### 2.1 MVP 约束说明

1. 数据分析默认处理单表输入。
2. 模型选择依赖 Literature Node 的 `method_decision`，不做独立推理。
3. Text-to-Code Bridge 的约束（evidence_required）同样适用于 Analysis Node。

---

## 三、数据结构

### 3.1 AnalysisState（子图状态）

```python
# backend/agents/orchestrator/subgraphs/analysis_state.py

from typing import TypedDict, Optional, List

class AnalysisState(TypedDict):
    task_id: str

    # 输入
    user_goal: str                          # 用户分析目标
    data_files: List[str]                   # 数据文件路径
    novelty_result: dict | None            # 来自 Novelty Node
    literature_result: dict | None          # 来自 Literature Node

    # 数据理解
    data_diagnosis: dict | None            # 数据诊断结果
    column_semantics: dict | None           # 列名语义解释

    # 分析决策
    recommended_analysis_type: str | None   # "indicator_construction" | "regression" | "prediction" | "visualization"
    recommended_models: List[str] | None    # 来自 Literature Node

    # Text-to-Code Bridge 调用
    bridge_input: dict | None              # 传递给 Bridge 的输入
    bridge_output: dict | None            # Bridge 输出
    bridge_status: str | None             # Bridge 执行状态

    # 分析结果
    analysis_result: dict | None          # 最终分析结果

    # 状态
    status: str  # "understanding" | "planning" | "executing" | "interrupted" | "done" | "error"
    interrupt_reason: str | None
    interrupt_data: dict | None
    human_decision: dict | None
    error_message: str | None
```

### 3.2 AnalysisResult（输出结构）

```python
# backend/agents/models/analysis.py

from pydantic import BaseModel, Field
from typing import List, Optional

class DataDiagnosis(BaseModel):
    """数据诊断"""
    file_name: str
    row_count: int
    column_count: int
    column_names: List[str]
    column_types: dict  # {"col_name": "int" | "float" | "str" | "datetime"}
    missing_values: dict  # {"col_name": count}
    outlier_columns: List[str] = Field(default_factory=list)
    panel_structure: dict | None = Field(default=None, description="面板数据结构")

class AnalysisResult(BaseModel):
    """Analysis Node 输出"""
    task_id: str

    # 数据摘要
    data_diagnosis: DataDiagnosis

    # 分析决策
    recommended_analysis_type: str
    recommended_models: List[str]

    # Bridge 执行结果
    bridge_executed: bool = False
    code_script: str = ""
    execution_result: dict | None = Field(default=None)

    # 分析输出
    charts: List[dict] = Field(default_factory=list, description="生成的图表")
    tables: List[dict] = Field(default_factory=list, description="生成的结果表")
    numerical_results: dict = Field(default_factory=dict, description="关键数值结果")

    # 质量信息
    quality_warnings: List[str] = Field(default_factory=list)

    # 元数据
    created_at: str
```

---

## 四、Analysis Node 子图设计

### 4.1 子图流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Analysis Node 子图                              │
│                                                                  │
│  ┌──────────────┐                                                │
│  │    start    │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────┐                                            │
│  │ understand_data   │  ← 诊断数据，理解列名语义                   │
│  │ (DuckDB 探查)   │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ plan_analysis     │  ← 结合 literature_result 制定分析计划     │
│  │ (LLM 规划)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ call_bridge       │  ← 调用 Text-to-Code Bridge               │
│  │ (子图调用)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ interrupt        │────▶│ human_decision  │  ← 透传 Bridge  │
│  │ (Bridge 中断)    │     └─────────────────┘      中断         │
│  └──────────────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ finalize_result   │  ← 汇总分析结果                           │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │      end        │                                            │
│  └──────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 节点详细设计

#### 4.2.1 understand_data 节点

```python
async def understand_data_node(state: AnalysisState) -> AnalysisState:
    """
    诊断数据，理解列名语义
    """
    import duckdb
    from backend.agents.tools.duckdb_wrapper import DuckDBWrapper

    data_files = state.get("data_files", [])
    if not data_files:
        state["error_message"] = "未提供数据文件"
        state["status"] = "error"
        return state

    data_file = data_files[0]  # MVP 默认单文件

    # 使用 DuckDB 探查数据
    duckdb_wrapper = DuckDBWrapper()
    diagnosis = await duckdb_wrapper.diagnose(data_file)

    # LLM 理解列名语义
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4")

    column_semantics_prompt = f"""
    数据文件：{data_file}

    列信息：
    {format_column_info(diagnosis)}

    任务：理解每个列的语义，识别其角色。

    返回JSON格式：
    {{
        "column_semantics": {{
            "col_name": {{
                "semantic": "语义描述",
                "role": "dependent_var | independent_var | control_var | id | time | other",
                "data_type": "continuous | binary | count | categorical"
            }}
        }},
        "panel_structure": {{
            "is_panel": true/false,
            "entity_column": "个体标识列",
            "time_column": "时间列",
            "suggested_analysis_type": "regression | prediction | indicator_construction | visualization"
        }}
    }}
    """

    response = await llm.ainvoke(column_semantics_prompt)
    result = json.loads(response.content)

    state["data_diagnosis"] = diagnosis
    state["column_semantics"] = result.get("column_semantics")
    state["panel_structure"] = result.get("panel_structure")
    state["status"] = "planning"

    return state
```

#### 4.2.2 plan_analysis 节点

```python
async def plan_analysis_node(state: AnalysisState) -> AnalysisState:
    """
    结合 literature_result 制定分析计划
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    user_goal = state["user_goal"]
    column_semantics = state.get("column_semantics", {})
    panel_structure = state.get("panel_structure", {})
    literature_result = state.get("literature_result", {})

    # 提取 Literature Node 的方法决策
    method_decision = literature_result.get("method_decision", {})
    recommended_models = method_decision.get("recommended_methods", [])

    planning_prompt = f"""
    用户分析目标：{user_goal}

    数据列语义：
    {json.dumps(column_semantics, indent=2, ensure_ascii=False)}

    面板数据结构：
    {json.dumps(panel_structure, indent=2, ensure_ascii=False)}

    文献推荐方法：
    {recommended_models}

    任务：制定分析计划。

    返回JSON格式：
    {{
        "recommended_analysis_type": "indicator_construction | regression | prediction | visualization",
        "recommended_models": ["模型列表"],
        "analysis_steps": ["步骤1", "步骤2"],
        "forbidden_operations": ["禁止的操作"]
    }}
    """

    response = await llm.ainvoke(planning_prompt)
    result = json.loads(response.content)

    state["recommended_analysis_type"] = result.get("recommended_analysis_type")
    state["recommended_models"] = result.get("recommended_models")
    state["analysis_plan"] = result.get("analysis_steps")
    state["forbidden_operations"] = result.get("forbidden_operations", [])

    # 准备 Bridge 输入
    state["bridge_input"] = {
        "task_id": state["task_id"],
        "user_goal": user_goal,
        "data_files": state["data_files"],
        "analysis_type": result.get("recommended_analysis_type"),
        "recommended_models": result.get("recommended_models"),
        "column_semantics": column_semantics,
        "forbidden_operations": state.get("forbidden_operations", [])
    }

    state["status"] = "executing"

    return state
```

#### 4.2.3 call_bridge 节点

```python
async def call_bridge_node(state: AnalysisState) -> AnalysisState:
    """
    调用 Text-to-Code Bridge 子图
    """
    from backend.agents.orchestrator.subgraphs.text_to_code_bridge import (
        build_text_to_code_graph,
        TextToCodeState
    )

    bridge_input = state.get("bridge_input", {})
    literature_result = state.get("literature_result", {})

    # 从 Literature Node 获取 evidence_package
    evidence_chunks = []
    if literature_result.get("all_chunks"):
        evidence_chunks = [
            {
                "chunk_id": c["chunk_id"],
                "source_file": c.get("source_file") or c.get("title"),
                "page_ref": c.get("page_ref"),
                "text": c["text"],
                "relevance_score": c.get("relevance_score", 0.5)
            }
            for c in literature_result["all_chunks"]
        ]

    # 构建 Bridge 状态
    bridge_state = TextToCodeState(
        task_id=state["task_id"],
        user_goal=bridge_input["user_goal"],
        data_files=bridge_input["data_files"],
        analysis_type=bridge_input["analysis_type"],
        evidence_package=None,  # Bridge 内部会自己检索
        generated_code=None,
        status="retrieving"
    )

    # 如果 Literature 已检索到证据，直接传入
    if evidence_chunks:
        bridge_state["evidence_package"] = {
            "task_id": state["task_id"],
            "evidence_chunks": evidence_chunks,
            "quality_score": literature_result.get("quality_score", 0.5),
            "quality_warning": None,
            "missing_aspects": []
        }

    # 运行 Bridge 子图
    text_to_code_graph = build_text_to_code_graph()

    try:
        result_state = None
        async for state_update in text_to_code_graph.astream(
            bridge_state,
            config={"configurable": {"thread_id": f"{state['task_id']}_analysis"}}
        ):
            result_state = state_update

            # 检查中断
            if result_state.get("status") == "interrupted":
                # 透传 Bridge 中断
                state["status"] = "interrupted"
                state["interrupt_reason"] = result_state.get("interrupt_reason")
                state["interrupt_data"] = result_state.get("interrupt_data")
                state["bridge_status"] = "interrupted"
                return state

        # Bridge 执行完成
        state["bridge_output"] = result_state
        state["bridge_status"] = "done"

        # 提取分析结果
        if result_state.get("execution_result"):
            state["analysis_result"] = {
                "code_script": result_state.get("generated_code", {}).get("code_script", ""),
                "execution_result": result_state["execution_result"],
                "charts": result_state["execution_result"].get("charts", []),
                "numerical_results": result_state["execution_result"].get("output_data", {})
            }

        state["status"] = "finalizing"

    except Exception as e:
        state["error_message"] = f"Bridge 执行失败: {str(e)}"
        state["status"] = "error"

    return state
```

#### 4.2.4 finalize_result 节点

```python
async def finalize_result_node(state: AnalysisState) -> AnalysisState:
    """
    汇总分析结果
    """
    from datetime import datetime

    bridge_output = state.get("bridge_output", {})
    execution_result = bridge_output.get("execution_result", {})

    state["analysis_result"] = {
        "task_id": state["task_id"],
        "data_diagnosis": state.get("data_diagnosis"),
        "recommended_analysis_type": state.get("recommended_analysis_type"),
        "recommended_models": state.get("recommended_models"),
        "bridge_executed": state.get("bridge_status") == "done",
        "code_script": bridge_output.get("generated_code", {}).get("code_script", ""),
        "execution_result": execution_result,
        "charts": execution_result.get("charts", []),
        "tables": [],  # 简化
        "numerical_results": execution_result.get("output_data", {}),
        "quality_warnings": bridge_output.get("generated_code", {}).get("quality_warnings", []),
        "created_at": datetime.utcnow().isoformat()
    }

    state["status"] = "done"

    return state
```

### 4.3 子图编译

```python
def build_analysis_graph():
    """编译 Analysis Node 子图"""

    workflow = StateGraph(AnalysisState)

    workflow.add_node("understand_data", understand_data_node)
    workflow.add_node("plan_analysis", plan_analysis_node)
    workflow.add_node("call_bridge", call_bridge_node)
    workflow.add_node("finalize_result", finalize_result_node)

    workflow.set_entry_point("understand_data")
    workflow.add_edge("understand_data", "plan_analysis")
    workflow.add_edge("plan_analysis", "call_bridge")

    # Bridge 中断透传
    workflow.add_conditional_edges(
        "call_bridge",
        lambda s: "interrupt" if s["status"] == "interrupted" else "finalize",
        {
            "interrupt": "__interrupt__",
            "finalize": "finalize_result"
        }
    )

    workflow.add_edge("finalize_result", END)

    return workflow.compile()
```

---

## 五、DuckDB Wrapper（数据诊断）

```python
# backend/agents/tools/duckdb_wrapper.py

import duckdb
from typing import Dict, List

class DuckDBWrapper:
    """DuckDB 数据处理封装"""

    async def diagnose(self, file_path: str) -> Dict:
        """
        诊断数据文件
        """
        conn = duckdb.connect(database=":memory:")

        # 读取数据
        if file_path.endswith(".csv"):
            df = conn.execute(f"SELECT * FROM read_csv_auto('{file_path}')").fetchdf()
        elif file_path.endswith(".parquet"):
            df = conn.execute(f"SELECT * FROM read_parquet('{file_path}')").fetchdf()
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

        # 基本统计
        diagnosis = {
            "file_name": file_path.split("/")[-1],
            "row_count": len(df),
            "column_count": len(df.columns),
            "column_names": list(df.columns),
            "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
            "outlier_columns": self._detect_outliers(df),
            "basic_stats": df.describe().to_dict()
        }

        conn.close()
        return diagnosis

    def _detect_outliers(self, df, threshold=3) -> List[str]:
        """检测异常值列（简化版）"""
        outlier_cols = []
        for col in df.select_dtypes(include=["number"]).columns:
            stats = df[col].describe()
            q1 = stats["25%"]
            q3 = stats["75%"]
            iqr = q3 - q1
            outliers = ((df[col] < q1 - threshold * iqr) | (df[col] > q3 + threshold * iqr)).sum()
            if outliers > 0:
                outlier_cols.append(col)
        return outlier_cols
```

---

## 六、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/models/analysis.py` | AnalysisResult 数据模型 |
| `backend/agents/orchestrator/subgraphs/analysis_state.py` | 子图状态定义 |
| `backend/agents/orchestrator/subgraphs/analysis_node.py` | Analysis Node 主逻辑 |
| `backend/agents/tools/duckdb_wrapper.py` | DuckDB 封装（数据诊断） |

---

## 七、依赖与输出

### 7.1 依赖

```
Analysis Node 依赖：
├── backend/agents/tools/duckdb_wrapper.py              # 数据诊断
├── backend/agents/tools/paperqa_wrapper.py             # 复用
├── backend/agents/tools/openalex_wrapper.py            # 复用
├── backend/agents/orchestrator/subgraphs/text_to_code_bridge.py  # Bridge 子图
└── literature_result from Literature Node
```

### 7.2 输出

```
Analysis Node 输出 → Brief Builder：
├── analysis_result.data_diagnosis        # 数据摘要
├── analysis_result.code_script           # 执行的代码
├── analysis_result.execution_result      # 执行结果
├── analysis_result.charts               # 图表列表
└── analysis_result.numerical_results    # 数值结果
```

---

## 八、实施检查清单

- [ ] AnalysisResult 数据模型
- [ ] AnalysisState 状态定义
- [ ] DuckDB Wrapper（数据诊断）
- [ ] understand_data 节点
- [ ] plan_analysis 节点
- [ ] call_bridge 节点（调用 Bridge 子图）
- [ ] Bridge 中断透传
- [ ] finalize_result 节点
- [ ] 端到端集成测试
