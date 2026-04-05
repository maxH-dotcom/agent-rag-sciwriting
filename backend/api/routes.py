from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from backend.api.schemas import (
    AbortTaskRequest,
    ContinueTaskRequest,
    CreateTaskRequest,
    FileUploadResponse,
    MultiFileUploadResponse,
    RuntimeInfoResponse,
    TaskCheckpointResponse,
    TaskHistoryResponse,
    TaskListResponse,
    TaskResponse,
)
from backend.agents.runtime import get_orchestration_runtime_info
from backend.core.config import UPLOAD_DIR
from backend.core.file_validation import SUPPORTED_DATA_SUFFIXES, SUPPORTED_PAPER_SUFFIXES
from backend.core.task_store import store

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

router = APIRouter()


@router.get("/system/runtime", response_model=RuntimeInfoResponse)
def get_runtime_info() -> RuntimeInfoResponse:
    payload = get_orchestration_runtime_info()
    payload["task_repository_backend"] = store.repository.backend_name
    payload["checkpoint_repository_backend"] = store.checkpoint_repository.backend_name
    return RuntimeInfoResponse(**payload)


@router.post("/upload", response_model=MultiFileUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="上传数据文件或论文文件"),
    kind: str = Query("auto", description="文件类型：data / paper / auto（按后缀自动判断）"),
) -> MultiFileUploadResponse:
    """上传文件到服务端，返回绝对路径供后续 /tasks 使用。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    all_allowed = SUPPORTED_DATA_SUFFIXES | SUPPORTED_PAPER_SUFFIXES

    results: list[FileUploadResponse] = []
    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        # 后缀校验
        if suffix not in all_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"文件类型不支持: {suffix or '无后缀'}，允许: {sorted(all_allowed)}",
            )

        # 判断 kind
        if kind == "auto":
            file_kind = "data" if suffix in SUPPORTED_DATA_SUFFIXES else "paper"
        elif kind in ("data", "paper"):
            expected = SUPPORTED_DATA_SUFFIXES if kind == "data" else SUPPORTED_PAPER_SUFFIXES
            if suffix not in expected:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {filename} 后缀 {suffix} 与指定类型 {kind} 不匹配，"
                    f"允许: {sorted(expected)}",
                )
            file_kind = kind
        else:
            raise HTTPException(status_code=400, detail=f"kind 参数无效: {kind}，允许: data / paper / auto")

        # 读取内容并检查大小
        content = await upload.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件 {filename} 超过大小限制 ({MAX_UPLOAD_SIZE // 1024 // 1024} MB)",
            )

        # 保存：用 uuid 前缀防止文件名冲突
        safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        dest = UPLOAD_DIR / safe_name
        dest.write_bytes(content)

        results.append(
            FileUploadResponse(
                path=str(dest.resolve()),
                name=filename,
                suffix=suffix,
                size_bytes=len(content),
                kind=file_kind,
            )
        )

    return MultiFileUploadResponse(files=results)


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
