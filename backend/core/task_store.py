from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any
import uuid

from backend.agents.runtime import create_research_runtime
from backend.core.checkpoint_repository import CheckpointRepository, create_checkpoint_repository
from backend.core.file_validation import validate_user_files
from backend.core.task_history import build_history_event, now_iso
from backend.core.task_mutations import apply_human_payload
from backend.core.task_repository import TaskRepository, create_task_repository

if TYPE_CHECKING:
    from backend.api.schemas import ContinueTaskRequest, CreateTaskRequest


class TaskStore:
    def __init__(
        self,
        repository: TaskRepository | None = None,
        checkpoint_repository: CheckpointRepository | None = None,
    ) -> None:
        self.repository = repository or create_task_repository()
        self.checkpoint_repository = checkpoint_repository or create_checkpoint_repository()
        self.lock = threading.Lock()
        self.orchestrator = create_research_runtime()
        self._tasks: dict[str, dict[str, Any]] = self.repository.load_all()
        self._checkpoints: dict[str, list[dict[str, Any]]] = self.checkpoint_repository.load_all()
        self._load()

    def _load(self) -> None:
        self._tasks = self.repository.load_all()
        self._checkpoints = self.checkpoint_repository.load_all()

    def _save(self) -> None:
        self.repository.save_all(self._tasks)
        self.checkpoint_repository.save_all(self._checkpoints)

    def _append_checkpoint(self, task_id: str, state: dict[str, Any], *, event: str) -> None:
        checkpoints = list(self._checkpoints.get(task_id) or [])
        checkpoints.append(
            {
                "event": event,
                "timestamp": now_iso(),
                "current_node": state.get("current_node"),
                "status": state.get("status"),
                "interrupt_reason": state.get("interrupt_reason"),
                "result_keys": sorted(list((state.get("result") or {}).keys())),
            }
        )
        self._checkpoints[task_id] = checkpoints

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self._tasks.values())[::-1]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.lock:
            return self._tasks.get(task_id)

    def get_checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        with self.lock:
            return list(self._checkpoints.get(task_id) or [])

    def create_task(self, request: "CreateTaskRequest") -> dict[str, Any]:
        with self.lock:
            task_id = f"task_{uuid.uuid4().hex[:10]}"
            created_at = now_iso()
            file_manifest = validate_user_files(request.data_files, request.paper_files)
            state = self.orchestrator.create_initial_state(
                task_id=task_id,
                task_type=request.task_type,
                user_query=request.user_query,
                data_files=request.data_files,
                paper_files=request.paper_files,
                file_manifest=file_manifest,
            )
            final_state = self.orchestrator.run_until_pause(state)
            response = self.orchestrator.to_task_response(final_state)
            response["created_at"] = created_at
            response["updated_at"] = now_iso()
            response["history"] = [
                build_history_event(
                    event="task_created",
                    node=response["current_node"],
                    detail={
                        "status": response["status"],
                        "interrupt_reason": response.get("interrupt_reason"),
                        "validated_files": file_manifest,
                    },
                )
            ]
            self._tasks[task_id] = response
            self._append_checkpoint(task_id, response, event="task_created")
            self._save()
            return response

    def continue_task(self, task_id: str, request: "ContinueTaskRequest") -> dict[str, Any]:
        with self.lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            if task["status"] != "interrupted":
                raise ValueError("Task is not interrupted")
            state = self.orchestrator.from_task_response(task)
            state = apply_human_payload(state, request.payload if request.decision == "modified" else None)
            state["human_decision"] = {
                "decision": request.decision,
                "payload": request.payload,
            }
            final_state = self.orchestrator.run_until_pause(state, resume=True)
            response = self.orchestrator.to_task_response(final_state)
            response["created_at"] = task["created_at"]
            response["updated_at"] = now_iso()
            history = list(task.get("history") or [])
            history.append(
                build_history_event(
                    event="task_continued",
                    node=task["current_node"],
                    detail={
                        "decision": request.decision,
                        "status_after": response["status"],
                        "next_node": response["current_node"],
                    },
                )
            )
            response["history"] = history
            self._tasks[task_id] = response
            self._append_checkpoint(task_id, response, event="task_continued")
            self._save()
            return response

    def abort_task(self, task_id: str, reason: str) -> dict[str, Any]:
        with self.lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            task["status"] = "aborted"
            task["next_action"] = None
            task["interrupt_reason"] = reason
            task["updated_at"] = now_iso()
            history = list(task.get("history") or [])
            history.append(
                build_history_event(
                    event="task_aborted",
                    node=task["current_node"],
                    detail={"reason": reason},
                )
            )
            task["history"] = history
            self._append_checkpoint(task_id, task, event="task_aborted")
            self._save()
            return task


store = TaskStore()
