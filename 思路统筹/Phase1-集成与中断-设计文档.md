# Phase 1：集成与中断设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `Phase1-Novelty-Node-设计文档.md`
> - `Phase1-Literature-Node-设计文档.md`
> - `Phase1-Text-to-Code-Bridge-设计文档.md`
> - `Phase1-Analysis-Node-设计文档.md`
> - `Phase1-Writing-Node-设计文档.md`
> - `Phase1-Research-Brief-Schema-设计文档.md`

---

## 一、Brief Builder 完善设计

### 1.1 Brief Builder 定位

Brief Builder 是系统的**数据汇聚中心**，负责：
- 汇总所有节点输出到 Research_Brief
- 验证数据完整性
- 提供人工编辑接口
- 管理版本历史

### 1.2 子图流程

```
┌─────────────────────────────────────────────────────────────────┐
│                 Brief Builder 子图                                │
│                                                                  │
│  ┌──────────────┐                                                │
│  │    start    │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────┐                                            │
│  │ collect_inputs    │  ← 收集所有节点输出                        │
│  │                  │    novelty/literature/analysis/writing      │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ assemble_brief    │  ← 组装 Research_Brief                    │
│  │                  │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ validate_brief    │  ← 验证 Schema 完整性                     │
│  │                  │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌─────────────────┐                   │
│  │ interrupt        │────▶│ human_edit       │  ← Brief 中断    │
│  │ (编辑确认)       │     └─────────────────┘                   │
│  └──────────────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │ save_version      │  ← 保存到 Redis                           │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐                                            │
│  │      end        │                                            │
│  └──────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Brief Builder 节点实现

```python
# backend/agents/orchestrator/subgraphs/brief_builder_node.py

async def brief_builder_node(state: MainState) -> MainState:
    """
    Brief Builder 汇总所有节点输出
    构建 Research_Brief
    """
    from datetime import datetime
    from backend.agents.models.research_brief import ResearchBrief
    from backend.core.brief_version import BriefVersionManager
    from backend.core.redis import get_redis
    import uuid

    task_id = state["task_id"]

    # 1. 收集所有节点输出
    novelty_result = state.get("novelty_result")
    literature_result = state.get("literature_result")
    analysis_result = state.get("analysis_result")
    writing_result = state.get("writing_result")

    # 2. 组装 Brief 数据
    brief_data = {
        "version": "1.0.0",
        "brief_id": f"brief_{task_id}_{datetime.utcnow().isoformat()}",
        "task_id": task_id,
        "task_type": state.get("task_type", "analysis"),
        "research_goal": state.get("user_query", ""),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "draft"
    }

    # 填充 Novelty Position
    if novelty_result:
        brief_data["novelty_position"] = {
            "overlap_with_existing": novelty_result.get("overlap_with_existing", []),
            "differentiation_points": novelty_result.get("differentiation_points", []),
            "suggested_topic_directions": novelty_result.get("suggested_topic_directions", []),
            "novelty_score": novelty_result.get("novelty_score", 0.0),
            "human_approved": novelty_result.get("human_approved", False)
        }

    # 填充 Literature Result → Evidence Map + Method Decision
    if literature_result:
        # Evidence Map
        all_chunks = literature_result.get("all_chunks", [])
        claims = []
        for i, chunk in enumerate(all_chunks[:10]):  # 最多10条
            claims.append({
                "claim_id": f"claim_{i+1}",
                "claim_text": chunk.get("text", "")[:200],
                "source_chunk_ids": [chunk.get("chunk_id", "")],
                "source_files": [chunk.get("source_file", "")],
                "confidence": chunk.get("relevance_score", 0.5),
                "is_verified": False
            })

        brief_data["evidence_map"] = {"claims": claims}

        # Method Decision
        method_decision = literature_result.get("method_decision", {})
        brief_data["method_decision"] = {
            "recommended_models": method_decision.get("recommended_methods", []),
            "rejected_models": method_decision.get("rejected_methods", []),
            "reasoning": method_decision.get("reasoning", ""),
            "evidence_sources": [c.get("chunk_id") for c in all_chunks],
            "model_parameters": {},
            "robustness_checks": []
        }

        # References
        references = literature_result.get("references", [])
        brief_data["references"] = references

    # 填充 Analysis Outputs
    if analysis_result:
        brief_data["analysis_outputs"] = {
            "code_script": analysis_result.get("code_script", ""),
            "execution_status": "success" if analysis_result.get("execution_result") else "pending",
            "execution_result": analysis_result.get("execution_result"),
            "charts": analysis_result.get("charts", []),
            "tables": analysis_result.get("tables", []),
            "numerical_results": analysis_result.get("numerical_results", {}),
            "error_message": analysis_result.get("error_message")
        }

        # Data Summary
        if analysis_result.get("data_diagnosis"):
            brief_data["data_summary"] = {
                "files": [{"file_name": analysis_result["data_diagnosis"].get("file_name", "")}],
                "total_rows": analysis_result["data_diagnosis"].get("row_count", 0),
                "total_columns": analysis_result["data_diagnosis"].get("column_count", 0),
                "column_types": analysis_result["data_diagnosis"].get("column_types", {}),
                "diagnostic_notes": ""
            }

    # 填充 Draft Sections
    if writing_result:
        brief_data["draft_sections"] = {
            "outline": writing_result.get("outline", ""),
            "abstract": writing_result.get("abstract", ""),
            "introduction": writing_result.get("introduction", ""),
            "methods": writing_result.get("methods", ""),
            "results": writing_result.get("results", ""),
            "discussion": writing_result.get("discussion", ""),
            "references": writing_result.get("references", "")
        }

    # 3. 添加审计条目
    brief_data["audit_trail"] = [{
        "entry_id": f"audit_{uuid.uuid4().hex[:12]}",
        "timestamp": datetime.utcnow().isoformat(),
        "node": "brief",
        "action": "node_output",
        "node_output_summary": "Brief Builder 汇总各节点输出"
    }]

    # 4. 验证 Brief
    validation_errors = []
    warnings = []

    try:
        brief = ResearchBrief.model_validate(brief_data)
    except ValidationError as e:
        validation_errors = e.errors()
        warnings.append(f"部分字段验证失败")

    # 5. 中断等待用户编辑
    return {
        **state,
        "brief_id": brief_data["brief_id"],
        "current_brief": brief_data,
        "validation_errors": validation_errors,
        "warnings": warnings,
        "status": "interrupted",
        "interrupt_reason": "brief_ready_for_review",
        "interrupt_data": {
            "brief": brief_data,
            "validation_errors": validation_errors,
            "warnings": warnings,
            "can_proceed": len(validation_errors) == 0
        }
    }
