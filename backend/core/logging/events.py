"""结构化日志事件类型常量（Phase 2）."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# 节点事件
# ---------------------------------------------------------------------------
NODE_STARTED = "node_started"
NODE_COMPLETED = "node_completed"
NODE_FAILED = "node_failed"
NODE_INTERRUPTED = "node_interrupted"
NODE_RESUMED = "node_resumed"

# ---------------------------------------------------------------------------
# 工具事件
# ---------------------------------------------------------------------------
TOOL_CALLED = "tool_called"
TOOL_COMPLETED = "tool_completed"
TOOL_FAILED = "tool_failed"

# ---------------------------------------------------------------------------
# 任务事件
# ---------------------------------------------------------------------------
TASK_CREATED = "task_created"
TASK_STARTED = "task_started"
TASK_COMPLETED = "task_completed"
TASK_FAILED = "task_failed"
TASK_INTERRUPTED = "task_interrupted"
TASK_RESUMED = "task_resumed"
TASK_ABORTED = "task_aborted"

# ---------------------------------------------------------------------------
# 用户交互事件
# ---------------------------------------------------------------------------
HUMAN_APPROVED = "human_approved"
HUMAN_REJECTED = "human_rejected"
HUMAN_FEEDBACK = "human_feedback"
HUMAN_MODIFIED = "human_modified"

# ---------------------------------------------------------------------------
# 性能事件
# ---------------------------------------------------------------------------
LATENCY_WARNING = "latency_warning"
MEMORY_WARNING = "memory_warning"
RETRY_ATTEMPT = "retry_attempt"
CHECKPOINT_SAVED = "checkpoint_saved"
CHECKPOINT_RESTORED = "checkpoint_restored"
