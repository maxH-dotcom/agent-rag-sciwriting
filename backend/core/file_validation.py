from __future__ import annotations

from pathlib import Path
from typing import Literal


SUPPORTED_DATA_SUFFIXES = {".csv", ".xlsx", ".xls"}
SUPPORTED_PAPER_SUFFIXES = {".pdf", ".txt", ".md"}


class FileValidationError(ValueError):
    """Raised when user-provided file paths are invalid."""


def _validate_file(path_str: str, *, kind: Literal["data", "paper"]) -> dict:
    path = Path(path_str).expanduser()
    allowed_suffixes = SUPPORTED_DATA_SUFFIXES if kind == "data" else SUPPORTED_PAPER_SUFFIXES

    if not path.is_absolute():
        raise FileValidationError(f"{kind} 文件路径必须是绝对路径: {path_str}")
    if not path.exists():
        raise FileValidationError(f"{kind} 文件不存在: {path_str}")
    if not path.is_file():
        raise FileValidationError(f"{kind} 路径不是文件: {path_str}")
    if path.suffix.lower() not in allowed_suffixes:
        raise FileValidationError(
            f"{kind} 文件类型不支持: {path.suffix or '无后缀'}，允许类型: {sorted(allowed_suffixes)}"
        )

    return {
        "path": str(path.resolve()),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "kind": kind,
    }


def validate_user_files(data_files: list[str], paper_files: list[str]) -> dict:
    validated_data_files = [_validate_file(path, kind="data") for path in data_files]
    validated_paper_files = [_validate_file(path, kind="paper") for path in paper_files]

    return {
        "data_files": validated_data_files,
        "paper_files": validated_paper_files,
    }
