# Phase 1：Research_Brief Schema 设计文档

> **版本**：v0.1
> **日期**：2026-04-02
> **前置文档**：
> - `Phase0-最小可运行骨架-实施计划.md`
> - `Phase1-Text-to-Code-Bridge-设计文档.md`
> - `Phase1-Literature-Node-设计文档.md`

---

## 一、定位与作用

### 1.1 Research_Brief 是系统的数据契约

```
所有节点输出 ──▶ Research_Brief ──▶ Writing Node
                    │
                    ├── 唯一数据来源
                    ├── 经过清洗和聚合
                    └── 支持人工编辑
```

**核心原则**：`No raw logs into writer`
- Writing Node 只接收 Research_Brief
- 不接收原始检索日志、代码错误、杂质上下文

### 1.2 数据流向

```
Novelty Node ──┐
               │
Literature ────┼──▶ Brief Builder ──▶ Research_Brief ──▶ Writing Node
               │        │
Analysis ──────┘        │
                       ├── 汇总所有节点输出
                       ├── 清洗和聚合
                       └── 支持人工审核
```

---

## 二、关键设计决策（已确认）

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 版本管理 | Redis 存储版本 | 原子操作，适合并发 |
| 编辑粒度 | 字段级编辑 | 安全，不破坏 Schema |
| 验证机制 | Pydantic Schema 验证 | 确保数据类型正确 |
| Audit Trail | 节点+人工操作+变更 | 完整可追溯 |

---

## 三、Schema 设计

### 3.1 主 Schema

```python
# backend/agents/models/research_brief.py

from typing import TypedDict, Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    TOPIC_NOVELTY_CHECK = "topic_novelty_check"
    MODEL_RECOMMENDATION = "model_recommendation"
    ANALYSIS = "analysis"
    WRITING = "writing"

class ResearchBrief(BaseModel):
    """Research_Brief 主 Schema"""

    # ===== 标识 =====
    version: str = "1.0.0"
    brief_id: str  # 格式: brief_{task_id}_{timestamp}

    # ===== 任务信息 =====
    task_type: TaskType
    task_id: str
    research_goal: str = Field(description="用户的研究目标/问题")

    # ===== 选题创新性 =====
    novelty_position: Optional[NoveltyPosition] = Field(
        default=None,
        description="选题查重结果"
    )

    # ===== 数据摘要 =====
    data_summary: Optional[DataSummary] = Field(
        default=None,
        description="数据文件摘要"
    )

    # ===== 方法决策 =====
    method_decision: Optional[MethodDecision] = Field(
        default=None,
        description="模型和方法选择"
    )

    # ===== 分析输出 =====
    analysis_outputs: Optional[AnalysisOutputs] = Field(
        default=None,
        description="代码执行结果和图表"
    )

    # ===== 证据映射 =====
    evidence_map: Optional[EvidenceMap] = Field(
        default=None,
        description="论断与证据的绑定关系"
    )

    # ===== 草稿章节 =====
    draft_sections: Optional[DraftSections] = Field(
        default=None,
        description="论文各部分草稿"
    )

    # ===== 局限性 =====
    limitations: Optional[List[str]] = Field(
        default_factory=list,
        description="研究的局限性"
    )

    # ===== 未来工作 =====
    future_work: Optional[List[str]] = Field(
        default_factory=list,
        description="未来研究方向"
    )

    # ===== 审计追踪 =====
    audit_trail: List[AuditEntry] = Field(
        default_factory=list,
        description="操作审计链"
    )

    # ===== 元数据 =====
    created_at: str
    updated_at: str
    created_by: str = "system"  # "system" | "user"
    status: str = "draft"  # "draft" | "review" | "final"

    @field_validator('updated_at', 'created_at')
    @classmethod
    def validate_timestamp(cls, v):
        if isinstance(v, str):
            # 验证 ISO 格式
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
```

### 3.2 子 Schema

