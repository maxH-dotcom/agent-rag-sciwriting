"""基于标准 Redis string 命令的 LangGraph checkpointer，不依赖 RedisJSON 模块。"""
from __future__ import annotations

import json
from typing import Any, Iterator, Optional, Tuple

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.serde.base import SerializerProtocol


class JsonSerializer:
    """使用标准 JSON 序列化/反序列化。"""

    def loads(self, data: str) -> dict[str, Any]:
        return json.loads(data)

    def dumps(self, data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False)


class RedisStringCheckpointer(BaseCheckpointSaver):
    """使用 Redis SET/GET 存储 checkpoint，不依赖 RedisJSON 模块。"""

    def __init__(
        self,
        redis_url: str,
        *,
        serializer: SerializerProtocol | None = None,
    ) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:
            raise RuntimeError("redis 依赖未安装") from exc

        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.serde = serializer or JsonSerializer()

    def _key(self, thread_id: str, checkpoint_ns: str) -> str:
        return f"langgraph:checkpoint:{thread_id}:{checkpoint_ns}"

    def get(self, config: dict[str, Any]) -> Optional[dict[str, Any]]:
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        if not thread_id:
            return None
        key = self._key(thread_id, checkpoint_ns)
        data = self.redis.get(key)
        if not data:
            return None
        return self.serde.loads(data)

    def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        if not thread_id:
            raise ValueError("thread_id is required")
        key = self._key(thread_id, checkpoint_ns)
        self.redis.set(key, self.serde.dumps(checkpoint))
        # 返回新 config
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint.get("id", ""),
            }
        }

    def list(
        self,
        config: dict[str, Any],
        *,
        filter: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return
        pattern = f"langgraph:checkpoint:{thread_id}:*"
        for key in self.redis.scan_iter(match=pattern, count=100):
            data = self.redis.get(key)
            if data:
                yield self.serde.loads(data)

    def delete(self, config: dict[str, Any]) -> None:
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        if not thread_id:
            return
        key = self._key(thread_id, checkpoint_ns)
        self.redis.delete(key)
