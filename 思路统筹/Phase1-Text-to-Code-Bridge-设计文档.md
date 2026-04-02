# Phase 1：Text-to-Code Bridge 技术设计文档

> **版本**：v0.1
> **日期**：2026-04-02
> **前置文档**：`Phase0-最小可运行骨架-实施计划.md`

---

## 一、设计目标

Text-to-Code Bridge 是系统的**核心约束层**，确保任何关键分析代码的生成都基于真实的学术依据。

**核心原则**：`No evidence, no code`

---

## 二、关键设计决策（已确认）

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 证据不足处理 | 警告但仍生成 | 灵活性优先，用户可override |
| 证据质量评估 | LLM自动评估 | 自动化，减少人工介入 |
| 代码审核方式 | 自动检查后执行 | 速度优先，但有安全边界 |
| 代码执行沙箱 | Pyodide | 浏览器内WebAssembly，部署简单 |
| 数据传递方式 | 文件路径读取 | 数据存Redis/文件，代码读路径 |
| 证据映射格式 | 结构化证据包 | chunk_id + text + page_ref，可追溯 |
| Bridge形态 | 独立LangGraph子图 | 支持复杂多步流程 |

---

## 三、数据结构

### 3.1 Evidence Package（结构化证据包）

```python
from typing import TypedDict, Optional, List
from pydantic import BaseModel

class EvidenceChunk(BaseModel):
    """单个证据块"""
    chunk_id: str           # 证据ID，如 "chunk_101"
    source_file: str        # 来源文件，如 "参考文献01.pdf"
    page_ref: str           # 页码引用，如 "p.45"
    text: str               # 证据文本
    relevance_score: float  # 与任务的相关性评分 0-1

class EvidencePackage(BaseModel):
    """证据包：代码生成所需的所有依据"""
    task_id: str
    evidence_chunks: List[EvidenceChunk]
    quality_score: float    # 整体质量评分 0-1
    quality_warning: str | None  # 质量问题警告
    missing_aspects: List[str]  # 缺失的方面
```

### 3.2 Code Generation Request（代码生成请求）

```python
class CodeGenRequest(BaseModel):
    """代码生成请求"""
    task_id: str
    user_goal: str                           # 用户目标描述
    evidence_package: EvidencePackage         # 证据包
    data_files: List[str]                    # 数据文件路径
    output_schema: dict | None               # 期望输出格式
    forbidden_operations: List[str]          # 禁止的操作
    code_template: str | None                # 代码模板（可选）
```

### 3.3 Generated Code（生成的代码）

```python
class GeneratedCode(BaseModel):
    """生成的代码及其元数据"""
    code_script: str                          # Python代码
    imports: List[str]                       # 所需导入
    execution_plan: List[str]                 # 执行步骤说明
    evidence_bindings: List[dict]             # 每个步骤的证据绑定
    # evidence_bindings 示例：
    # [
    #   {
    #     "step": 1,
    #     "operation": "计算碳排放总量",
    #     "formula": "CO2 = Σ(activity_data × emission_factor)",
    #     "evidence_chunk_id": "chunk_101",
    #     "line_numbers": [15, 16, 17]
    #   }
    # ]
    quality_warnings: List[str]               # 质量问题警告
    auto_check_result: dict                  # 自动检查结果
```

### 3.4 Code Execution Result（代码执行结果）

```python
class ExecutionResult(BaseModel):
    """代码执行结果"""
    success: bool
    output_data: dict | None                 # 输出数据
    charts: List[str] | None                 # 生成的图表路径
    error_message: str | None
    execution_time_ms: int
    numeric_verification: dict | None         # 数值验证结果
    # numeric_verification 示例：
    # {
    #   "total_carbon_2020": 523.41,
    #   "expected_value": 523.41,
    #   "tolerance": 0.5,
    #   "passed": True
    # }
```

---

## 四、Text-to-Code Bridge 子图设计

### 4.1 子图状态定义

