"""Text-to-Code Bridge 数据模型.

兼容 Pydantic v1 (1.10.x)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _to_dict(obj: BaseModel) -> Dict[str, Any]:
    """兼容 Pydantic v1/v2 的序列化."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj.dict()


class EvidenceChunk(BaseModel):
    """单个证据块 — 来自文献检索结果."""

    chunk_id: str
    source: str  # 来源描述，如 "OpenAlex: Author (2020)"
    text: str
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


class EvidencePackage(BaseModel):
    """证据包：代码生成所需的所有文献依据."""

    task_id: str
    evidence_chunks: List[EvidenceChunk] = Field(default_factory=list)
    quality_score: float = 0.0
    quality_warning: Optional[str] = None
    missing_aspects: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


class CodeCheckResult(BaseModel):
    """代码自动检查结果."""

    passed: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


class EvidenceBinding(BaseModel):
    """代码步骤与证据的绑定关系."""

    step: int
    operation: str
    evidence_chunk_id: Optional[str] = None
    line_numbers: List[int] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


class GeneratedCode(BaseModel):
    """生成的代码及其元数据."""

    code_script: str
    imports: List[str] = Field(default_factory=list)
    execution_plan: List[str] = Field(default_factory=list)
    evidence_bindings: List[EvidenceBinding] = Field(default_factory=list)
    check_result: Optional[CodeCheckResult] = None
    adaptation_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)


class ExecutionResult(BaseModel):
    """代码执行结果."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    output_files: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _to_dict(self)
