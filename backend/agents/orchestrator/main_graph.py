from __future__ import annotations

from copy import deepcopy
from typing import Callable, Dict

from backend.agents.models.state import MainState, NODE_SEQUENCE
from backend.agents.orchestrator.subgraphs import (
    analysis_node,
    brief_builder_node,
    data_mapping_node,
    literature_node,
    novelty_node,
    writing_node,
)


class BaseResearchRuntime:
    def __init__(self) -> None:
        self.node_map: Dict[str, Callable[[MainState], MainState]] = {
            "data_mapping": data_mapping_node.run,
            "literature": literature_node.run,
            "novelty": novelty_node.run,
            "analysis": analysis_node.run,
            "brief": brief_builder_node.run,
            "writing": writing_node.run,
        }
        self.runtime_name = "base"

    def create_initial_state(
        self,
        task_id: str,
        task_type: str,
        user_query: str,
        data_files: list[str],
        paper_files: list[str],
        file_manifest: dict | None = None,
    ) -> MainState:
        return MainState(
            task_id=task_id,
            task_type=task_type,
            user_query=user_query,
            current_node="data_mapping",
            status="pending",
            next_action="start_pipeline",
            data_files=data_files,
            paper_files=paper_files,
            file_manifest=file_manifest,
            data_mapping_result=None,
            literature_result=None,
            novelty_result=None,
            analysis_result=None,
            brief_result=None,
            writing_result=None,
            interrupt_reason=None,
            interrupt_data=None,
            human_decision=None,
            result=None,
        )

    def _next_node(self, current_node: str) -> str | None:
        try:
            index = NODE_SEQUENCE.index(current_node)
        except ValueError:
            return None
        next_index = index + 1
        return NODE_SEQUENCE[next_index] if next_index < len(NODE_SEQUENCE) else None

    def _prepare_resume(self, state: MainState) -> MainState:
        working = deepcopy(state)
        decision = working.get("human_decision", {})
        if decision.get("decision") == "rejected":
            working["status"] = "aborted"
            working["next_action"] = None
            working["interrupt_reason"] = "user_rejected_current_stage"
            return working
        next_node = self._next_node(working["current_node"])
        if next_node is None:
            return working
        working["current_node"] = next_node
        working["status"] = "running"
        working["interrupt_reason"] = None
        working["interrupt_data"] = None
        return working

    def run_until_pause(self, state: MainState, resume: bool = False) -> MainState:
        raise NotImplementedError

    def to_task_response(self, state: MainState) -> dict:
        return {
            "task_id": state["task_id"],
            "task_type": state["task_type"],
            "user_query": state["user_query"],
            "data_files": state.get("data_files", []),
            "paper_files": state.get("paper_files", []),
            "file_manifest": state.get("file_manifest"),
            "created_at": "",
            "updated_at": "",
            "current_node": state["current_node"],
            "status": state["status"],
            "next_action": state.get("next_action"),
            "interrupt_reason": state.get("interrupt_reason"),
            "interrupt_data": state.get("interrupt_data"),
            "result": {
                "data_mapping_result": state.get("data_mapping_result"),
                "literature_result": state.get("literature_result"),
                "novelty_result": state.get("novelty_result"),
                "analysis_result": state.get("analysis_result"),
                "brief_result": state.get("brief_result"),
                "writing_result": state.get("writing_result"),
                "final_output": state.get("result"),
                "human_decision": state.get("human_decision"),
            },
            "history": [],
            "runtime_backend": self.runtime_name,
        }

    def from_task_response(self, payload: dict) -> MainState:
        result = payload.get("result") or {}
        return MainState(
            task_id=payload["task_id"],
            task_type=payload["task_type"],
            user_query=payload["user_query"],
            current_node=payload["current_node"],
            status=payload["status"],
            next_action=payload.get("next_action"),
            data_files=payload.get("data_files", []),
            paper_files=payload.get("paper_files", []),
            file_manifest=payload.get("file_manifest"),
            data_mapping_result=result.get("data_mapping_result"),
            literature_result=result.get("literature_result"),
            novelty_result=result.get("novelty_result"),
            analysis_result=result.get("analysis_result"),
            brief_result=result.get("brief_result"),
            writing_result=result.get("writing_result"),
            interrupt_reason=payload.get("interrupt_reason"),
            interrupt_data=payload.get("interrupt_data"),
            human_decision=result.get("human_decision"),
            result=result.get("final_output"),
        )


class ResearchAssistantOrchestrator(BaseResearchRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.runtime_name = "custom"

    def run_until_pause(self, state: MainState, resume: bool = False) -> MainState:
        working = deepcopy(state)

        if resume:
            working = self._prepare_resume(working)
            if working["status"] == "aborted":
                return working

        while True:
            node_name = working["current_node"]
            handler = self.node_map[node_name]
            working = handler(working)
            if working["status"] in {"interrupted", "done", "error", "aborted"}:
                return working
            next_node = self._next_node(node_name)
            if next_node is None:
                return working
            working["current_node"] = next_node
