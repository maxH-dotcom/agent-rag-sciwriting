import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.checkpoint_repository import FileCheckpointRepository
from backend.core.task_repository import FileTaskRepository
from backend.core.task_store import TaskStore


class ApiLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise unittest.SkipTest(f"fastapi test client unavailable: {exc}")

        cls._test_client_cls = TestClient

    def setUp(self) -> None:
        from backend.main import app
        from backend.api import routes

        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.data_path = temp_path / "demo.csv"
        self.paper_path = temp_path / "paper.pdf"
        with open(self.data_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["年份", "地区", "碳排放总量", "农业产值"])
            writer.writerow([2024, "杭州", 10, 5])
        self.paper_path.write_text("paper body", encoding="utf-8")

        self.original_store = routes.store
        routes.store = TaskStore(
            repository=FileTaskRepository(temp_path / "tasks.json"),
            checkpoint_repository=FileCheckpointRepository(temp_path / "checkpoints.json"),
        )
        self.client = self._test_client_cls(app)

    def tearDown(self) -> None:
        from backend.api import routes

        routes.store = self.original_store
        self.temp_dir.cleanup()

    def test_index_and_healthz(self) -> None:
        root_response = self.client.get("/")
        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(root_response.json()["health"], "/healthz")

        health_response = self.client.get("/healthz")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json()["status"], "ok")

        runtime_response = self.client.get("/system/runtime")
        self.assertEqual(runtime_response.status_code, 200)
        self.assertIn("effective_backend", runtime_response.json())

    def test_task_lifecycle_endpoints(self) -> None:
        create_response = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "我想分析农业产值对碳排放的影响",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [str(self.paper_path.resolve())],
            },
        )
        self.assertEqual(create_response.status_code, 200)
        task = create_response.json()
        task_id = task["task_id"]
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["current_node"], "data_mapping")

        fetch_response = self.client.get(f"/tasks/{task_id}")
        self.assertEqual(fetch_response.status_code, 200)
        self.assertEqual(fetch_response.json()["task_id"], task_id)

        history_response = self.client.get(f"/tasks/{task_id}/history")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()["history"][0]["event"], "task_created")

        continue_response = self.client.post(
            f"/tasks/{task_id}/continue",
            json={
                "decision": "modified",
                "payload": {"dependent_var": "自定义因变量"},
            },
        )
        self.assertEqual(continue_response.status_code, 200)
        continued = continue_response.json()
        self.assertEqual(continued["current_node"], "literature")
        self.assertEqual(
            continued["result"]["data_mapping_result"]["dependent_var"],
            "自定义因变量",
        )

        checkpoint_response = self.client.get(f"/tasks/{task_id}/checkpoints")
        self.assertEqual(checkpoint_response.status_code, 200)
        self.assertGreaterEqual(len(checkpoint_response.json()["checkpoints"]), 2)

        abort_response = self.client.post(
            f"/tasks/{task_id}/abort",
            json={"reason": "manual_stop"},
        )
        self.assertEqual(abort_response.status_code, 200)
        self.assertEqual(abort_response.json()["status"], "aborted")

    def test_invalid_file_returns_400(self) -> None:
        response = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "测试错误路径",
                "data_files": ["/tmp/not_exists.csv"],
                "paper_files": [],
            },
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
