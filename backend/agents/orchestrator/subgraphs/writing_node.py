from __future__ import annotations

from backend.agents.models.state import MainState


def run(state: MainState) -> MainState:
    brief = state.get("brief_result", {})
    goal = brief.get("research_goal", state["user_query"])
    writing_result = {
        "outline": [
            "1. 研究背景与问题",
            "2. 数据与变量映射",
            "3. 方法与证据依据",
            "4. 结果展示与解释",
            "5. 局限性与后续工作",
        ],
        "methods": f"本文围绕“{goal}”构建分析流程，优先采用证据支持的可解释模型，并保留人工审核环节。",
        "results": "结果部分将在代码执行后填充关键系数、显著性和图表说明。",
        "abstract": f"本研究提出一套面向科研工作流的辅助系统，用于支持“{goal}”的问题分析。",
    }
    state["writing_result"] = writing_result
    state["result"] = {
        "brief": brief,
        "draft": writing_result,
    }
    state["current_node"] = "writing"
    state["status"] = "done"
    state["next_action"] = None
    state["interrupt_reason"] = None
    state["interrupt_data"] = None
    return state

