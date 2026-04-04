from __future__ import annotations

import csv
from pathlib import Path

from backend.agents.models.state import MainState
from backend.agents.tools.question_parser import parse_question


def run(state: MainState) -> MainState:
    data_files = state.get("data_files") or []
    file_path = data_files[0] if data_files else None
    file_manifest = state.get("file_manifest") or {}
    columns: list[str] = []
    preview: list[dict[str, str]] = []

    if file_path and Path(file_path).exists() and str(file_path).endswith(".csv"):
        with open(file_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            for index, row in enumerate(reader):
                preview.append(row)
                if index >= 2:
                    break
    else:
        columns = ["年份", "地区", "农业产值", "碳排放总量", "农药使用量"]

    parsed = parse_question(state["user_query"], columns)
    mapping = {
        "dependent_var": parsed.dependent_var,
        "independent_vars": parsed.independent_vars,
        "control_vars": parsed.control_vars,
        "entity_column": "地区" if "地区" in columns else None,
        "time_column": "年份" if "年份" in columns else None,
        "columns": columns,
        "preview": preview,
        "file_manifest": file_manifest,
    }
    state["data_mapping_result"] = mapping
    state["current_node"] = "data_mapping"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "data_mapping_required"
    state["interrupt_data"] = {
        "recommended_mapping": mapping,
        "message": "请先确认变量映射，后续所有分析都依赖这一步。",
    }
    return state