```python
# ===== NoveltyPosition =====

class NoveltyPosition(BaseModel):
    """选题创新性"""

    overlap_with_existing: List[str] = Field(
        default_factory=list,
        description="与已有工作的重复点"
    )
    differentiation_points: List[str] = Field(
        default_factory=list,
        description="可区分点/创新点"
    )
    suggested_topic_directions: List[str] = Field(
        default_factory=list,
        description="推荐的题目方向"
    )
    novelty_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="创新性评分"
    )
    human_approved: bool = Field(
        default=False,
        description="是否经过人工确认"
    )


# ===== DataSummary =====

class DataSummary(BaseModel):
    """数据摘要"""

    files: List[DataFile] = Field(
        default_factory=list,
        description="数据文件列表"
    )
    total_rows: int = Field(default=0, ge=0)
    total_columns: int = Field(default=0, ge=0)
    column_types: dict = Field(
        default_factory=dict,
        description="列名到类型的映射"
    )
    panel_structure: Optional[PanelStructure] = Field(
        default=None,
        description="面板数据结构"
    )
    diagnostic_notes: str = Field(
        default="",
        description="数据诊断备注"
    )
    missing_values: dict = Field(
        default_factory=dict,
        description="各列缺失值统计"
    )
    outliers: List[str] = Field(
        default_factory=list,
        description="异常值列"
    )


class DataFile(BaseModel):
    """数据文件"""

    file_id: str
    file_name: str
    file_type: str  # "xlsx" | "csv" | "xls"
    file_path: str
    size_bytes: int


class PanelStructure(BaseModel):
    """面板数据结构"""

    is_panel: bool = Field(default=False)
    entity_column: str = Field(default="", description="个体标识列")
    time_column: str = Field(default="", description="时间列")
    time_range: tuple = Field(default=(None, None), description="时间范围")
    entity_count: int = Field(default=0, description="个体数量")
    time_periods: int = Field(default=0, description="时间期数")


# ===== MethodDecision =====

class MethodDecision(BaseModel):
    """方法决策"""

    recommended_models: List[str] = Field(
        default_factory=list,
        description="推荐的模型"
    )
    rejected_models: List[str] = Field(
        default_factory=list,
        description="不推荐的模型及原因"
    )
    reasoning: str = Field(default="", description="推荐理由")
    evidence_sources: List[str] = Field(
        default_factory=list,
        description="证据来源 chunk_id"
    )
    model_parameters: dict = Field(
        default_factory=dict,
        description="模型参数建议"
    )
    robustness_checks: List[str] = Field(
        default_factory=list,
        description="稳健性检验建议"
    )


# ===== AnalysisOutputs =====

class AnalysisOutputs(BaseModel):
    """分析输出"""

    code_script: str = Field(default="", description="执行的代码")
    execution_status: str = Field(
        default="pending",
        description="pending | running | success | failed"
    )
    execution_result: Optional[dict] = Field(
        default=None,
        description="执行结果"
    )
    charts: List[ChartOutput] = Field(
        default_factory=list,
        description="生成的图表"
    )
    tables: List[TableOutput] = Field(
        default_factory=list,
        description="生成的结果表"
    )
    numerical_results: dict = Field(
        default_factory=dict,
        description="关键数值结果"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="错误信息"
    )


class ChartOutput(BaseModel):
    """图表输出"""

    chart_id: str
    chart_type: str  # "line" | "bar" | "scatter" | "heatmap"
    title: str
    file_path: str
    description: str = ""


class TableOutput(BaseModel):
    """表输出"""

    table_id: str
    table_name: str
    file_path: str
    row_count: int
    column_count: int
    description: str = ""


# ===== EvidenceMap =====

class EvidenceMap(BaseModel):
    """证据映射"""

    claims: List[Claim] = Field(
        default_factory=list,
        description="论断列表"
    )


class Claim(BaseModel):
    """单个论断"""

    claim_id: str
    claim_text: str = Field(description="论断内容")
    source_chunk_ids: List[str] = Field(
        default_factory=list,
        description="来源证据 chunk_id"
    )
    source_files: List[str] = Field(
        default_factory=list,
        description="来源文件"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="论断置信度"
    )
    is_verified: bool = Field(
        default=False,
        description="是否经验证"
    )


# ===== DraftSections =====

class DraftSections(BaseModel):
    """草稿章节"""

    title: str = Field(default="", description="论文标题候选")
    outline: str = Field(default="", description="论文提纲")
    abstract: str = Field(default="", description="摘要草稿")
    introduction: str = Field(
        default="",
        description="引言草稿"
    )
    methods: str = Field(default="", description="方法部分草稿")
    results: str = Field(default="", description="结果部分草稿")
    discussion: str = Field(
        default="",
        description="讨论部分草稿"
    )
    references: str = Field(default="", description="参考文献列表")
    appendices: str = Field(default="", description="附录")


# ===== AuditTrail =====

class AuditEntry(BaseModel):
    """审计条目"""

    entry_id: str
    timestamp: str
    node: str  # "novelty" | "literature" | "analysis" | "brief" | "writing"
    action: str  # "node_output" | "human_edit" | "human_approve" | "human_reject"
    user_id: Optional[str] = None  # "system" 或用户ID

    # 变更详情
    field_path: Optional[str] = Field(
        default=None,
        description="变更字段路径，如 'novelty_position.suggested_topic_directions'"
    )
    old_value: Optional[str] = Field(
        default=None,
        description="变更前的值"
    )
    new_value: Optional[str] = Field(
        default=None,
        description="变更后的值"
    )

    # 节点输出摘要
    node_output_summary: Optional[str] = Field(
        default=None,
        description="节点输出摘要"
    )

    # 人工操作详情
    human_action: Optional[str] = Field(
        default=None,
        description="人工操作类型"
    )
    human_notes: Optional[str] = Field(
        default=None,
        description="人工备注"
    )
```

