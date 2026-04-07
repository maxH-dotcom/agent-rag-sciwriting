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

# 用户配置路径
CONFIG_DIR = Path.home() / ".research_assistant"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE_PATH = CONFIG_DIR / "config.json"

# 沙箱配置
DEFAULT_SANDBOX_TIMEOUT = int(os.environ.get("DEFAULT_SANDBOX_TIMEOUT", "60"))
MAX_OUTPUT_SIZE = int(os.environ.get("MAX_OUTPUT_SIZE", str(1_000_000)))


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


def get_settings() -> dict:
    """获取当前配置."""
    if CONFIG_FILE_PATH.exists():
        try:
            return json.loads(CONFIG_FILE_PATH.read_text())
        except Exception:
            pass
    return {
        "preferred_model": "auto",
        "sandbox_timeout": DEFAULT_SANDBOX_TIMEOUT,
        "max_output_size": MAX_OUTPUT_SIZE,
        "auto_convert_year_column": True,
        "zotero_api_key": ZOTERO_API_KEY,
    }


def update_settings(updates: dict) -> dict:
    """更新配置 (仅支持特定字段)."""
    config = get_settings()
    allowed_fields = {
        "preferred_model",
        "sandbox_timeout",
        "max_output_size",
        "auto_convert_year_column",
        "default_method_preference",
    }
    for key, value in updates.items():
        if key in allowed_fields:
            config[key] = value
    try:
        CONFIG_FILE_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    except Exception:
        pass
    return config
