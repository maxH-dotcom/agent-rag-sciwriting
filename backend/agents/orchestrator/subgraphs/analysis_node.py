from __future__ import annotations

import json
import re

from backend.agents.models.state import MainState
from backend.agents.tools.model_recommender import recommend_models, recommend_models_by_method_preference
from backend.agents.orchestrator.subgraphs.text_to_code_bridge import run_bridge


def run(state: MainState) -> MainState:
    mapping = state.get("data_mapping_result", {})
    has_panel = bool(mapping.get("entity_column") and mapping.get("time_column"))

    # 优先使用用户指定的方法偏好
    method_pref = mapping.get("method_preference")
    if method_pref:
        models = recommend_models_by_method_preference(method_pref, has_panel)
    else:
        models = recommend_models(has_panel)

    # 运行 Text-to-Code Bridge（证据提取 → 代码生成 → 安全检查 → 沙箱执行）
    bridge_result = run_bridge(state)

    generated = bridge_result.get("generated_code") or {}
    exec_result = bridge_result.get("execution_result")
    bridge_status = bridge_result.get("bridge_status", "unknown")
    result_summary = _extract_result_summary(exec_result)

    state["analysis_result"] = {
        "recommended_models": models,
        "code_script": generated.get("code_script", ""),
        "execution_plan": generated.get("execution_plan", []),
        "evidence_bindings": generated.get("evidence_bindings", []),
        "adaptation_explanation": generated.get("adaptation_explanation", ""),
        "check_result": bridge_result.get("check_result"),
        "execution_result": exec_result,
        "result_summary": result_summary,
        "bridge_status": bridge_status,
        "bridge_error": bridge_result.get("bridge_error"),
        "evidence_package": bridge_result.get("evidence_package"),
    }
    state["current_node"] = "analysis"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "code_plan_ready"
    state["interrupt_data"] = {
        "code_script": generated.get("code_script", ""),
        "execution_plan": generated.get("execution_plan", []),
        "recommended_models": models,
        "bridge_status": bridge_status,
        "execution_result": exec_result,
        "result_summary": result_summary,
        "adaptation_explanation": generated.get("adaptation_explanation", ""),
        "message": _build_message(bridge_status, exec_result),
    }
    return state


def _build_message(bridge_status: str, exec_result: dict | None) -> str:
    if bridge_status == "check_failed":
        return "代码安全检查未通过，请审核后决定是否调整。"
    if bridge_status == "execution_failed":
        err = (exec_result or {}).get("error_message", "未知错误")
        return f"代码已执行但失败: {err}。请审核代码方案。"
    if bridge_status == "success":
        return "代码已生成并成功执行，请审核分析结果和代码方案后继续。"
    return "请审核生成的代码方案后继续。"


def _extract_result_summary(exec_result: dict | None) -> dict | None:
    if not exec_result:
        return None

    structured = _extract_structured_result(exec_result)
    if not structured:
        return None

    coefficients = structured.get("coefficients") or {}
    primary_name = None
    primary_payload = None
    for name, payload in coefficients.items():
        if name != "const":
            primary_name = name
            primary_payload = payload or {}
            break

    coef = primary_payload.get("coef") if isinstance(primary_payload, dict) else None
    pvalue = primary_payload.get("pvalue") if isinstance(primary_payload, dict) else None

    direction = None
    if isinstance(coef, (int, float)):
        if coef > 0:
            direction = "positive"
        elif coef < 0:
            direction = "negative"
        else:
            direction = "neutral"

    significance = None
    if isinstance(pvalue, (int, float)):
        if pvalue < 0.01:
            significance = "high"
        elif pvalue < 0.05:
            significance = "medium"
        elif pvalue < 0.1:
            significance = "low"
        else:
            significance = "not_significant"

    summary_parts: list[str] = []
    if structured.get("method"):
        summary_parts.append(f"当前模型为 {structured['method']}")
    if isinstance(structured.get("n_obs"), (int, float)):
        summary_parts.append(f"样本量 {int(structured['n_obs'])}")
    if isinstance(structured.get("r_squared"), (int, float)):
        summary_parts.append(f"R²={structured['r_squared']:.4f}")
    elif isinstance(structured.get("r_squared_within"), (int, float)):
        summary_parts.append(f"组内 R²={structured['r_squared_within']:.4f}")
    if primary_name and direction:
        direction_text = {"positive": "正向", "negative": "负向", "neutral": "接近于零"}[direction]
        summary_parts.append(f"{primary_name} 对结果变量呈{direction_text}影响")
    if significance:
        significance_text = {
            "high": "在 1% 水平显著",
            "medium": "在 5% 水平显著",
            "low": "在 10% 水平边际显著",
            "not_significant": "统计上不显著",
        }[significance]
        summary_parts.append(significance_text)

    return {
        "method": structured.get("method"),
        "n_obs": structured.get("n_obs"),
        "r_squared": structured.get("r_squared"),
        "adj_r_squared": structured.get("adj_r_squared"),
        "r_squared_within": structured.get("r_squared_within"),
        "did_interaction_coef": structured.get("did_interaction_coef"),
        "primary_variable": primary_name,
        "primary_coef": coef,
        "primary_pvalue": pvalue,
        "direction": direction,
        "significance": significance,
        "summary_text": "，".join(summary_parts) + "。" if summary_parts else None,
        "coefficients": coefficients,
    }


def _extract_structured_result(exec_result: dict) -> dict | None:
    if isinstance(exec_result.get("coefficients"), dict) or exec_result.get("method"):
        return exec_result

    stdout = exec_result.get("stdout")
    if not isinstance(stdout, str):
        return None

    match = re.search(r"\{\s*\"method\"[\s\S]*\}\s*$", stdout)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