---

## 四、版本管理设计

### 4.1 Redis 存储结构

```
# Redis Key Structure

brief:{brief_id}:current          # 当前版本
brief:{brief_id}:versions        # 版本列表 (Redis List)
brief:{brief_id}:meta            # 元数据 (hash)
brief:{brief_id}:lock            # 分布式锁

# 版本内容
brief:{brief_id}:v:{version}     # 各版本内容 (hash)
```

### 4.2 版本操作

```python
# backend/core/brief_version.py

class BriefVersionManager:
    """Research_Brief 版本管理器"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "brief"

    def save_version(self, brief: ResearchBrief) -> str:
        """
        保存新版本
        返回版本号
        """
        brief_id = brief.brief_id
        version = datetime.utcnow().isoformat()

        # 序列化
        brief_json = brief.model_dump_json()

        # 存储版本内容
        version_key = f"{self.prefix}:{brief_id}:v:{version}"
        self.redis.set(version_key, brief_json)

        # 更新版本列表
        versions_key = f"{self.prefix}:{brief_id}:versions"
        self.redis.rpush(versions_key, version)

        # 更新当前版本
        current_key = f"{self.prefix}:{brief_id}:current"
        self.redis.set(current_key, version)

        # 限制版本数量（保留最近 50 个）
        self._prune_versions(brief_id, keep=50)

        return version

    def get_version(self, brief_id: str, version: str) -> ResearchBrief:
        """获取指定版本"""
        version_key = f"{self.prefix}:{brief_id}:v:{version}"
        data = self.redis.get(version_key)
        return ResearchBrief.model_validate_json(data)

    def get_current(self, brief_id: str) -> ResearchBrief:
        """获取当前版本"""
        current_key = f"{self.prefix}:{brief_id}:current"
        version = self.redis.get(current_key)
        if not version:
            return None
        return self.get_version(brief_id, version)

    def get_history(self, brief_id: str, limit: int = 10) -> List[dict]:
        """获取版本历史"""
        versions_key = f"{self.prefix}:{brief_id}:versions"
        versions = self.redis.lrange(versions_key, -limit, -1)
        return [{"version": v} for v in reversed(versions)]

    def _prune_versions(self, brief_id: str, keep: int = 50):
        """清理旧版本"""
        versions_key = f"{self.prefix}:{brief_id}:versions"

        # 获取所有版本
        all_versions = self.redis.lrange(versions_key, 0, -1)

        if len(all_versions) <= keep:
            return

        # 删除旧版本
        to_delete = all_versions[:-keep]
        for v in to_delete:
            version_key = f"{self.prefix}:{brief_id}:v:{v}"
            self.redis.delete(version_key)

        # 更新列表
        self.redis.ltrim(versions_key, -keep, -1)
```

---

## 五、人工编辑机制

### 5.1 字段级编辑 API