```python
# backend/agents/orchestrator/subgraphs/text_to_code_state.py

from typing import TypedDict, Optional, List
from .evidence_package import EvidencePackage, EvidenceChunk
from .generated_code import GeneratedCode, ExecutionResult

class TextToCodeState(TypedDict):
    """Text-to-Code Bridge 子图状态"""
    task_id: str

    # 输入
    user_goal: str
    data_files: List[str]
    analysis_type: str  # "indicator_construction" | "regression" | "prediction" | "visualization"

    # Evidence 检索
    evidence_package: Optional[EvidencePackage]
    evidence_retrieval_error: str | None

    # 代码生成
    generated_code: Optional[GeneratedCode]
    code_generation_error: str | None

    # 中断相关
    status: str  # "retrieving" | "generating" | "checking" | "executing" | "interrupted" | "done" | "error"
    interrupt_reason: str | None
    interrupt_data: dict | None
    human_decision: dict | None

    # 输出
    execution_result: Optional[ExecutionResult]
    final_output: dict | None
```

### 4.2 子图节点设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Text-to-Code Bridge 子图                      │
│                                                                  │
│  ┌──────────────┐                                                │
│  │  start      │                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────┐                                            │
│  │ retrieve_evidence │  ← 调用 paper-qa 检索证据                  │
│  │ (LLM评估质量)    │                                            │
│  └────────┬─────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ evaluate_quality │────▶│ quality_warning │ → 中断展示警告   │
│  │ (LLM判断)        │     └─────────────────┘                   │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ generate_code    │  ← 基于证据包生成代码                       │
│  │ (LLM生成+注释)   │     绑定 evidence_chunk_id                 │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ auto_check       │────▶│ syntax_error    │ → 返回错误       │
│  │ (语法+安全检查)   │     └─────────────────┘                   │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ execute_code     │  ← Pyodide 执行                           │
│  │ (沙箱环境)       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ verify_results   │  ← 数值验证（如有期望值）                  │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │    end          │                                            │
│  └──────────────────┘                                            │
│                                                                  │
│  中断点：quality_warning（证据质量警告，用户选择是否继续）          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 节点实现

#### 4.3.1 Evidence 检索节点

```python
# backend/agents/orchestrator/subgraphs/text_to_code_bridge.py

async def retrieve_evidence_node(state: TextToCodeState) -> TextToCodeState:
    """
    检索证据节点
    调用 paper-qa 检索相关文献和方法依据
    """
    from backend.agents.tools.paperqa_wrapper import PaperQATool

    paperqa = PaperQATool()

    # 根据任务类型构建检索查询
    query = build_evidence_query(
        goal=state["user_goal"],
        analysis_type=state["analysis_type"],
        data_files=state["data_files"]
    )

    try:
        evidence_chunks = await paperqa.retrieve(
            query=query,
            top_k=5,
            filters={
                "file_types": [".pdf", ".docx"],
                "min_relevance": 0.3
            }
        )

        return {
            **state,
            "evidence_package": {
                "task_id": state["task_id"],
                "evidence_chunks": evidence_chunks,
                "quality_score": 0.0,  # 待评估
                "quality_warning": None,
                "missing_aspects": []
            },
            "status": "retrieving"
        }
    except Exception as e:
        return {
            **state,
            "evidence_retrieval_error": str(e),
            "status": "error"
        }


def build_evidence_query(goal: str, analysis_type: str, data_files: list) -> str:
    """构建证据检索查询"""
    templates = {
        "indicator_construction": (
            f"基于文献中的公式和系数表，构建指标计算方法。"
            f"用户目标：{goal}。"
            f"需要检索：碳排放系数、计算公式、变量定义"
        ),
        "regression": (
            f"查找回归分析方法的选择依据和实现步骤。"
            f"用户目标：{goal}。"
            f"需要检索：模型选择理由、变量处理方法、稳健性检验"
        ),
        "prediction": (
            f"查找时间序列预测或情景模拟的方法依据。"
            f"用户目标：{goal}。"
            f"需要检索：预测方法、情景设定、数据处理"
        ),
        "visualization": (
            f"查找数据可视化的最佳实践和图表选择依据。"
            f"用户目标：{goal}。"
            f"需要检索：图表类型选择、配色规范、标注方式"
        )
    }
    return templates.get(analysis_type, goal)
```

