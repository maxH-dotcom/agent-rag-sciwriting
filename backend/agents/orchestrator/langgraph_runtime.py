from __future__ import annotations

from copy import deepcopy
from typing import Any, TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from backend.agents.models.state import MainState
from backend.agents.orchestrator.main_graph import BaseResearchRuntime

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


class LangGraphResearchRuntime(BaseResearchRuntime):
    def __init__(self, checkpointer: "BaseCheckpointSaver | None" = None) -> None:
        super().__init__()
        self.runtime_name = "langgraph"
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MainState)

        workflow.add_node("entry_router", self._entry_router)
        for node_name, handler in self.node_map.items():
            workflow.add_node(node_name, handler)

        workflow.add_edge(START, "entry_router")
        workflow.add_conditional_edges(
            "entry_router",
            self._route_from_state,
            {name: name for name in self.node_map},
        )

        for node_name in self.node_map:
            workflow.add_conditional_edges(
                node_name,
                self._next_step_for_graph,
                {
                    "data_mapping": "data_mapping",
                    "literature": "literature",
                    "novelty": "novelty",
                    "analysis": "analysis",
                    "brief": "brief",
                    "writing": "writing",
                    "__end__": END,
                },
            )

        return workflow.compile(checkpointer=self.checkpointer)

    def _entry_router(self, state: MainState) -> MainState:
        return state

    def _route_from_state(self, state: MainState) -> str:
        return state["current_node"]

    def _next_step_for_graph(self, state: MainState) -> str:
        if state["status"] in {"interrupted", "done", "error", "aborted"}:
            return "__end__"
        next_node = self._next_node(state["current_node"])
        return next_node or "__end__"

    def run_until_pause(self, state: MainState, resume: bool = False) -> MainState:
        working = deepcopy(state)
        if resume:
            working = self._prepare_resume(working)
            if working["status"] == "aborted":
                return working
        config: dict[str, Any] = {}
        if self.checkpointer is not None:
            config = {"configurable": {"thread_id": working.get("task_id", "default")}}
        return self.graph.invoke(working, config=config)
