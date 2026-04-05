from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class MainState(TypedDict, total=False):
    task_id: str
    task_type: str
    user_query: str
    current_node: str
    status: str
    next_action: Optional[str]
    data_files: List[str]
    paper_files: List[str]
    file_manifest: Optional[Dict[str, Any]]
    data_mapping_result: Optional[Dict[str, Any]]
    literature_result: Optional[Dict[str, Any]]
    novelty_result: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    brief_result: Optional[Dict[str, Any]]
    writing_result: Optional[Dict[str, Any]]
    interrupt_reason: Optional[str]
    interrupt_data: Optional[Dict[str, Any]]
    human_decision: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]


NODE_SEQUENCE = [
    "data_mapping",
    "literature",
    "novelty",
    "analysis",
    "brief",
    "writing",
]