```python
# backend/api/routes.py

class EditBriefFieldRequest(BaseModel):
    """编辑单个字段"""
    field_path: str  # 如 "novelty_position.suggested_topic_directions"
    value: Any  # 新值
    user_notes: str = ""  # 修改备注


@router.patch("/briefs/{brief_id}/fields")
async def edit_brief_field(
    brief_id: str,
    req: EditBriefFieldRequest
):
    """
    字段级编辑
    验证类型安全
    """
    # 1. 获取当前版本
    version_manager = BriefVersionManager(get_redis())
    brief = version_manager.get_current(brief_id)

    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    # 2. 验证字段路径
    if not is_valid_field_path(req.field_path):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field path: {req.field_path}"
        )

    # 3. 验证新值类型
    try:
        validated_value = validate_field_value(
            brief,
            req.field_path,
            req.value
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(e)}"
        )

    # 4. 创建审计条目
    old_value = get_field_by_path(brief, req.field_path)

    audit_entry = AuditEntry(
        entry_id=f"audit_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.utcnow().isoformat(),
        node="brief",
        action="human_edit",
        user_id="current_user",  # 从 auth 获取
        field_path=req.field_path,
        old_value=str(old_value),
        new_value=str(req.value),
        human_action="field_edit",
        human_notes=req.user_notes
    )

    # 5. 更新字段
    set_field_by_path(brief, req.field_path, validated_value)
    brief.audit_trail.append(audit_entry)
    brief.updated_at = datetime.utcnow().isoformat()

    # 6. 保存新版本
    new_version = version_manager.save_version(brief)

    return {
        "brief_id": brief_id,
        "version": new_version,
        "field_path": req.field_path,
        "audit_entry_id": audit_entry.entry_id
    }
```

### 5.2 字段验证函数

```python
# backend/core/brief_validation.py

def validate_field_value(
    brief: ResearchBrief,
    field_path: str,
    value: Any
) -> Any:
    """
    验证字段值类型
    """
    # 字段路径到类型的映射
    field_types = {
        "novelty_position.overlap_with_existing": list,
        "novelty_position.differentiation_points": list,
        "novelty_position.novelty_score": float,
        "novelty_position.human_approved": bool,
        "method_decision.recommended_models": list,
        "method_decision.rejected_models": list,
        "method_decision.reasoning": str,
        "draft_sections.title": str,
        "draft_sections.abstract": str,
        # ...
    }

    expected_type = field_types.get(field_path)

    if expected_type is None:
        raise ValueError(f"Unknown field path: {field_path}")

    if expected_type == list:
        if not isinstance(value, list):
            raise ValidationError(f"Expected list for {field_path}")
        return value

    if expected_type == float:
        if isinstance(value, str):
            value = float(value)
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Expected float for {field_path}")
        return float(value)

    if expected_type == bool:
        if isinstance(value, str):
            value = value.lower() in ("true", "1", "yes")
        return bool(value)

    # 默认类型检查
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Expected {expected_type.__name__} for {field_path}"
        )

    return value


def is_valid_field_path(path: str) -> bool:
    """验证字段路径是否合法"""
    valid_paths = {
        "novelty_position",
        "novelty_position.overlap_with_existing",
        "novelty_position.differentiation_points",
        "novelty_position.suggested_topic_directions",
        "novelty_position.novelty_score",
        "novelty_position.human_approved",
        "data_summary",
        "data_summary.diagnostic_notes",
        "method_decision",
        "method_decision.recommended_models",
        "method_decision.rejected_models",
        "method_decision.reasoning",
        "analysis_outputs",
        "analysis_outputs.code_script",
        "analysis_outputs.execution_status",
        "evidence_map",
        "draft_sections",
        "draft_sections.title",
        "draft_sections.outline",
        "draft_sections.abstract",
        "draft_sections.methods",
        "draft_sections.results",
        "limitations",
        "future_work",
        "audit_trail",  # 只读
    }

    return path in valid_paths
```

---

## 六、前端编辑组件

### 6.1 Brief 编辑器 UI

