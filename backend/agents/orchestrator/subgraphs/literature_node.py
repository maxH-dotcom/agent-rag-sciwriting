from __future__ import annotations

from backend.agents.models.state import MainState
from backend.agents.tools.literature_search import retrieve_literature


def run(state: MainState) -> MainState:
    state["literature_result"] = retrieve_literature(
        state["user_query"],
        paper_files=state.get("paper_files", []),
    )
    state["current_node"] = "literature"
    state["status"] = "running"
    state["next_action"] = "continue_pipeline"
    state["interrupt_reason"] = None
    state["interrupt_data"] = None
    return state
