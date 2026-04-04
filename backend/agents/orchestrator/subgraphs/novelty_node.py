from __future__ import annotations

from backend.agents.models.state import MainState


def run(state: MainState) -> MainState:
    methods = state.get("literature_result", {}).get("method_metadata", [])
    recommended_method = methods[0]["method_name"] if methods else "固定效应模型"
    novelty_result = {
        "transfer_assessments": [
            {
                "method_name": recommended_method,
                "transfer_feasibility": "高",
                "transfer_feasibility_reason": "目标问题和文献中的面板型驱动因素分析高度接近。",
                "required_adaptations": [
                    "确认变量映射是否与原研究一致",
                    "补充控制变量的领域解释",
                ],
            }
        ],
        "recommended_direction": {
            "summary": f"优先沿着“{recommended_method} + 证据驱动代码生成”推进。",
            "why": "这条路线解释性强，适合第一版产品沉淀测试样本和人工审核流程。",
        },
        "differentiation_points": [
            "把文献证据、代码方案和写作草稿串成一条工作流",
            "保留人工中断点，避免黑箱一把梭",
        ],
    }
    state["novelty_result"] = novelty_result
    state["current_node"] = "novelty"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "novelty_result_ready"
    state["interrupt_data"] = novelty_result
    return state

