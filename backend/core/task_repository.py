from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from backend.core.config import REDIS_URL, RUNTIME_DIR, TASK_REPOSITORY_BACKEND, TASK_STORE_PATH


class TaskRepository(Protocol):
    backend_name: str

    def load_all(self) -> dict[str, dict[str, Any]]:
        ...

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        ...


class FileTaskRepository:
    backend_name = "file"

    def __init__(self, path: Path) -> None:
        self.path = path

    def load_all(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class RedisTaskRepository:
    backend_name = "redis"

    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("redis 依赖未安装，无法启用 Redis 持久化。") from exc

        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key = "research_assistant:tasks"

    def load_all(self) -> dict[str, dict[str, Any]]:
        payload = self.redis.get(self.key)
        return json.loads(payload) if payload else {}

    def save_all(self, tasks: dict[str, dict[str, Any]]) -> None:
        self.redis.set(self.key, json.dumps(tasks, ensure_ascii=False))


def create_task_repository() -> TaskRepository:
    if TASK_REPOSITORY_BACKEND == "redis":
        try:
            return RedisTaskRepository(REDIS_URL)
        except Exception:
            return FileTaskRepository(TASK_STORE_PATH)
    return FileTaskRepository(TASK_STORE_PATH)
