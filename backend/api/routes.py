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
    SettingsResponse,
    SettingsUpdateRequest,
    TaskCheckpointResponse,
    TaskCreationError,
    TaskHistoryResponse,
    TaskListResponse,
    TaskResponse,
)
from backend.agents.runtime import get_orchestration_runtime_info
from backend.core.config import (
    DEFAULT_SANDBOX_TIMEOUT,
    MAX_OUTPUT_SIZE,
    UPLOAD_DIR,
    get_settings,
    update_settings,
)
from backend.core.file_validation import (
    FileValidationError,
    SUPPORTED_DATA_SUFFIXES,
    SUPPORTED_PAPER_SUFFIXES,
)
from backend.core.task_store import store

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

router = APIRouter()


@router.get("/system/runtime", response_model=RuntimeInfoResponse)
def get_runtime_info() -> RuntimeInfoResponse:
    payload = get_orchestration_runtime_info()
    payload["task_repository_backend"] = store.repository.backend_name
    payload["checkpoint_repository_backend"] = store.checkpoint_repository.backend_name
    return RuntimeInfoResponse(**payload)


@router.get("/settings", response_model=SettingsResponse)
def get_settings_endpoint() -> SettingsResponse:
    """获取当前配置."""
    config = get_settings()
    return SettingsResponse(
        settings=config,
        available_models=[
            "PanelOLS", "DID", "ARIMA", "SARIMA", "Prophet", "VAR",
            "GARCH", "XGBoost", "LSTM", "RandomForest", "SDM", "SEM",
        ],
        sandbox_config={
            "timeout_seconds": config.get("sandbox_timeout", DEFAULT_SANDBOX_TIMEOUT),
            "max_output_size": config.get("max_output_size", MAX_OUTPUT_SIZE),
            "allowed_imports": list({
                "pandas", "numpy", "scipy", "statsmodels", "sklearn",
                "matplotlib", "seaborn", "linearmodels",
            }),
        },
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings_endpoint(request: SettingsUpdateRequest) -> SettingsResponse:
    """更新配置 (仅支持特定字段)."""
    config = update_settings(request.updates)
    return SettingsResponse(
        settings=config,
        available_models=[
            "PanelOLS", "DID", "ARIMA", "SARIMA", "Prophet", "VAR",
            "GARCH", "XGBoost", "LSTM", "RandomForest", "SDM", "SEM",
        ],
        sandbox_config={
            "timeout_seconds": config.get("sandbox_timeout", DEFAULT_SANDBOX_TIMEOUT),
            "max_output_size": config.get("max_output_size", MAX_OUTPUT_SIZE),
            "allowed_imports": list({
                "pandas", "numpy", "scipy", "statsmodels", "sklearn",
                "matplotlib", "seaborn", "linearmodels",
            }),
        },
    )


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
    except FileValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE",
                "message": str(exc),
                "guidance": _build_file_error_guidance(str(exc)),
                "detail": None,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _build_file_error_guidance(error_msg: str) -> str:
    msg = error_msg.lower()
    if "必须是绝对路径" in error_msg:
        return "请使用绝对路径，例如：/Users/你的名字/data.csv 或 C:\\Users\\你的名字\\data.csv"
    if "文件不存在" in error_msg:
        return "请检查文件路径是否正确，路径中不要有拼写错误或多余空格"
    if "不是文件" in error_msg:
        return "该路径存在但不是文件，请确认传入的是文件路径而非文件夹路径"
    if "csv" in msg:
        return "数据文件仅支持 CSV/XLSX/XLS 格式，请确保文件格式正确"
    if "pdf" in msg or "txt" in msg or "md" in msg:
        return "论文文件仅支持 PDF/TXT/MD 格式"
    if "类型不支持" in error_msg:
        data_types = ", ".join(SUPPORTED_DATA_SUFFIXES)
        paper_types = ", ".join(SUPPORTED_PAPER_SUFFIXES)
        return f"不支持的文件格式。数据文件用：{data_types}，论文文件用：{paper_types}"
    return "请检查文件路径是否正确，文件是否存在，格式是否支持"


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
