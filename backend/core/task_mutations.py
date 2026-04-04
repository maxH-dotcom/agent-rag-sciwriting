from __future__ import annotations

from typing import Any

from backend.agents.models.state import MainState


def apply_human_payload(state: MainState, payload: dict[str, Any] | None) -> MainState:
    if not payload:
        return state

    current_node = state.get("current_node")

    if current_node == "data_mapping":
        current = dict(state.get("data_mapping_result") or {})
        current.update(payload)
        state["data_mapping_result"] = current
        if state.get("interrupt_data"):
            state["interrupt_data"]["recommended_mapping"] = current

    elif current_node == "analysis":
        current = dict(state.get("analysis_result") or {})
        current.update(payload)
        state["analysis_result"] = current
        state["interrupt_data"] = current

    elif current_node == "brief":
        current = dict(state.get("brief_result") or {})
        current.update(payload)
        state["brief_result"] = current
        state["interrupt_data"] = current

    elif current_node == "novelty":
        current = dict(state.get("novelty_result") or {})
        current.update(payload)
        state["novelty_result"] = current
        state["interrupt_data"] = current

    return state

