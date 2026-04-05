from __future__ import annotations

from backend.agents.models.state import MainState
from backend.agents.tools.literature_search import retrieve_literature


def run(state: MainState) -> MainState:
    state["literature_result"] = retrieve_literature(
        state["user_query"],
        paper_files=state.get("paper_files", []),
    )
    state["current_node"] = "literature"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "literature_review_required"
    state["interrupt_data"] = {
        "literature_result": state["literature_result"],
        "message": "请审核文献检索结果，确认相关性和完整性后再继续。",
    }
    return state
