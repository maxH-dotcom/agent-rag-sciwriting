from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_history_event(event: str, node: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event": event,
        "node": node,
        "timestamp": now_iso(),
        "detail": detail or {},
    }

