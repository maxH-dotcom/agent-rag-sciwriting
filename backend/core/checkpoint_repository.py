from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from backend.core.config import CHECKPOINT_STORE_PATH, REDIS_URL, RUNTIME_DIR, TASK_REPOSITORY_BACKEND


class CheckpointRepository(Protocol):
    backend_name: str

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        ...

    def save_all(self, checkpoints: dict[str, list[dict[str, Any]]]) -> None:
        ...


class FileCheckpointRepository:
    backend_name = "file"

    def __init__(self, path: Path) -> None:
        self.path = path

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save_all(self, checkpoints: dict[str, list[dict[str, Any]]]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(checkpoints, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class RedisCheckpointRepository:
    backend_name = "redis"

    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("redis 依赖未安装，无法启用 Redis checkpoint。") from exc

        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key = "research_assistant:checkpoints"

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        payload = self.redis.get(self.key)
        return json.loads(payload) if payload else {}

    def save_all(self, checkpoints: dict[str, list[dict[str, Any]]]) -> None:
        self.redis.set(self.key, json.dumps(checkpoints, ensure_ascii=False))


def create_checkpoint_repository() -> CheckpointRepository:
    if TASK_REPOSITORY_BACKEND == "redis":
        try:
            return RedisCheckpointRepository(REDIS_URL)
        except Exception:
            return FileCheckpointRepository(CHECKPOINT_STORE_PATH)
    return FileCheckpointRepository(CHECKPOINT_STORE_PATH)
