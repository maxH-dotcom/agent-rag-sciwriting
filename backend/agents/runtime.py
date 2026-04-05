from __future__ import annotations

from typing import Any

from backend.core.config import LANGGRAPH_CHECKPOINT_BACKEND, ORCHESTRATION_BACKEND, REDIS_URL
from backend.agents.orchestrator.main_graph import ResearchAssistantOrchestrator


def _create_checkpointer():
    backend = LANGGRAPH_CHECKPOINT_BACKEND
    if backend == "redis":
        from backend.core.redis_checkpointer import RedisStringCheckpointer
        return RedisStringCheckpointer(REDIS_URL)
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


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
    langgraph_info = detect_langgraph_support()
    backend = ORCHESTRATION_BACKEND
    if backend == "langgraph" and langgraph_info["available"]:
        from backend.agents.orchestrator.langgraph_runtime import LangGraphResearchRuntime

        checkpointer = _create_checkpointer()
        return LangGraphResearchRuntime(checkpointer=checkpointer)
    return ResearchAssistantOrchestrator()


def get_orchestration_runtime_info() -> dict[str, Any]:
    langgraph = detect_langgraph_support()
    backend = ORCHESTRATION_BACKEND
    effective_backend = backend
    checkpointer_backend = LANGGRAPH_CHECKPOINT_BACKEND

    if backend == "langgraph" and not langgraph["available"]:
        effective_backend = "custom"

    return {
        "configured_backend": backend,
        "effective_backend": effective_backend,
        "langgraph": langgraph,
        "checkpoint_status": (
            "langgraph_with_redis"
            if (langgraph["available"] and backend == "langgraph" and checkpointer_backend == "redis")
            else "langgraph_with_memory"
            if (langgraph["available"] and backend == "langgraph")
            else "custom_runtime_with_checkpoint_repository"
        ),
        "checkpoint_backend": checkpointer_backend,
        "factory_ready": True,
    }