```typescript
// frontend/components/brief-editor.tsx

interface BriefEditorProps {
  brief: ResearchBrief;
  onSave: (updatedBrief: ResearchBrief) => void;
  readOnlyFields?: string[];
}

export function BriefEditor({ brief, onSave, readOnlyFields = [] }: BriefEditorProps) {
  return (
    <div className="space-y-6">
      {/* 选题创新性 */}
      <SectionCard title="选题创新性">
        <FieldArray
          field="novelty_position.differentiation_points"
          label="可区分点"
          items={brief.novelty_position?.differentiation_points || []}
          onChange={(items) => updateField(
            "novelty_position.differentiation_points",
            items
          )}
          readOnly={readOnlyFields.includes("novelty_position.differentiation_points")}
        />

        <FieldArray
          field="novelty_position.suggested_topic_directions"
          label="推荐题目方向"
          items={brief.novelty_position?.suggested_topic_directions || []}
          onChange={(items) => updateField(
            "novelty_position.suggested_topic_directions",
            items
          )}
          readOnly={readOnlyFields.includes("novelty_position.suggested_topic_directions")}
        />

        <div className="flex items-center gap-4 mt-4">
          <label className="text-sm text-gray-600">
            创新性评分: {brief.novelty_position?.novelty_score || 0}/1.0
          </label>
          {!readOnlyFields.includes("novelty_position.human_approved") && (
            <button
              onClick={() => updateField(
                "novelty_position.human_approved",
                true
              )}
              className="px-3 py-1 bg-green-100 text-green-800 rounded"
            >
              确认选题
            </button>
          )}
        </div>
      </SectionCard>

      {/* 方法决策 */}
      <SectionCard title="方法决策">
        <FieldArray
          field="method_decision.recommended_models"
          label="推荐模型"
          items={brief.method_decision?.recommended_models || []}
          onChange={(items) => updateField(
            "method_decision.recommended_models",
            items
          )}
          readOnly={readOnlyFields.includes("method_decision.recommended_models")}
        />

        <TextField
          field="method_decision.reasoning"
          label="推荐理由"
          value={brief.method_decision?.reasoning || ""}
          onChange={(value) => updateField(
            "method_decision.reasoning",
            value
          )}
          readOnly={readOnlyFields.includes("method_decision.reasoning")}
        />
      </SectionCard>

      {/* 草稿章节 */}
      <SectionCard title="论文草稿">
        <TextField
          field="draft_sections.title"
          label="标题"
          value={brief.draft_sections?.title || ""}
          onChange={(value) => updateField("draft_sections.title", value)}
        />

        <TextArea
          field="draft_sections.abstract"
          label="摘要"
          value={brief.draft_sections?.abstract || ""}
          onChange={(value) => updateField("draft_sections.abstract", value)}
          rows={4}
        />

        <TextArea
          field="draft_sections.methods"
          label="方法"
          value={brief.draft_sections?.methods || ""}
          onChange={(value) => updateField("draft_sections.methods", value)}
          rows={6}
        />

        {/* ... 其他字段 */}
      </SectionCard>

      {/* 审计历史 */}
      <SectionCard title="编辑历史">
        <AuditTrail entries={brief.audit_trail} />
      </SectionCard>
    </div>
  );
}

// 字段编辑函数
async function updateField(fieldPath: string, value: any) {
  const response = await fetch(`/api/briefs/${brief.brief_id}/fields`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      field_path: fieldPath,
      value,
      user_notes: ""
    })
  });

  if (response.ok) {
    const updated = await response.json();
    onSave(loadNewVersion(updated.version));
  }
}
```

---

## 七、Brief Builder 节点

### 7.1 Brief Builder 子图状态

```python
# backend/agents/orchestrator/subgraphs/brief_builder_state.py

class BriefBuilderState(TypedDict):
    task_id: str
    brief_id: str

    # 来源数据
    novelty_result: dict | None
    literature_result: dict | None
    analysis_result: dict | None
    writing_result: dict | None

    # 当前 Brief
    current_brief: dict | None

    # 编辑状态
    status: str  # "assembling" | "validating" | "interrupted" | "done"
    interrupt_reason: str | None
    interrupt_data: dict | None

    # 验证
    validation_errors: List[str]
    warnings: List[str]
```

### 7.2 Brief Builder 逻辑

