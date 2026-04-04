from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:  # pragma: no cover - fallback for bare Python environments
    BaseModel = None
    Field = None


if BaseModel is not None:
    class ResearchBrief(BaseModel):
        version: str = "1.0.0"
        task_id: str
        research_goal: str
        status: str = "draft"
        data_summary: dict[str, Any] = Field(default_factory=dict)
        novelty_position: dict[str, Any] = Field(default_factory=dict)
        method_decision: dict[str, Any] = Field(default_factory=dict)
        analysis_outputs: dict[str, Any] = Field(default_factory=dict)
        evidence_map: dict[str, Any] = Field(default_factory=dict)
        draft_sections: dict[str, Any] = Field(default_factory=dict)
        audit_trail: list[dict[str, Any]] = Field(default_factory=list)
else:
    @dataclass
    class ResearchBrief:
        version: str = "1.0.0"
        task_id: str = ""
        research_goal: str = ""
        status: str = "draft"
        data_summary: dict[str, Any] = field(default_factory=dict)
        novelty_position: dict[str, Any] = field(default_factory=dict)
        method_decision: dict[str, Any] = field(default_factory=dict)
        analysis_outputs: dict[str, Any] = field(default_factory=dict)
        evidence_map: dict[str, Any] = field(default_factory=dict)
        draft_sections: dict[str, Any] = field(default_factory=dict)
        audit_trail: list[dict[str, Any]] = field(default_factory=list)

        def model_dump(self) -> dict[str, Any]:
            return asdict(self)
