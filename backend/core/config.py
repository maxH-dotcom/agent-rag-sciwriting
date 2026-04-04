from __future__ import annotations

import os
from pathlib import Path


RUNTIME_DIR = Path(".runtime")
TASK_STORE_PATH = RUNTIME_DIR / "tasks.json"
CHECKPOINT_STORE_PATH = RUNTIME_DIR / "checkpoints.json"
TASK_REPOSITORY_BACKEND = os.environ.get("TASK_REPOSITORY_BACKEND", "file")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
ORCHESTRATION_BACKEND = os.environ.get("ORCHESTRATION_BACKEND", "custom")