```python
async def brief_builder_node(state: MainState) -> MainState:
    """
    Brief Builder 汇总所有节点输出
    构建 Research_Brief
    """
    from .brief_builder_state import BriefBuilderState
    from backend.agents.models.research_brief import ResearchBrief

    task_id = state["task_id"]

    # 1. 汇总各节点输出
    brief_data = {
        "brief_id": f"brief_{task_id}_{datetime.utcnow().isoformat()}",
        "task_id": task_id,
        "task_type": state.get("task_type"),
        "research_goal": state.get("user_query"),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # 2. 填充 Novelty Position
    if state.get("novelty_result"):
        brief_data["novelty_position"] = {
            "overlap_with_existing": state["novelty_result"].get("overlap", []),
            "differentiation_points": state["novelty_result"].get("differentiation", []),
            "suggested_topic_directions": state["novelty_result"].get("suggestions", []),
            "novelty_score": calculate_novelty_score(state["novelty_result"]),
            "human_approved": state.get("human_decision", {}).get("decision") == "approved"
        }

    # 3. 填充 Literature Result
    if state.get("literature_result"):
        brief_data["evidence_map"] = {
            "claims": build_claims_from_literature(state["literature_result"])
        }

        brief_data["method_decision"] = {
            "recommended_models": state["literature_result"].get("method_decision", {}).get("recommended_methods", []),
            "rejected_models": state["literature_result"].get("method_decision", {}).get("rejected_methods", []),
            "reasoning": state["literature_result"].get("method_decision", {}).get("reasoning", ""),
            "evidence_sources": [
                c["chunk_id"]
                for c in state["literature_result"].get("all_chunks", [])
            ]
        }

    # 4. 填充 Analysis Outputs
    if state.get("analysis_result"):
        brief_data["analysis_outputs"] = state["analysis_result"].get("execution_result", {})
        brief_data["data_summary"] = state["analysis_result"].get("data_summary", {})

    # 5. 填充 Draft Sections（如果有）
    if state.get("writing_result"):
        brief_data["draft_sections"] = state["writing_result"]

    # 6. 添加审计条目
    brief_data["audit_trail"] = [{
        "entry_id": f"audit_{uuid.uuid4().hex[:12]}",
        "timestamp": datetime.utcnow().isoformat(),
        "node": "brief",
        "action": "node_output",
        "node_output_summary": "Brief Builder 汇总各节点输出"
    }]

    # 7. 验证 Brief
    validation_errors = []
    warnings = []

    try:
        brief = ResearchBrief.model_validate(brief_data)
    except ValidationError as e:
        validation_errors = e.errors()
        # 尝试部分有效版本
        brief = create_partial_brief(brief_data, validation_errors)
        warnings.append(f"部分字段验证失败: {validation_errors}")

    # 8. 保存到 Redis
    version_manager = BriefVersionManager(get_redis())
    current_version = version_manager.save_version(brief)

    return {
        **state,
        "brief_result": {
            "brief_id": brief.brief_id,
            "version": current_version,
            "brief": brief.model_dump(),
            "validation_errors": validation_errors,
            "warnings": warnings
        },
        "current_node": "brief",
        "status": "done"
    }
```

---

## 八、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/models/research_brief.py` | Research_Brief Pydantic Schema |
| `backend/core/brief_version.py` | 版本管理器 |
| `backend/core/brief_validation.py` | 字段验证工具 |
| `backend/api/routes_brief.py` | Brief API 路由 |
| `backend/agents/orchestrator/subgraphs/brief_builder_state.py` | Brief Builder 状态 |
| `backend/agents/orchestrator/subgraphs/brief_builder_node.py` | Brief Builder 逻辑 |
| `frontend/components/brief-editor.tsx` | 前端编辑器组件 |
| `frontend/components/audit-trail.tsx` | 审计历史组件 |

---

## 九、实施检查清单

- [ ] Research_Brief Pydantic Schema
- [ ] BriefVersionManager（Redis 版本管理）
- [ ] 字段验证函数
- [ ] Brief API（PATCH /briefs/{id}/fields）
- [ ] Brief Builder 子图
- [ ] 前端 BriefEditor 组件
- [ ] 审计历史 UI

---

## 十、下一步

Phase 1 剩余内容：
1. **Analysis Node**（调用 Text-to-Code Bridge + 处理数据）
2. **Writing Node**（生成提纲和草稿）
3. **4 个中断点的完整实现**