```

---

## 二、五中断点集成设计（调整后，2026-04-04）

### 2.1 中断点总览

| 中断点 | 节点 | 触发时机 | 用户决策 |
|--------|------|----------|----------|
| **数据映射中断（新增）** | 数据准备 | 用户上传数据后自动解析 + 预览 | 确认变量映射/修改/取消上传 |
| Novelty 中断 | Novelty Node | 迁移/组合/调整评估完成 | 确认迁移方向/修改/拒绝 |
| Bridge 中断 | Text-to-Code Bridge | 证据质量警告 | 继续/终止 |
| Brief 中断 | Brief Builder | Research_Brief 组装完成 | 确认/编辑/终止 |
| Writing 中断 | Writing Node | 草稿生成完成 | 确认/修改/重新生成 |

### 2.2 数据映射中断（新增，2026-04-04）

**触发时机**：用户上传数据文件后，系统自动解析列名、数据类型、面板结构，然后中断等待用户确认。

**用户看到的内容**：
- 自动解析出的列名列表
- 检测到的数据类型（数值型/文本型/日期型）
- 检测到的面板结构（如果有地区+年份列）
- 推荐的数据结构判断（面板/截面/时间序列）

**用户需要做的决策**：
- 确认/修改因变量 (Y)
- 确认/修改自变量 (X) 列表
- 确认/修改控制变量列表
- 确认/修改地区列（面板数据）
- 确认/修改年份列（面板数据）
- 确认/取消上传

```json
{
  "status": "interrupted",
  "interrupt_reason": "data_mapping_required",
  "interrupt_data": {
    "file_name": "zhejiang_carbon.csv",
    "detected_columns": ["地区", "年份", "农业产值", "碳排放", "农药使用量", "GDP"],
    "detected_types": {
      "地区": "文本",
      "年份": "数值",
      "农业产值": "数值",
      "碳排放": "数值",
      "农药使用量": "数值",
      "GDP": "数值"
    },
    "detected_panel_structure": {
      "is_panel": true,
      "potential_entity_column": "地区",
      "potential_time_column": "年份"
    },
    "recommended_mapping": {
      "dependent_var": "碳排放",
      "independent_vars": ["农业产值"],
      "control_vars": ["农药使用量", "GDP"],
      "entity_column": "地区",
      "time_column": "年份"
    }
  }
}
```

### 2.3 Novelty 中断的内涵调整（2026-04-04）

**调整前**：展示重复点/区分点/推荐方向

**调整后**：展示的内容更丰富——
- **迁移评估结果**：每个候选方法的迁移可行性、需要的调整、风险点
- **组合选项**：可组合的方法及组合价值
- **推荐方向**：含完整的迁移逻辑说明（来源方法→如何迁移→需要做什么调整）
- **变量映射**：原方法变量到用户变量的映射关系

### 2.2 API 层中断处理

```python
# backend/api/routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ContinueTaskRequest(BaseModel):
    """继续任务请求"""
    task_id: str
    node: str  # "novelty" | "bridge" | "brief" | "writing"
    decision: str  # "approved" | "modified" | "rejected" | "cancelled"
    data: dict | None = None  # 决策数据（如修改内容）

