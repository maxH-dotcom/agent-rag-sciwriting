from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from backend.agents.models.state import MainState
from backend.agents.tools.question_parser import parse_question


def _infer_and_convert_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    自动检测并转换数据列类型。

    规则:
    - 年份/年度/Year 列: 转为 int (检测 "2020", "2020年", 2020.0 格式)
    - 数值列: 转为 float
    - 地区/Entity 列: 保持 string
    """
    df = df.copy()

    # 年份列识别
    year_patterns = ["年份", "年度", "Year", "year", "年"]
    year_col = None
    for col in df.columns:
        col_clean = col.replace("\n", "").replace(" ", "")
        if any(p in col_clean for p in year_patterns):
            year_col = col
            break

    if year_col:
        # 转换为 int
        def parse_year(val):
            if pd.isna(val):
                return val
            s = str(val).strip()
            s = re.sub(r"[年.\s]", "", s)
            try:
                return int(float(s))
            except (ValueError, TypeError):
                return val

        df[year_col] = df[year_col].apply(parse_year)

    # 数值列识别 (排除明显非数值列)
    non_numeric_cols = {"地区", "城市", "省份", "地区代码", "地区·代码", "entity", "time"}
    for col in df.columns:
        col_clean = col.replace("\n", "").replace(" ", "")
        if col_clean in non_numeric_cols or col == year_col:
            continue
        if df[col].dtype == object:  # string 列
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass  # 保持原样

    return df


def run(state: MainState) -> MainState:
    data_files = state.get("data_files") or []
    file_path = data_files[0] if data_files else None
    file_manifest = state.get("file_manifest") or {}
    columns: list[str] = []
    preview: list[dict[str, str]] = []

    if file_path:
        suffix = Path(file_path).suffix.lower()
        if not Path(file_path).exists():
            state["status"] = "error"
            state["next_action"] = None
            state["interrupt_reason"] = "data_file_not_found"
            state["interrupt_data"] = {
                "message": f"数据文件不存在: {file_path}",
                "provided_path": file_path,
                "hint": "请在创建任务时提供正确的数据文件路径",
            }
            return state
        if suffix not in {".csv", ".xlsx", ".xls"}:
            state["status"] = "error"
            state["next_action"] = None
            state["interrupt_reason"] = "unsupported_file_type"
            state["interrupt_data"] = {
                "message": f"不支持的文件类型，仅支持 CSV/XLSX/XLS: {file_path}",
                "provided_path": file_path,
            }
            return state

        try:
            if suffix == ".csv":
                df_preview = pd.read_csv(file_path, nrows=3, encoding="utf-8-sig")
            else:
                df_preview = pd.read_excel(file_path, nrows=3)
            df_preview = _infer_and_convert_dtypes(df_preview)
            columns = df_preview.columns.tolist()
            preview = df_preview.to_dict(orient="records")
        except Exception as exc:
            if suffix == ".csv":
                with open(file_path, "r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    columns = reader.fieldnames or []
                    for index, row in enumerate(reader):
                        preview.append(row)
                        if index >= 2:
                            break
            else:
                state["status"] = "error"
                state["next_action"] = None
                state["interrupt_reason"] = "data_file_parse_error"
                state["interrupt_data"] = {
                    "message": f"无法读取 Excel 数据文件: {Path(file_path).name}",
                    "provided_path": file_path,
                    "detail": str(exc),
                    "hint": "请确认文件未损坏，并已安装 openpyxl 依赖。",
                }
                return state
    else:
        # 无文件时用 fallback 列（测试场景或用户未上传数据文件）
        columns = ["年份", "地区", "农业产值", "碳排放总量", "农药使用量"]

    parsed = parse_question(state["user_query"], columns)
    mapping = {
        "dependent_var": parsed.dependent_var,
        "independent_vars": parsed.independent_vars,
        "control_vars": parsed.control_vars,
        "entity_column": "地区" if "地区" in columns else None,
        "time_column": "年份" if "年份" in columns else None,
        "method_preference": parsed.method_preference,
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
