from __future__ import annotations

from typing import Any, TypedDict


class MainState(TypedDict, total=False):
    task_id: str
    task_type: str
    user_query: str
    current_node: str
    status: str
    next_action: str | None
    data_files: list[str]
    paper_files: list[str]
    file_manifest: dict[str, Any] | None
    data_mapping_result: dict[str, Any] | None
    literature_result: dict[str, Any] | None
    novelty_result: dict[str, Any] | None
    analysis_result: dict[str, Any] | None
    brief_result: dict[str, Any] | None
    writing_result: dict[str, Any] | None
    interrupt_reason: str | None
    interrupt_data: dict[str, Any] | None
    human_decision: dict[str, Any] | None
    result: dict[str, Any] | None


NODE_SEQUENCE = [
    "data_mapping",
    "literature",
    "novelty",
    "analysis",
    "brief",
    "writing",
]