@router.post("/tasks/{task_id}/continue")
async def continue_task(task_id: str, req: ContinueTaskRequest):
    """
    处理中断后继续任务
    """
    # 1. 获取当前任务状态
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "interrupted":
        raise HTTPException(status_code=400, detail="Task is not interrupted")

    # 2. 构建决策数据
    human_decision = {
        "decision": req.decision,
        "data": req.data or {},
        "timestamp": datetime.utcnow().isoformat()
    }

    # 3. 更新任务状态，触发 LangGraph 继续执行
    updated_task = await langgraph.continue_task(
        task_id=task_id,
        human_decision=human_decision
    )

    return {
        "task_id": task_id,
        "status": updated_task["status"],
        "current_node": updated_task["current_node"]
    }
```

### 2.3 Main Graph 中断处理

```python
# backend/agents/orchestrator/main_graph.py

from langgraph.graph import StateGraph, END
from backend.agents.models.state import MainState

def build_main_graph():
    """构建主图"""

    workflow = StateGraph(MainState)

    # 添加所有节点
    workflow.add_node("novelty", novelty_node)
    workflow.add_node("literature", literature_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("brief", brief_builder_node)
    workflow.add_node("writing", writing_node)

    # 设置入口点
    workflow.set_entry_point("novelty")

    # 边
    workflow.add_edge("novelty", "literature")
    workflow.add_edge("literature", "analysis")
    workflow.add_edge("analysis", "brief")
    workflow.add_edge("brief", "writing")
    workflow.add_edge("writing", END)

    # 中断点配置
    interrupt_config = {
        "novelty": {
            "condition": lambda s: s.get("status") == "interrupted" and "novelty" in s.get("interrupt_reason", ""),
            "resume_node": "literature"  # 继续后进入 literature
        },
        "brief": {
            "condition": lambda s: s.get("status") == "interrupted" and "brief" in s.get("interrupt_reason", ""),
            "resume_node": "writing"  # 继续后进入 writing
        },
        "writing": {
            "condition": lambda s: s.get("status") == "interrupted" and "writing" in s.get("interrupt_reason", ""),
            "resume_node": END  # 继续后结束
        }
    }

    return workflow.compile()
```

---

## 三、中断前端组件

### 3.1 中断管理组件

```tsx
// frontend/components/interrupt-manager.tsx

interface InterruptHandlerProps {
  taskId: string;
  interruptReason: string;
  interruptData: any;
  onResume: (decision: string, data?: any) => void;
  onAbort: () => void;
}

export function InterruptManager({
  taskId,
  interruptReason,
  interruptData,
  onResume,
  onAbort
}: InterruptHandlerProps) {
  // 根据中断原因渲染对应的组件
  switch (interruptReason) {
    case "data_mapping_required":
      return <DataMappingInterrupt {...props} />;  // 新增
    case "novelty_result_ready":
      return <NoveltyInterrupt {...props} />;
    case "low_evidence_quality":
      return <BridgeInterrupt {...props} />;
    case "brief_ready_for_review":
      return <BriefInterrupt {...props} />;
    case "draft_ready":
      return <WritingInterrupt {...props} />;
    default:
      return <GenericInterrupt {...props} />;
  }
}
```

### 3.2 各中断组件

#### NoveltyInterrupt

```tsx
// frontend/components/novelty-interrupt.tsx

export function NoveltyInterrupt({ interruptData, onResume, onAbort }) {
  const [selectedDirection, setSelectedDirection] = useState<string | null>(null);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h3 className="font-bold text-blue-800 mb-2">选题创新性评估</h3>

      <div className="mb-4">
        <p className="text-sm">创新性评分：{interruptData.noveltyScore}/1.0</p>
      </div>

      {interruptData.overlapWithExisting?.length > 0 && (
        <div className="mb-3">
          <p className="font-semibold text-red-700 text-sm">与已有工作重复：</p>
          <ul className="list-disc pl-5 text-sm">
            {interruptData.overlapWithExisting.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {interruptData.suggestedTopicDirections?.length > 0 && (
        <div className="mb-3">
          <p className="font-semibold text-sm">推荐研究方向：</p>
          {interruptData.suggestedTopicDirections.map((dir, i) => (
            <label key={i} className="flex items-center gap-2">
              <input
                type="radio"
                name="direction"
                checked={selectedDirection === dir}
                onChange={() => setSelectedDirection(dir)}
              />
              {dir}
            </label>
          ))}
        </div>
      )}

      <div className="flex gap-3 mt-4">
        <button
          onClick={() => onResume("approved", { accepted_direction: selectedDirection })}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          确认选题方向
        </button>
        <button
          onClick={() => onResume("modified", { custom_direction: "用户修改的方向" })}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          修改研究方向
        </button>
        <button onClick={onAbort} className="px-4 py-2 bg-gray-300 rounded">
          终止任务
        </button>
      </div>
    </div>
  );
}
```

#### BriefInterrupt

```tsx
// frontend/components/brief-interrupt.tsx

export function BriefInterrupt({ interruptData, onResume, onAbort }) {
  const [editingBrief, setEditingBrief] = useState(interruptData.brief);

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <h3 className="font-bold text-yellow-800 mb-2">Research Brief 已生成</h3>

      {interruptData.warnings?.length > 0 && (
        <div className="mb-3 p-2 bg-yellow-100 rounded">
          <p className="text-sm text-yellow-700">{interruptData.warnings.join(", ")}</p>
        </div>
      )}

      <BriefEditor
        brief={editingBrief}
        onChange={setEditingBrief}
        readOnlyFields={["task_id", "created_at"]}
      />

      <div className="flex gap-3 mt-4">
        <button
          onClick={() => onResume("approved")}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          确认 Brief
        </button>
        <button
          onClick={() => onResume("modified", { edited_brief: editingBrief })}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          保存修改
        </button>
        <button onClick={onAbort} className="px-4 py-2 bg-gray-300 rounded">
          取消
        </button>
      </div>
    </div>
  );
}
```

#### DataMappingInterrupt（新增，2026-04-04）

```tsx
// frontend/components/data-mapping-interrupt.tsx

export function DataMappingInterrupt({ interruptData, onResume, onAbort }) {
  const [mapping, setMapping] = useState({
    dependent_var: interruptData.recommended_mapping?.dependent_var || "",
    independent_vars: interruptData.recommended_mapping?.independent_vars || [],
    control_vars: interruptData.recommended_mapping?.control_vars || [],
    entity_column: interruptData.recommended_mapping?.entity_column || "",
    time_column: interruptData.recommended_mapping?.time_column || ""
  });

  const columns = interruptData.detected_columns || [];

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h3 className="font-bold text-blue-800 mb-2">请确认数据变量映射</h3>
      <p className="text-sm text-gray-600 mb-4">
        文件：{interruptData.file_name} | 检测到 {columns.length} 列
      </p>

      {/* 因变量 */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">因变量 (Y)</label>
        <select
          value={mapping.dependent_var}
          onChange={(e) => setMapping({ ...mapping, dependent_var: e.target.value })}
          className="w-full p-2 border rounded"
        >
          <option value="">-- 请选择 --</option>
          {columns.map(col => <option key={col} value={col}>{col}</option>)}
        </select>
      </div>

      {/* 自变量 */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">自变量 (X)</label>
        <MultiSelect
          options={columns.filter(c => c !== mapping.dependent_var)}
          selected={mapping.independent_vars}
          onChange={(vals) => setMapping({ ...mapping, independent_vars: vals })}
          placeholder="选择自变量（可多选）"
        />
      </div>

      {/* 控制变量 */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">控制变量</label>
        <MultiSelect
          options={columns.filter(c => c !== mapping.dependent_var && !mapping.independent_vars.includes(c))}
          selected={mapping.control_vars}
          onChange={(vals) => setMapping({ ...mapping, control_vars: vals })}
          placeholder="选择控制变量（可多选）"
        />
      </div>

      {/* 面板数据专用 */}
      {interruptData.detected_panel_structure?.is_panel && (
        <>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">地区/个体列</label>
            <select
              value={mapping.entity_column}
              onChange={(e) => setMapping({ ...mapping, entity_column: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">-- 请选择 --</option>
              {columns.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">时间列</label>
            <select
              value={mapping.time_column}
              onChange={(e) => setMapping({ ...mapping, time_column: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">-- 请选择 --</option>
              {columns.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </div>
        </>
      )}

      <div className="flex gap-3 mt-4">
        <button
          onClick={() => onResume("approved", { variable_mapping: mapping })}
          className="px-4 py-2 bg-green-600 text-white rounded"
          disabled={!mapping.dependent_var}
        >
          确认映射
        </button>
        <button
          onClick={() => onResume("modified", { variable_mapping: mapping })}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          修改映射
        </button>
        <button onClick={onAbort} className="px-4 py-2 bg-gray-300 rounded">
          取消上传
        </button>
      </div>
    </div>
  );
}
```

---

## 四、LLM 配置持久化设计（扩展，2026-04-04）

### 4.1 配置文件位置

LLM 配置存储在 `~/.research_assistant/llm_config.json`，用户首次配置后持久化保存。

### 4.2 LLM 配置模型

```python
# backend/core/llm_config.py

from pydantic import BaseModel
from typing import Optional, List
import json
import os

class LLMProviderConfig(BaseModel):
    """单个 Provider 的配置"""
    name: str
    default_model: str
    available_models: List[str]
    api_style: str  # "openai" | "google" | "custom"

class LLMConfig(BaseModel):
    """LLM 全局配置（一次配置，持久化）"""
    current_provider: str = "groq"
    current_model: str = "llama-3.3-70b-versatile"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # 支持的 Providers（扩展，2026-04-04）
    providers: dict = {
        # OpenAI 兼容格式
        "openai": LLMProviderConfig(
            name="OpenAI",
            default_model="gpt-4o",
            available_models=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            api_style="openai"
        ),
        "groq": LLMProviderConfig(
            name="Groq",
            default_model="llama-3.3-70b-versatile",
            available_models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"],
            api_style="openai"
        ),
        "deepseek": LLMProviderConfig(
            name="DeepSeek",
            default_model="deepseek-chat",
            available_models=["deepseek-chat", "deepseek-coder"],
            api_style="openai"
        ),
        "kimi": LLMProviderConfig(
            name="Kimi (Moonshot)",
            default_model="moonshot-v1-8k",
            available_models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            api_style="openai"
        ),
        "minimax": LLMProviderConfig(
            name="Minimax",
            default_model="abab6-chat",
            available_models=["abab6-chat", "abab5.5-chat"],
            api_style="openai"
        ),
        "zhipu": LLMProviderConfig(
            name="智谱 (Zhipu)",
            default_model="glm-4",
            available_models=["glm-4", "glm-4-flash", "glm-3-turbo"],
            api_style="openai"
        ),
        "baichuan": LLMProviderConfig(
            name="百川 (Baichuan)",
            default_model="baichuan4",
            available_models=["baichuan4", "baichuan3-turbo"],
            api_style="openai"
        ),
        "qianfan": LLMProviderConfig(
            name="百度千帆 (Qianfan)",
            default_model="ernie-4.0-8k",
            available_models=["ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-128k"],
            api_style="custom"
        ),
        "local": LLMProviderConfig(
            name="Local (Ollama)",
            default_model="llama3",
            available_models=["llama3", "llama3.1", "mistral", "codellama", "qwen2.5"],
            api_style="openai"
        ),
        # Google 格式
        "gemini": LLMProviderConfig(
            name="Google Gemini",
            default_model="gemini-1.5-flash",
            available_models=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
            api_style="google"
        ),
        # Anthropic
        "anthropic": LLMProviderConfig(
            name="Anthropic",
            default_model="claude-sonnet-4-20250514",
            available_models=["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
            api_style="anthropic"
        ),
    }

    @classmethod
    def load(cls) -> "LLMConfig":
        """从配置文件加载"""
        config_path = os.path.expanduser("~/.research_assistant/llm_config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return cls(**json.load(f))
        return cls()  # 返回默认配置（Groq）

    def save(self):
        """保存到配置文件"""
        config_path = os.path.expanduser("~/.research_assistant/llm_config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump({
                "current_provider": self.current_provider,
                "current_model": self.current_model,
                "api_key": self.api_key,
                "base_url": self.base_url
            }, f, indent=2)

    def get_llm(self):
        """获取配置好的 LLM 实例"""
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic

        p = self.current_provider

        if p == "openai":
            return ChatOpenAI(model=self.current_model, api_key=self.api_key)

        elif p == "groq":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key
            )

        elif p == "deepseek":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://api.deepseek.com",
                api_key=self.api_key
            )

        elif p == "kimi":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://api.moonshot.cn/v1",
                api_key=self.api_key
            )

        elif p == "minimax":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://api.minimax.chat/v1",
                api_key=self.api_key
            )

        elif p == "zhipu":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://open.bigmodel.cn/api/paas/v4",
                api_key=self.api_key
            )

        elif p == "baichuan":
            return ChatOpenAI(
                model=self.current_model,
                base_url="https://api.baichuan-ai.com/v1",
                api_key=self.api_key
            )

        elif p == "qianfan":
            import os
            os.environ["BAIDU_QIANFAN_AK"] = self.api_key
            from langchain_community.llms import QianfanLLMEndpoint
            return QianfanLLMEndpoint(model=self.current_model)

        elif p == "local":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=self.current_model,
                base_url=self.base_url or "http://localhost:11434"
            )

        elif p == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=self.current_model)

        elif p == "anthropic":
            return ChatAnthropic(model=self.current_model, api_key=self.api_key)
```

### 4.3 API 路由

```python
# backend/api/routes_llm.py

@router.get("/config/llm")
async def get_llm_config():
    """获取当前 LLM 配置（不返回 api_key）"""
    config = LLMConfig.load()
    return {
        "current_provider": config.current_provider,
        "current_model": config.current_model,
        "providers": config.providers,
        "has_api_key": bool(config.api_key)
    }

@router.post("/config/llm")
async def update_llm_config(req: LLMConfigUpdateRequest):
    """更新 LLM 配置"""
    config = LLMConfig.load()
    config.current_provider = req.provider
    config.current_model = req.model
    if req.api_key:
        config.api_key = req.api_key
    if req.base_url:
        config.base_url = req.base_url
    config.save()
    return {"status": "ok", "message": "LLM 配置已保存"}
```

### 4.4 前端配置 UI

```tsx
// frontend/components/llm-config.tsx

export function LLMConfigPanel() {
  const [config, setConfig] = useState({ provider: "groq", model: "", hasApiKey: false });

  useEffect(() => {
    fetch("/api/config/llm").then(r => r.json()).then(setConfig);
  }, []);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="font-bold mb-4">LLM 配置</h3>

      <div className="mb-4">
        <label className="block text-sm mb-1">Provider</label>
        <select
          value={config.current_provider}
          onChange={(e) => setConfig({ ...config, provider: e.target.value })}
          className="w-full p-2 border rounded"
        >
          {Object.entries(config.providers).map(([key, val]) => (
            <option key={key} value={key}>{val.name}</option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-sm mb-1">模型</label>
        <select
          value={config.current_model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
          className="w-full p-2 border rounded"
        >
          {config.providers[config.current_provider]?.available_models.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-sm mb-1">API Key</label>
        <input
          type="password"
          placeholder={config.hasApiKey ? "已配置（不显示）" : "输入 API Key"}
          className="w-full p-2 border rounded"
        />
      </div>

      <button className="px-4 py-2 bg-green-600 text-white rounded">
        保存配置
      </button>
    </div>
  );
}
```

---

## 五、MCP 集成设计（新增，2026-04-04）

### 5.1 MCP 定位

MCP (Model Context Protocol) 允许系统连接外部工具服务，丰富 Agent 的能力范围。

### 5.2 MCP Port 配置

```python
# backend/core/mcp_config.py

from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import os

class MCPPortConfig(BaseModel):
    """单个 MCP Port 的配置"""
    port_id: str  # 唯一标识，如 "academic_search"
    name: str  # 显示名称
    description: str  # 说明
    enabled: bool = True
    url: str  # MCP 服务地址
    auth_token: Optional[str] = None  # 认证 token
    timeout: int = 30  # 超时秒数
    capabilities: List[str] = []  # ["search", "compute", "render", "api"]


class MCPConfig(BaseModel):
    """MCP 全局配置"""
    ports: Dict[str, MCPPortConfig] = {}

    @classmethod
    def load(cls) -> "MCPConfig":
        config_path = os.path.expanduser("~/.research_assistant/mcp_config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return cls(**json.load(f))
        return cls()

    def save(self):
        config_path = os.path.expanduser("~/.research_assistant/mcp_config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)

    def add_port(self, port: MCPPortConfig):
        self.ports[port.port_id] = port

    def get_port(self, port_id: str) -> Optional[MCPPortConfig]:
        return self.ports.get(port_id)

    def list_enabled_ports(self) -> List[MCPPortConfig]:
        return [p for p in self.ports.values() if p.enabled]
```

### 5.3 内置 MCP Ports（预设）

| Port ID | 名称 | 功能 | URL 示例 |
|---------|------|------|----------|
| `academic_search` | 学术数据库搜索 | 扩展文献检索能力 | `http://localhost:8001` |
| `wolfram` | Wolfram 计算 | 数学公式计算、符号运算 | `http://localhost:8002` |
| `chart_render` | 图表渲染服务 | 高级图表渲染 | `http://localhost:8003` |
| `data_clean` | 数据清洗服务 | 专业数据清洗 | `http://localhost:8004` |
| `translate` | 翻译服务 | 中英文翻译 | `http://localhost:8005` |
| `custom_api` | 自定义 API | 用户自定义第三方 API | `http://localhost:8006` |

### 5.4 MCP Client 实现

```python
# backend/core/mcp_client.py

import aiohttp
import json
from typing import Any, Dict, Optional

class MCPClient:
    """MCP 客户端"""

    def __init__(self, config: MCPPortConfig):
        self.config = config
        self.base_url = config.url
        self.timeout = aiohttp.ClientTimeout(total=config.timeout)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """调用 MCP 工具"""
        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/mcp",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"MCP call failed: {resp.status}")
                result = await resp.json()
                return result.get("result", {})

    async def list_tools(self) -> List[Dict]:
        """列出可用工具"""
        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/mcp",
                headers=headers,
                json=payload
            ) as resp:
                result = await resp.json()
                return result.get("result", {}).get("tools", [])


class MCPManager:
    """MCP Port 管理器"""

    def __init__(self):
        self.config = MCPConfig.load()
        self._clients: Dict[str, MCPClient] = {}

    def get_client(self, port_id: str) -> Optional[MCPClient]:
        if port_id not in self._clients:
            port = self.config.get_port(port_id)
            if not port or not port.enabled:
                return None
            self._clients[port_id] = MCPClient(port)
        return self._clients[port_id]

    async def call_tool(self, port_id: str, tool_name: str, arguments: Dict) -> Dict:
        client = self.get_client(port_id)
        if not client:
            raise Exception(f"MCP port {port_id} not found or disabled")
        return await client.call_tool(tool_name, arguments)

    def add_mcp_port(self, port: MCPPortConfig):
        self.config.add_port(port)
        self.config.save()
        # 清除缓存，强制重新创建 client
        if port.port_id in self._clients:
            del self._clients[port.port_id]
```

### 5.5 API 路由

```python
# backend/api/routes_mcp.py

@router.get("/config/mcp")
async def list_mcp_ports():
    """列出所有 MCP Ports"""
    manager = MCPManager()
    ports = manager.config.list_enabled_ports()
    return {
        "ports": [
            {
                "port_id": p.port_id,
                "name": p.name,
                "description": p.description,
                "enabled": p.enabled,
                "capabilities": p.capabilities
            }
            for p in ports
        ]
    }

@router.post("/config/mcp/ports")
async def add_mcp_port(req: MCPPortConfig):
    """添加 MCP Port"""
    manager = MCPManager()
    manager.add_mcp_port(req)
    return {"status": "ok", "port_id": req.port_id}

@router.delete("/config/mcp/ports/{port_id}")
async def remove_mcp_port(port_id: str):
    """移除 MCP Port"""
    manager = MCPManager()
    if port_id in manager.config.ports:
        del manager.config.ports[port_id]
        manager.config.save()
    return {"status": "ok"}

@router.post("/mcp/{port_id}/call")
async def call_mcp_tool(port_id: str, req: MCPToolCallRequest):
    """调用 MCP Port 工具"""
    manager = MCPManager()
    result = await manager.call_tool(port_id, req.tool_name, req.arguments)
    return result
```

### 5.6 前端 MCP 管理 UI

```tsx
// frontend/components/mcp-port-manager.tsx

export function MCPPortManager() {
  const [ports, setPorts] = useState([]);

  useEffect(() => {
    fetch("/api/config/mcp").then(r => r.json()).then(d => setPorts(d.ports));
  }, []);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="font-bold mb-4">MCP Ports 管理</h3>

      <div className="space-y-4">
        {ports.map(port => (
          <div key={port.port_id} className="border rounded p-3">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-medium">{port.name}</h4>
                <p className="text-sm text-gray-500">{port.description}</p>
                <div className="flex gap-1 mt-1">
                  {port.capabilities.map(c => (
                    <span key={c} className="text-xs bg-gray-100 px-2 py-0.5 rounded">{c}</span>
                  ))}
                </div>
              </div>
              <label className="flex items-center">
                <input type="checkbox" checked={port.enabled} className="mr-2" />
                启用
              </label>
            </div>
          </div>
        ))}
      </div>

      <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">
        添加自定义 Port
      </button>
    </div>
  );
}
```

### 5.7 在 Agent 中使用 MCP

```python
# 在 Literature Node 中使用 academic_search MCP Port

async def search_with_mcp(query: str, top_k: int = 10):
    """使用 MCP 学术搜索端口"""
    try:
        manager = MCPManager()
        result = await manager.call_tool(
            port_id="academic_search",
            tool_name="search",
            arguments={"query": query, "top_k": top_k}
        )
        return result.get("results", [])
    except Exception as e:
        # MCP 不可用时降级到本地检索
        logger.warning(f"MCP academic_search unavailable: {e}")
        return []
```

---

## 六、SSE 状态推送设计

### 4.1 SSE 端点

```python
# backend/api/routes.py

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.get("/tasks/{task_id}/stream")
async def stream_task_status(task_id: str, request: Request):
    """
    SSE 流式推送任务状态变更
    """
    async def event_generator():
        # 获取 Redis pubsub
        redis = get_redis()
        pubsub = redis.pubsub()
        channel = f"task:{task_id}:events"

        await pubsub.subscribe(channel)

        try:
            # 发送初始状态
            task = get_task(task_id)
            yield f"event: status\ndata: {json.dumps(task)}\n\n"

            # 监听状态变更
            while True:
                # 检查客户端断开
                if await request.is_disconnected():
                    break

                # 等待 Redis 消息
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = json.loads(message["data"])
                    yield f"event: {data.get('event_type', 'update')}\ndata: {json.dumps(data)}\n\n"

                await asyncio.sleep(0.1)

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )
```

### 4.2 状态变更事件发布

```python
# backend/core/task_events.py

def publish_task_event(task_id: str, event_type: str, data: dict):
    """
    发布任务状态变更事件
    """
    redis = get_redis()
    channel = f"task:{task_id}:events"

    event = {
        "event_type": event_type,
        "task_id": task_id,
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }

    redis.publish(channel, json.dumps(event))
```

```python
# 在各节点中调用

# Novelty Node 完成创新性评估
publish_task_event(task_id, "node_completed", {
    "node": "novelty",
    "status": "interrupted",
    "interrupt_reason": "novelty_result_ready",
    "interrupt_data": {...}
})

# Brief Builder 完成
publish_task_event(task_id, "node_completed", {
    "node": "brief",
    "status": "interrupted",
    "interrupt_reason": "brief_ready_for_review",
    "interrupt_data": {...}
})
```

### 4.3 前端 SSE 订阅

```tsx
// frontend/hooks/useTaskStream.ts

import { useEffect, useRef, useState } from "react";

export function useTaskStream(taskId: string) {
  const [taskStatus, setTaskStatus] = useState<any>(null);
  const [interrupt, setInterrupt] = useState<any>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      setTaskStatus(data);

      if (data.status === "interrupted") {
        setInterrupt({
          reason: data.interrupt_reason,
          data: data.interrupt_data
        });
      }
    });

    eventSource.addEventListener("node_completed", (e) => {
      const data = JSON.parse(e.data);
      console.log(`Node ${data.node} completed`);
    });

    eventSource.addEventListener("error", (e) => {
      console.error("SSE error:", e);
    });

    return () => {
      eventSource.close();
    };
  }, [taskId]);

  const resumeTask = async (decision: string, data?: any) => {
    await fetch(`/api/tasks/${taskId}/continue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, data })
    });
    setInterrupt(null);
  };

  return { taskStatus, interrupt, resumeTask };
}
```

### 4.4 使用示例

```tsx
// frontend/components/task-workspace.tsx

export function TaskWorkspace({ taskId }: { taskId: string }) {
  const { taskStatus, interrupt, resumeTask } = useTaskStream(taskId);

  if (!taskStatus) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      {/* 任务状态展示 */}
      <TaskStatusBar
        status={taskStatus.status}
        currentNode={taskStatus.current_node}
      />

      {/* 中断处理 */}
      {interrupt && (
        <InterruptManager
          taskId={taskId}
          interruptReason={interrupt.reason}
          interruptData={interrupt.data}
          onResume={resumeTask}
          onAbort={() => resumeTask("rejected")}
        />
      )}

      {/* 结果展示 */}
      {taskStatus.status === "done" && (
        <TaskResult data={taskStatus.result} />
      )}
    </div>
  );
}
```

---

## 五、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/api/routes.py` | 中断处理 API |
| `backend/api/sse.py` | SSE 端点 |
| `backend/core/task_events.py` | 事件发布工具 |
| `backend/agents/orchestrator/main_graph.py` | 主图（含中断配置） |
| `frontend/components/interrupt-manager.tsx` | 中断管理器 |
| `frontend/components/novelty-interrupt.tsx` | Novelty 中断 UI |
| `frontend/components/brief-interrupt.tsx` | Brief 中断 UI |
| `frontend/hooks/useTaskStream.ts` | SSE 订阅 Hook |

---

## 六、实施检查清单

### Brief Builder
- [ ] BriefBuilderState 状态定义
- [ ] collect_inputs 节点
- [ ] assemble_brief 节点
- [ ] validate_brief 节点
- [ ] save_version 节点
- [ ] Brief 中断 UI

### 中断集成
- [ ] ContinueTaskRequest API
- [ ] 主图中断配置
- [ ] InterruptManager 组件
- [ ] 各节点中断数据格式

### SSE 推送
- [ ] SSE 端点实现
- [ ] Redis pubsub 集成
- [ ] task_events 工具
- [ ] useTaskStream Hook
- [ ] 前端集成测试

---

## 七、整体流程图（调整后，2026-04-04）

```
用户上传数据 + 提出研究问题
       │
       ▼
POST /tasks ──▶ Task ID
       │
       ▼
┌─────────────────────────┐
│ 数据解析 + 自动检测列名   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ [中断0：数据映射确认]   │  ← 用户选择因变量/自变量/控制变量/地区列/年份列
│ 数据映射 UI             │
└────────────┬────────────┘
             │
             ▼
      Literature Node
             │
             ▼
      Novelty Node ◀─────────────── [Novelty 中断：迁移评估确认]
             │                           │
             │  用户确认迁移方向后         │
             ▼                           ▼
      Analysis Node ──────────▶ [Bridge 中断] ──▶ Brief Builder
                                                           │
                                                           ▼
                                              [Brief 中断] ──▶ Writing
                                                                           │
                                                                           ▼
                                                            [Writing 中断] ──▶ 完成

SSE 实时推送：
  /tasks/{id}/stream ──▶ 状态变更 ──▶ 前端更新
```

**调整说明（2026-04-04）**：
- 新增**中断点0：数据映射确认**——用户上传数据后先选择变量映射，再进入 Literature
- Literature Node 在 Novelty 之前运行，提供 method_metadata
- Novelty 中断的内涵扩展为迁移/组合/调整评估确认
- LLM 配置持久化到 `~/.research_assistant/llm_config.json`