#### 4.3.2 Evidence 质量评估节点

```python
async def evaluate_quality_node(state: TextToCodeState) -> TextToCodeState:
    """
    评估证据质量
    LLM 判断证据是否充分，生成警告
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    evidence = state.get("evidence_package") or {}
    chunks = evidence.get("evidence_chunks", [])

    if not chunks:
        return {
            **state,
            "status": "interrupted",
            "interrupt_reason": "no_evidence_found",
            "interrupt_data": {
                "message": "未找到相关证据",
                "user_goal": state["user_goal"],
                "suggestion": "请尝试调整研究问题或上传更相关的文献"
            }
        }

    # LLM 评估证据质量
    quality_prompt = f"""
    评估以下证据是否充分支持代码生成：

    用户目标：{state["user_goal']}
    分析类型：{state["analysis_type"]}

    证据列表：
    {format_evidence_for_evaluation(chunks)}

    评估维度：
    1. 相关性：证据是否直接支持用户目标？
    2. 完整性：是否包含必要的公式、系数、变量定义？
    3. 具体性：证据是否足够具体可操作？

    返回JSON格式：
    {{
        "quality_score": 0.0-1.0,
        "quality_warning": "问题描述或null",
        "missing_aspects": ["缺失的方面列表"],
        "can_proceed": true/false
    }}
    """

    response = await llm.ainvoke(quality_prompt)
    evaluation = json.loads(response.content)

    # 如果证据质量低，中断等待用户确认
    if evaluation["can_proceed"] is False or evaluation["quality_score"] < 0.5:
        return {
            **state,
            "evidence_package": {
                **evidence,
                "quality_score": evaluation["quality_score"],
                "quality_warning": evaluation["quality_warning"],
                "missing_aspects": evaluation["missing_aspects"]
            },
            "status": "interrupted",
            "interrupt_reason": "low_evidence_quality",
            "interrupt_data": {
                "quality_score": evaluation["quality_score"],
                "warnings": evaluation["quality_warning"],
                "missing_aspects": evaluation["missing_aspects"],
                "chunks": chunks,  # 展示给用户
                "can_proceed_anyway": True  # 用户可选择继续
            }
        }

    return {
        **state,
        "evidence_package": {
            **evidence,
            "quality_score": evaluation["quality_score"],
            "quality_warning": evaluation["quality_warning"],
            "missing_aspects": evaluation["missing_aspects"]
        },
        "status": "generating"
    }


def format_evidence_for_evaluation(chunks: list) -> str:
    """格式化证据供评估使用"""
    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[{i}] {chunk['source_file']} (p.{chunk['page_ref']})")
        lines.append(f"    {chunk['text'][:500]}...")
    return "\n".join(lines)
```

#### 4.3.3 代码生成节点

