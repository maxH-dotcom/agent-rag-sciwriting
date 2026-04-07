import csv
import json
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
        self.excel_path = temp_path / "demo.xlsx"
        self.paper_path.write_text("paper body", encoding="utf-8")

        try:
            import pandas as pd  # type: ignore
        except ModuleNotFoundError:
            self.has_pandas = False
        else:
            self.has_pandas = True
            pd.DataFrame(
                [{"年份": 2024, "地区": "杭州", "碳排放总量": 10, "农业产值": 5}]
            ).to_excel(self.excel_path, index=False)

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

    # ---- 文件上传测试 ----

    def test_upload_csv_auto_kind(self) -> None:
        """上传 CSV 文件，auto 模式应识别为 data。"""
        response = self.client.post(
            "/upload",
            files=[("files", ("test.csv", b"a,b,c\n1,2,3", "text/csv"))],
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["files"]), 1)
        f = data["files"][0]
        self.assertEqual(f["name"], "test.csv")
        self.assertEqual(f["suffix"], ".csv")
        self.assertEqual(f["kind"], "data")
        self.assertGreater(f["size_bytes"], 0)
        self.assertTrue(Path(f["path"]).exists())

    def test_upload_pdf_auto_kind(self) -> None:
        """上传 PDF 文件，auto 模式应识别为 paper。"""
        response = self.client.post(
            "/upload",
            files=[("files", ("paper.pdf", b"%PDF-1.4 fake", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 200)
        f = response.json()["files"][0]
        self.assertEqual(f["kind"], "paper")
        self.assertEqual(f["suffix"], ".pdf")

    def test_upload_multiple_files(self) -> None:
        """同时上传多个文件。"""
        response = self.client.post(
            "/upload",
            files=[
                ("files", ("a.csv", b"x,y\n1,2", "text/csv")),
                ("files", ("b.pdf", b"%PDF", "application/pdf")),
            ],
        )
        self.assertEqual(response.status_code, 200)
        files = response.json()["files"]
        self.assertEqual(len(files), 2)
        kinds = {f["kind"] for f in files}
        self.assertEqual(kinds, {"data", "paper"})

    def test_upload_explicit_kind(self) -> None:
        """指定 kind=data 上传 CSV。"""
        response = self.client.post(
            "/upload?kind=data",
            files=[("files", ("d.csv", b"col\n1", "text/csv"))],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["files"][0]["kind"], "data")

    def test_upload_unsupported_suffix_returns_400(self) -> None:
        """上传不支持的文件类型应返回 400。"""
        response = self.client.post(
            "/upload",
            files=[("files", ("script.py", b"print(1)", "text/plain"))],
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_kind_mismatch_returns_400(self) -> None:
        """指定 kind=data 但上传 PDF 应返回 400。"""
        response = self.client.post(
            "/upload?kind=data",
            files=[("files", ("paper.pdf", b"%PDF", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_then_create_task(self) -> None:
        """上传文件后用返回路径创建任务的完整链路。"""
        upload_resp = self.client.post(
            "/upload",
            files=[("files", ("demo.csv", self.data_path.read_bytes(), "text/csv"))],
        )
        self.assertEqual(upload_resp.status_code, 200)
        uploaded_path = upload_resp.json()["files"][0]["path"]

        task_resp = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "测试上传链路",
                "data_files": [uploaded_path],
                "paper_files": [],
            },
        )
        self.assertEqual(task_resp.status_code, 200)
        self.assertEqual(task_resp.json()["status"], "interrupted")

    def test_task_stream_returns_sse_payload(self) -> None:
        create_response = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "我想分析农业产值对碳排放的影响",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [],
            },
        )
        self.assertEqual(create_response.status_code, 200)
        task_id = create_response.json()["task_id"]

        with self.client.stream("GET", f"/tasks/{task_id}/stream?once=true") as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"].split(";")[0], "text/event-stream")
            lines = []
            for line in response.iter_lines():
                if not line:
                    break
                lines.append(line)

        self.assertTrue(any(line.startswith("event: task") for line in lines))
        data_lines = [line for line in lines if line.startswith("data: ")]
        self.assertTrue(data_lines)
        payload = json.loads(data_lines[0][6:])
        self.assertEqual(payload["task_id"], task_id)
        self.assertEqual(payload["status"], "interrupted")

    def test_create_task_with_excel_file(self) -> None:
        if not self.has_pandas:
            self.skipTest("pandas/openpyxl unavailable")

        response = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "测试 Excel 数据文件",
                "data_files": [str(self.excel_path.resolve())],
                "paper_files": [],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "interrupted")
        columns = payload["result"]["data_mapping_result"]["columns"]
        self.assertIn("年份", columns)
        self.assertIn("农业产值", columns)


if __name__ == "__main__":
    unittest.main()
