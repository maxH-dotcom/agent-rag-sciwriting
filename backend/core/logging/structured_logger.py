"""结构化日志（Phase 2）.

用法：
    from backend.core.logging.structured_logger import structured_logger

    logger = structured_logger(__name__)
    logger.set_context(task_id="task_123", node="literature")

    logger.info("node_started", "Literature search started",
                query="carbon emission panel data")

    logger.warning("latency_warning", "LLM call slow",
                   duration_ms=15000)

    logger.error("node_failed", "Literature node failed",
                 error_type="TimeoutError", error_msg=str(e))

    logger.clear_context()
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Context 变量（线程/协程安全）
_task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)
_node_var: ContextVar[str | None] = ContextVar("node", default=None)
_task_type_var: ContextVar[str | None] = ContextVar("task_type", default=None)


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """输出 JSON 行格式的日志Formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            # 时间戳（ISO 8601 UTC）
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            # 日志级别
            "level": record.levelname,
            # logger 名称
            "logger": record.name,
            # 消息
            "message": record.getMessage(),
            # 事件类型（由 extra["event"] 传入）
            "event": getattr(record, "event", None),
            # 调用上下文
            "task_id": _task_id_var.get(),
            "node": _node_var.get(),
            "task_type": _task_type_var.get(),
            # 调用位置
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 合并 extra 中的业务字段
        extra_fields = getattr(record, "extra", None)
        if extra_fields:
            log_entry.update(extra_fields)

        # 异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=_json_default)


def _json_default(obj: Any) -> Any:
    """处理不可 JSON 序列化的对象."""
    try:
        return str(obj)
    except Exception:
        return f"<non-serializable: {type(obj).__name__}>"


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------


class StructuredLogger:
    """
    结构化日志记录器。

    特性：
    - JSON 行输出（每行一个 JSON 对象，便于 grep / log pipeline）
    - 自动注入 task_id / node 上下文（协程/线程安全）
    - event 字段统一事件类型，便于索引和查询
    """

    _root_logger: logging.Logger | None = None
    _initialized: bool = False

    def __init__(self, name: str) -> None:
        self._name = name
        self._logger = logging.getLogger(name)

    # ---- 上下文管理 ----

    def set_context(
        self,
        task_id: str | None = None,
        node: str | None = None,
        task_type: str | None = None,
    ) -> None:
        """设置日志上下文（当前协程/线程有效）."""
        if task_id is not None:
            _task_id_var.set(task_id)
        if node is not None:
            _node_var.set(node)
        if task_type is not None:
            _task_type_var.set(task_type)

    def clear_context(self) -> None:
        """清除所有日志上下文."""
        _task_id_var.set(None)
        _node_var.set(None)
        _task_type_var.set(None)

    @property
    def task_id(self) -> str | None:
        return _task_id_var.get()

    @property
    def node(self) -> str | None:
        return _node_var.get()

    # ---- 上下文管理器 ----

    @classmethod
    def with_context(
        cls,
        task_id: str | None = None,
        node: str | None = None,
        task_type: str | None = None,
    ) -> "StructuredLogger":
        """临时设置上下文的上下文管理器（with 块结束后恢复）."""
        return _LoggerContextManager(cls, task_id, node, task_type)

    # ---- 日志方法 ----

    def _log(
        self,
        level: int,
        event: str | None,
        message: str,
        **metadata: Any,
    ) -> None:
        """通用日志方法."""
        extra = {"extra": {"event": event, **metadata}}
        self._logger.log(level, message, extra=extra)

    def debug(self, event: str | None, message: str, **metadata: Any) -> None:
        self._log(logging.DEBUG, event, message, **metadata)

    def info(self, event: str | None, message: str, **metadata: Any) -> None:
        self._log(logging.INFO, event, message, **metadata)

    def warning(self, event: str | None, message: str, **metadata: Any) -> None:
        self._log(logging.WARNING, event, message, **metadata)

    def error(self, event: str | None, message: str, **metadata: Any) -> None:
        self._log(logging.ERROR, event, message, **metadata)

    def critical(self, event: str | None, message: str, **metadata: Any) -> None:
        self._log(logging.CRITICAL, event, message, **metadata)


class _LoggerContextManager:
    """StructuredLogger.with_context() 的实现."""

    __slots__ = ("_logger", "_task_id", "_node", "_task_type")

    def __init__(
        self,
        logger_class: type[StructuredLogger],
        task_id: str | None,
        node: str | None,
        task_type: str | None,
    ) -> None:
        # 不创建新 logger，复用全局已配置的
        self._logger = structured_logger(logger_class.__class__.__name__)
        self._task_id = task_id
        self._node = node
        self._task_type = task_type

    def __enter__(self) -> StructuredLogger:
        self._logger.set_context(
            task_id=self._task_id,
            node=self._node,
            task_type=self._task_type,
        )
        return self._logger

    def __exit__(self, *_: Any) -> None:
        self._logger.clear_context()


# ---------------------------------------------------------------------------
# 全局初始化 & 导出
# ---------------------------------------------------------------------------

_log_initialized = False


def _ensure_logging_initialized() -> None:
    global _log_initialized
    if _log_initialized:
        return

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root.addHandler(handler)

    root.setLevel(logging.INFO)
    _log_initialized = True


def structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器（全局单例配置）.

    推荐在模块级别使用：
        from backend.core.logging.structured_logger import structured_logger
        logger = structured_logger(__name__)
    """
    _ensure_logging_initialized()
    return StructuredLogger(name)