```python
async def generate_code_node(state: TextToCodeState) -> TextToCodeState:
    """
    基于证据包生成代码
    每个关键步骤绑定证据来源
    """
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")

    evidence = state["evidence_package"]
    chunks = evidence["evidence_chunks"]

    # 构建代码生成提示词
    code_gen_prompt = f"""
    基于以下证据，生成Python数据分析代码。

    用户目标：{state["user_goal"]}
    分析类型：{state["analysis_type"]}
    数据文件：{state["data_files"]}

    证据包：
    {format_evidence_for_codegen(chunks)}

    要求：
    1. 代码必须基于上述证据，不能凭空编造
    2. 每个关键计算步骤必须附带 evidence_chunk_id 注释
    3. 使用 pandas 处理数据，statsmodels/pyodide 进行分析
    4. 禁止的操作：{state.get('forbidden_operations', [])}
    5. 输出期望格式：{state.get('output_schema', '灵活输出')}

    返回JSON格式：
    {{
        "code_script": "完整的Python代码",
        "imports": ["需要的导入"],
        "execution_plan": ["步骤1", "步骤2"],
        "evidence_bindings": [
            {{
                "step": 1,
                "operation": "操作描述",
                "formula": "使用的公式",
                "evidence_chunk_id": "chunk_xxx",
                "line_numbers": [行号]
            }}
        ],
        "quality_warnings": ["警告列表"]
    }}
    """

    response = await llm.ainvoke(code_gen_prompt)
    result = json.loads(response.content)

    return {
        **state,
        "generated_code": result,
        "status": "checking"
    }


def format_evidence_for_codegen(chunks: list) -> str:
    """格式化证据供代码生成使用"""
    lines = []
    for chunk in chunks:
        lines.append(f"\n【证据ID: {chunk['chunk_id']}】")
        lines.append(f"来源: {chunk['source_file']}, p.{chunk['page_ref']}")
        lines.append(f"内容: {chunk['text']}")
    return "\n".join(lines)
```

#### 4.3.4 自动检查节点

```python
def auto_check_node(state: TextToCodeState) -> TextToCodeState:
    """
    自动检查生成的代码
    语法检查 + 安全检查
    """
    import ast
    import re

    code = state.get("generated_code", {}).get("code_script", "")

    errors = []

    # 1. 语法检查
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"语法错误: {e}")

    # 2. 安全检查
    forbidden_patterns = [
        (r"os\.system", "禁止使用 os.system"),
        (r"subprocess\.", "禁止使用 subprocess"),
        (r"eval\(", "禁止使用 eval"),
        (r"exec\(", "禁止使用 exec"),
        (r"__import__", "禁止使用 __import__"),
        (r"open\([^)]*['\"][wr]", "禁止直接读写文件"),
        (r"import\s+os", "禁止导入 os 模块"),
        (r"import\s+subprocess", "禁止导入 subprocess 模块"),
    ]

    for pattern, message in forbidden_patterns:
        if re.search(pattern, code):
            errors.append(message)

    # 3. 依赖检查
    # 检查是否有 paper-qa 等不兼容的导入

    if errors:
        return {
            **state,
            "status": "error",
            "code_generation_error": "\n".join(errors)
        }

    return {
        **state,
        "generated_code": {
            **state["generated_code"],
            "auto_check_result": {"passed": True, "warnings": []}
        },
        "status": "executing"
    }
```

#### 4.3.5 代码执行节点

```python
async def execute_code_node(state: TextToCodeState) -> TextToCodeState:
    """
    在 Pyodide 沙箱中执行代码
    """
    import subprocess
    import tempfile
    import os

    code = state["generated_code"]["code_script"]
    data_files = state["data_files"]

    # 准备执行环境
    # 方式1：使用 Pyodide.js（前端）
    # 方式2：使用 Pyodide Python包（后端）
    # 这里假设使用 Pyodide Python包

    try:
        import pyodide

        # 创建临时代码文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # 在 Pyodide 中执行
            # 注意：Pyodide 有一些限制（无网络、无文件系统访问等）
            result = await pyodide.runPythonAsync(code)

            return {
                **state,
                "execution_result": {
                    "success": True,
                    "output_data": result,
                    "charts": extract_chart_paths(result),
                    "error_message": None,
                    "execution_time_ms": 0,  # 简化
                    "numeric_verification": None
                },
                "status": "done",
                "final_output": result
            }

        finally:
            os.unlink(temp_file)

    except Exception as e:
        return {
            **state,
            "execution_result": {
                "success": False,
                "output_data": None,
                "charts": None,
                "error_message": str(e),
                "execution_time_ms": 0,
                "numeric_verification": None
            },
            "status": "error"
        }
```

