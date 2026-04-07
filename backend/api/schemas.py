from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "running", "interrupted", "done", "error", "aborted"]


class SettingsResponse(BaseModel):
    settings: Dict[str, Any]
    available_models: List[str]
    sandbox_config: Dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    updates: Dict[str, Any]


class CreateTaskRequest(BaseModel):
    task_type: str = Field(default="analysis")
    user_query: str = Field(min_length=1, description="用户研究问题")
    data_files: List[str] = Field(default_factory=list, description="数据文件路径")
    paper_files: List[str] = Field(default_factory=list, description="参考论文路径")


class ContinueTaskRequest(BaseModel):
    decision: Literal["approved", "modified", "rejected"]
    payload: Dict[str, Any] = Field(default_factory=dict)


class AbortTaskRequest(BaseModel):
    reason: str = "user_aborted"


class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    user_query: str
    data_files: List[str] = Field(default_factory=list)
    paper_files: List[str] = Field(default_factory=list)
    file_manifest: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_node: str
    status: TaskStatus
    next_action: Optional[str] = None
    interrupt_reason: Optional[str] = None
    interrupt_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    items: List[TaskResponse]


class TaskHistoryResponse(BaseModel):
    task_id: str
    history: List[Dict[str, Any]]


class TaskCheckpointResponse(BaseModel):
    task_id: str
    checkpoints: List[Dict[str, Any]]


class FileUploadResponse(BaseModel):
    path: str = Field(description="服务端绝对路径，可直接用于 data_files/paper_files")
    name: str
    suffix: str
    size_bytes: int
    kind: Literal["data", "paper"]


class MultiFileUploadResponse(BaseModel):
    files: List[FileUploadResponse]


class TaskCreationError(BaseModel):
    code: str = Field(description="错误代码")
    message: str = Field(description="错误原因（用户可读）")
    guidance: str = Field(description="如何修复")
    detail: Optional[str] = Field(default=None, description="原始错误详情")


class RuntimeInfoResponse(BaseModel):
    configured_backend: str
    effective_backend: str
    langgraph: Dict[str, Any]
    checkpoint_status: str
    factory_ready: bool
    task_repository_backend: str
    checkpoint_repository_backend: str
