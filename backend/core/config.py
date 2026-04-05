from __future__ import annotations

import json
import os
from pathlib import Path


RUNTIME_DIR = Path(".runtime")
TASK_STORE_PATH = RUNTIME_DIR / "tasks.json"
CHECKPOINT_STORE_PATH = RUNTIME_DIR / "checkpoints.json"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(RUNTIME_DIR / "uploads")))
TASK_REPOSITORY_BACKEND = os.environ.get("TASK_REPOSITORY_BACKEND", "file")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
ORCHESTRATION_BACKEND = os.environ.get("ORCHESTRATION_BACKEND", "custom")
LANGGRAPH_CHECKPOINT_BACKEND = os.environ.get("LANGGRAPH_CHECKPOINT_BACKEND", "memory")  # "memory" 或 "redis"（redis 需要 RedisJSON 模块）


def _load_zotero_key() -> str:
    if api_key := os.environ.get("ZOTERO_API_KEY"):
        return api_key
    config_path = Path.home() / ".research_assistant" / "zotero_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text()).get("api_key", "")
        except Exception:
            return ""
    return ""


ZOTERO_API_KEY = _load_zotero_key()