### 4.4 子图编译

```python
# backend/agents/orchestrator/subgraphs/text_to_code_bridge.py

def build_text_to_code_graph():
    """编译 Text-to-Code Bridge 子图"""

    workflow = StateGraph(TextToCodeState)

    # 添加节点
    workflow.add_node("retrieve_evidence", retrieve_evidence_node)
    workflow.add_node("evaluate_quality", evaluate_quality_node)
    workflow.add_node("generate_code", generate_code_node)
    workflow.add_node("auto_check", auto_check_node)
    workflow.add_node("execute_code", execute_code_node)
    workflow.add_node("verify_results", verify_results_node)

    # 设置边
    workflow.set_entry_point("retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "evaluate_quality")

    # 条件边：质量评估结果
    workflow.add_conditional_edges(
        "evaluate_quality",
        lambda s: "interrupt" if s["status"] == "interrupted" else "generate",
        {
            "interrupt": "__interrupt__",
            "generate": "generate_code"
        }
    )

    workflow.add_edge("generate_code", "auto_check")

    # 条件边：检查结果
    workflow.add_conditional_edges(
        "auto_check",
        lambda s: "error" if s["status"] == "error" else "execute",
        {
            "error": END,
            "execute": "execute_code"
        }
    )

    workflow.add_edge("execute_code", "verify_results")
    workflow.add_edge("verify_results", END)

    return workflow.compile()
```

---

## 五、中断处理

### 5.1 中断场景

| 中断点 | 触发条件 | 展示内容 | 用户选项 |
|--------|----------|----------|----------|
| 证据检索失败 | paper-qa 无结果 | 提示信息 | 调整问题 / 跳过 |
| 证据质量低 | quality_score < 0.5 | 质量问题列表 | 继续生成 / 终止 |
| 代码执行失败 | Pyodide 报错 | 错误信息 | 查看代码 / 重试 |

### 5.2 前端中断 UI

```typescript
// 当 interrupt_reason === "low_evidence_quality" 时展示

{
  status: "interrupted",
  interrupt_reason: "low_evidence_quality",
  interrupt_data: {
    quality_score: 0.35,
    warnings: "证据中缺少具体的碳排放系数表",
    missing_aspects: ["碳排放系数", "分项计算公式"],
    can_proceed_anyway: true
  }
}
```

```tsx
<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
  <h3 className="font-bold text-yellow-800 mb-2">⚠️ 证据质量警告</h3>

  <div className="mb-3">
    <p className="text-sm text-yellow-700">
      证据质量评分：{interrupt_data.quality_score}/1.0
    </p>
    <div className="w-full bg-yellow-200 rounded-full h-2">
      <div
        className="bg-yellow-600 h-2 rounded-full"
        style={{ width: `${interruptData.quality_score * 100}%` }}
      />
    </div>
  </div>

  {interruptData.warnings && (
    <div className="mb-3 p-2 bg-yellow-100 rounded">
      <p className="font-semibold text-sm">问题：</p>
      <p className="text-sm">{interruptData.warnings}</p>
    </div>
  )}

  {interruptData.missing_aspects?.length > 0 && (
    <div className="mb-3">
      <p className="font-semibold text-sm">缺失内容：</p>
      <ul className="list-disc pl-5 text-sm">
        {interruptData.missing_aspects.map((aspect: string) => (
          <li>{aspect}</li>
        ))}
      </ul>
    </div>
  )}

  <div className="flex gap-3 mt-4">
    <button
      onClick={() => handleContinue("approved")}
      className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
    >
      继续生成代码（已了解风险）
    </button>
    <button
      onClick={() => handleContinue("cancelled")}
      className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
    >
      取消
    </button>
  </div>
</div>
```

---

## 六、调用方式

### 6.1 从 Analysis Node 调用

