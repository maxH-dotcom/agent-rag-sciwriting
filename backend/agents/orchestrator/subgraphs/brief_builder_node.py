from __future__ import annotations

from backend.agents.models.research_brief import ResearchBrief
from backend.agents.models.state import MainState


def run(state: MainState) -> MainState:
    brief = ResearchBrief(
        task_id=state["task_id"],
        research_goal=state["user_query"],
        data_summary=state.get("data_mapping_result") or {},
        novelty_position=state.get("novelty_result") or {},
        method_decision={
            "recommended_models": state.get("analysis_result", {}).get("recommended_models", []),
            "evidence": state.get("literature_result", {}).get("references", []),
        },
        analysis_outputs=state.get("analysis_result") or {},
        evidence_map={"chunks": state.get("literature_result", {}).get("all_chunks", [])},
        audit_trail=[
            {"node": "brief", "action": "assembled"},
        ],
    )
    state["brief_result"] = brief.model_dump()
    state["current_node"] = "brief"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "brief_ready_for_review"
    state["interrupt_data"] = state["brief_result"]
    return state

