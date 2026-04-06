from __future__ import annotations

from backend.agents.models.state import MainState
from backend.agents.tools.model_recommender import recommend_models
from backend.agents.orchestrator.subgraphs.text_to_code_bridge import run_bridge


def run(state: MainState) -> MainState:
    mapping = state.get("data_mapping_result", {})
    has_panel = bool(mapping.get("entity_column") and mapping.get("time_column"))
    models = recommend_models(has_panel)

    # 运行 Text-to-Code Bridge（证据提取 → 代码生成 → 安全检查 → 沙箱执行）
    bridge_result = run_bridge(state)

    generated = bridge_result.get("generated_code") or {}
    exec_result = bridge_result.get("execution_result")
    bridge_status = bridge_result.get("bridge_status", "unknown")

    state["analysis_result"] = {
        "recommended_models": models,
        "code_script": generated.get("code_script", ""),
        "execution_plan": generated.get("execution_plan", []),
        "evidence_bindings": generated.get("evidence_bindings", []),
        "adaptation_explanation": generated.get("adaptation_explanation", ""),
        "check_result": bridge_result.get("check_result"),
        "execution_result": exec_result,
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
