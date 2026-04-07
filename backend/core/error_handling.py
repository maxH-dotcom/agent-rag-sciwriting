"""错误分类 + 重试机制（Phase 2）."""
from __future__ import annotations

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

# ---------------------------------------------------------------------------
# 错误分类
# ---------------------------------------------------------------------------


class ErrorSeverity(str, Enum):
    RETRYABLE = "retryable"  # 可重试（有退避）
    NON_RETRYABLE = "non_retryable"  # 不可重试（用户需修正代码/输入）
    FATAL = "fatal"  # 致命错误（任务直接终止）


@dataclass
class ErrorInfo:
    severity: ErrorSeverity
    category: str  # network | llm | resource | code | sandbox | system | unknown
    message: str
    retry_after_ms: int | None = None  # None = 用 base_delay


# 错误分类表：Exception type name → ErrorInfo
ERROR_CLASSIFICATION: dict[str, ErrorInfo] = {
    # ---- 网络错误（可重试）----
    "ConnectionError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="网络连接失败",
        retry_after_ms=1000,
    ),
    "TimeoutError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="请求超时",
        retry_after_ms=2000,
    ),
    "HTTPError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="HTTP 请求失败",
        retry_after_ms=1000,
    ),
    "SSLError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="SSL 错误",
        retry_after_ms=2000,
    ),
    "gaierror": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="network",
        message="DNS/网络地址错误",
        retry_after_ms=3000,
    ),
    # ---- LLM 错误（可重试）----
    "RateLimitError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="llm",
        message="LLM 速率限制",
        retry_after_ms=5000,
    ),
    "APIError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="llm",
        message="LLM API 错误",
        retry_after_ms=2000,
    ),
    "APITimeoutError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="llm",
        message="LLM API 超时",
        retry_after_ms=3000,
    ),
    # ---- 资源错误（可重试，有冷却）----
    "MemoryError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="resource",
        message="内存不足",
        retry_after_ms=10000,
    ),
    "OSError": ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="resource",
        message="系统资源错误",
        retry_after_ms=5000,
    ),
    # ---- 代码错误（不可重试）----
    "SyntaxError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="代码语法错误",
    ),
    "IndentationError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="缩进错误",
    ),
    "NameError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="变量未定义",
    ),
    "TypeError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="类型错误",
    ),
    "ValueError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="值错误",
    ),
    "KeyError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="字典键不存在",
    ),
    "FileNotFoundError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="文件不存在",
    ),
    "PermissionError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="code",
        message="权限错误",
    ),
    # ---- 沙箱错误（不可重试）----
    "SandboxTimeout": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="sandbox",
        message="沙箱执行超时",
    ),
    "SandboxMemoryLimit": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="sandbox",
        message="沙箱内存超限",
    ),
    "SandboxSecurityError": ErrorInfo(
        severity=ErrorSeverity.NON_RETRYABLE,
        category="sandbox",
        message="沙箱安全检查未通过",
    ),
    # ---- 致命错误（任务终止）----
    "FatalError": ErrorInfo(
        severity=ErrorSeverity.FATAL,
        category="system",
        message="系统致命错误",
    ),
    "TaskAbortError": ErrorInfo(
        severity=ErrorSeverity.FATAL,
        category="system",
        message="任务被强制中止",
    ),
}


def classify_error(error: BaseException | type[BaseException]) -> ErrorInfo:
    """
    将异常分类到 ErrorInfo。

    Args:
        error: 异常实例或异常类型

    Returns:
        ErrorInfo，始终返回有效分类（未知错误走 RETRYABLE fallback）
    """
    # 支持传入类型或实例
    error_type_name = (
        error.__class__.__name__
        if isinstance(error, BaseException)
        else (error.__name__ if isinstance(error, type) else type(error).__name__)
    )

    if error_type_name in ERROR_CLASSIFICATION:
        return ERROR_CLASSIFICATION[error_type_name]

    # 根据错误消息做二级推断
    error_msg = str(error).lower()
    if any(kw in error_msg for kw in ["timeout", "timed out", "超时"]):
        return ErrorInfo(
            severity=ErrorSeverity.RETRYABLE,
            category="network",
            message=f"超时错误（{error_type_name}）",
            retry_after_ms=3000,
        )
    if any(kw in error_msg for kw in ["memory", "内存"]):
        return ErrorInfo(
            severity=ErrorSeverity.RETRYABLE,
            category="resource",
            message=f"资源错误（{error_type_name}）",
            retry_after_ms=10000,
        )

    # 默认：未知但可重试一次
    return ErrorInfo(
        severity=ErrorSeverity.RETRYABLE,
        category="unknown",
        message=f"未知错误: {error_type_name}",
        retry_after_ms=1000,
    )


# ---------------------------------------------------------------------------
# 重试装饰器
# ---------------------------------------------------------------------------


def with_retry(
    max_attempts: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 30000,
    logger: logging.Logger | None = None,
):
    """
    带指数退避的重试装饰器（async / sync 通用）。

    使用示例：
        @with_retry(max_attempts=3, base_delay_ms=1000)
        async def call_llm(prompt: str) -> str:
            ...

        @with_retry(max_attempts=2, base_delay_ms=500)
        def parse_csv(path: str) -> pd.DataFrame:
            ...

    参数：
        max_attempts: 最大尝试次数（含首次，即 3 次 = 首次 + 2 次重试）
        base_delay_ms: 基础退避延迟（毫秒），每次重试翻倍
        max_delay_ms: 最大延迟上限
        logger: 可选 logger，用于打印重试日志
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # ---- sync 版本 ----
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: BaseException | None = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    error_info = classify_error(exc)

                    if error_info.severity in (
                        ErrorSeverity.NON_RETRYABLE,
                        ErrorSeverity.FATAL,
                    ):
                        raise

                    if attempt >= max_attempts - 1:
                        break

                    delay = error_info.retry_after_ms or base_delay_ms
                    delay = min(delay * (2**attempt), max_delay_ms)

                    _log_retry(
                        logger,
                        func,
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    _sync_sleep(delay / 1000)

            # 所有重试耗尽
            if last_error is not None:
                raise last_error
            raise RuntimeError(f"{func.__name__}: all retry attempts failed")

        # ---- async 版本 ----
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: BaseException | None = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)  # type: ignore[operator]
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    error_info = classify_error(exc)

                    if error_info.severity in (
                        ErrorSeverity.NON_RETRYABLE,
                        ErrorSeverity.FATAL,
                    ):
                        raise

                    if attempt >= max_attempts - 1:
                        break

                    delay = error_info.retry_after_ms or base_delay_ms
                    delay = min(delay * (2**attempt), max_delay_ms)

                    _log_retry(
                        logger,
                        func,
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay / 1000)

            if last_error is not None:
                raise last_error
            raise RuntimeError(f"{func.__name__}: all retry attempts failed")

        # 根据函数类型返回对应 wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

_SYNC_SLEEP = getattr(__import__("time"), "sleep")  # 避免 import time 污染签名


def _sync_sleep(seconds: float) -> None:
    _SYNC_SLEEP(seconds)


def _log_retry(
    logger: logging.Logger | None,
    func: Callable,
    attempt: int,
    max_attempts: int,
    exc: BaseException,
    delay_ms: int,
) -> None:
    msg = (
        f"[{func.__qualname__}] Attempt {attempt}/{max_attempts} failed "
        f"({type(exc).__name__}): {exc!s}. "
        f"Retrying in {delay_ms}ms..."
    )
    if logger:
        logger.warning(msg)
    else:
        import sys
        print(f"WARNING: {msg}", file=sys.stderr)