```python
# backend/agents/orchestrator/subgraphs/analysis_node.py

async def analysis_node(state: MainState) -> MainState:
    """
    Analysis Node 调用 Text-to-Code Bridge
    """
    # 检查是否需要代码生成
    if not needs_code_generation(state):
        return await analyze_without_code(state)

    # 调用 Text-to-Code Bridge
    from .text_to_code_bridge import build_text_to_code_graph

    text_to_code_graph = build_text_to_code_graph()

    # 准备输入状态
    code_state = {
        "task_id": state["task_id"],
        "user_goal": extract_code_goal(state),
        "data_files": extract_data_files(state),
        "analysis_type": determine_analysis_type(state),
        "evidence_package": None,
        "generated_code": None,
        "status": "retrieving"
    }

    # 运行子图
    result_state = None
    async for state_update in text_to_code_graph.astream(
        code_state,
        config={"configurable": {"thread_id": f"{state['task_id']}_tc"}}
    ):
        result_state = state_update

        # 检查是否中断
        if state_update.get("status") == "interrupted":
            # 中断等待用户确认
            return {
                **state,
                "status": "interrupted",
                "interrupt_reason": state_update["interrupt_reason"],
                "interrupt_data": state_update["interrupt_data"],
                "current_node": "analysis"
            }

    # 代码执行完成，继续分析
    return await finalize_analysis(state, result_state)
```

---

## 七、与其他模块的集成

### 7.1 与 Literature Node 的关系

```
Literature Node                     Text-to-Code Bridge
      │                                    │
      │  发现需要代码执行的指标构造          │
      ▼                                    │
生成 method_decision ─────────────────────▶│
      │                                    │
      │  包含 evidence_sources              │
      │  包含 method_formula                │
      ▼                                    │
      │                                     ▼
      │                            基于这些依据生成代码
      │                                     │
      ◀────────────────────────────────────┘
      │
      ▼
返回 Analysis Result
```

### 7.2 与 Brief Builder 的关系

```
Text-to-Code Bridge 执行结果 ──▶ Brief Builder
                                        │
├── analysis_outputs.code_script        │
├── analysis_outputs.execution_result   │
├── evidence_bindings ──────────────────▶ evidence_map
│
└── 生成的图表和数值结果 ──────────────▶ analysis_outputs
```

---

## 八、错误处理

### 8.1 错误分类

| 错误类型 | 处理策略 | 是否可重试 |
|----------|----------|------------|
| 证据检索超时 | 降级：使用已有证据 | 是 |
| 证据检索无结果 | 中断：提示用户 | 否 |
| LLM 生成失败 | 重试 2 次后报错 | 是 |
| 代码语法错误 | 返回错误，要求重新生成 | 否 |
| Pyodide 执行超时 | 降级：限制执行时间 | 是 |
| Pyodide 执行崩溃 | 报错，记录错误信息 | 否 |

### 8.2 重试机制

```python
def with_retry(func, max_attempts=2):
    """带重试的装饰器"""
    async def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # 指数退避
        raise last_error
    return wrapper
```

---

## 九、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | 主子图 + 节点实现 |
| `backend/agents/orchestrator/subgraphs/text_to_code_state.py` | 子图状态定义 |
| `backend/agents/models/evidence_package.py` | EvidencePackage 模型 |
| `backend/agents/models/code_generation.py` | 代码生成相关模型 |
| `backend/agents/tools/paperqa_wrapper.py` | paper-qa 封装 |
| `backend/core/sandbox.py` | Pyodide 沙箱管理 |

---

## 十、下一步

### 10.1 待讨论

- Literature Node 内部设计
- Research_Brief Schema 完整字段
- 其他 4 个节点的实现

### 10.2 实施顺序建议

1. **Text-to-Code Bridge**（已设计）
2. **Literature Node**（为 Bridge 提供证据）
3. **Research_Brief Schema**（统一数据格式）
4. **Analysis Node**（调用 Bridge）
5. **Brief Builder + Writing Node**
