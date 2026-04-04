from __future__ import annotations

from typing import Any

from backend.core.config import ORCHESTRATION_BACKEND
from backend.agents.orchestrator.main_graph import ResearchAssistantOrchestrator


def detect_langgraph_support() -> dict[str, Any]:
    try:
        import langgraph  # type: ignore # pragma: no cover - optional dependency
    except ModuleNotFoundError:
        return {
            "available": False,
            "reason": "langgraph 未安装，当前使用自定义编排器。",
            "version": None,
        }

    return {
        "available": True,
        "reason": "langgraph 已安装，可进入下一步真实编排接入。",
        "version": getattr(langgraph, "__version__", "unknown"),
    }


def create_research_runtime():
    langgraph = detect_langgraph_support()
    backend = ORCHESTRATION_BACKEND
    if backend == "langgraph" and langgraph["available"]:
        from backend.agents.orchestrator.langgraph_runtime import LangGraphResearchRuntime

        return LangGraphResearchRuntime()
    return ResearchAssistantOrchestrator()


def get_orchestration_runtime_info() -> dict[str, Any]:
    langgraph = detect_langgraph_support()
    backend = ORCHESTRATION_BACKEND
    effective_backend = backend

    if backend == "langgraph" and not langgraph["available"]:
        effective_backend = "custom"

    return {
        "configured_backend": backend,
        "effective_backend": effective_backend,
        "langgraph": langgraph,
        "checkpoint_status": (
            "ready_for_langgraph"
            if langgraph["available"]
            else "custom_runtime_with_checkpoint_repository"
        ),
        "factory_ready": True,
    }
