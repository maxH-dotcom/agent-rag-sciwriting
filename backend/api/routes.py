from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    AbortTaskRequest,
    ContinueTaskRequest,
    CreateTaskRequest,
    RuntimeInfoResponse,
    TaskCheckpointResponse,
    TaskHistoryResponse,
    TaskListResponse,
    TaskResponse,
)
from backend.agents.runtime import get_orchestration_runtime_info
from backend.core.task_store import store


router = APIRouter()


@router.get("/system/runtime", response_model=RuntimeInfoResponse)
def get_runtime_info() -> RuntimeInfoResponse:
    payload = get_orchestration_runtime_info()
    payload["task_repository_backend"] = store.repository.backend_name
    payload["checkpoint_repository_backend"] = store.checkpoint_repository.backend_name
    return RuntimeInfoResponse(**payload)


@router.post("/tasks", response_model=TaskResponse)
def create_task(request: CreateTaskRequest) -> TaskResponse:
    try:
        return TaskResponse.model_validate(store.create_task(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks() -> TaskListResponse:
    return TaskListResponse(items=[TaskResponse.model_validate(item) for item in store.list_tasks()])


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str) -> TaskResponse:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}/history", response_model=TaskHistoryResponse)
def get_task_history(task_id: str) -> TaskHistoryResponse:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskHistoryResponse(task_id=task_id, history=task.get("history", []))


@router.get("/tasks/{task_id}/checkpoints", response_model=TaskCheckpointResponse)
def get_task_checkpoints(task_id: str) -> TaskCheckpointResponse:
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskCheckpointResponse(task_id=task_id, checkpoints=store.get_checkpoints(task_id))


@router.post("/tasks/{task_id}/continue", response_model=TaskResponse)
def continue_task(task_id: str, request: ContinueTaskRequest) -> TaskResponse:
    try:
        task = store.continue_task(task_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/abort", response_model=TaskResponse)
def abort_task(task_id: str, request: AbortTaskRequest) -> TaskResponse:
    try:
        task = store.abort_task(task_id, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    return TaskResponse.model_validate(task)
