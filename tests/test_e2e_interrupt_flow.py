"""端到端测试：create → 中断 → modified继续 → 再次中断 → approved继续 → done"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app
from backend.api import routes
from backend.core.checkpoint_repository import FileCheckpointRepository
from backend.core.task_repository import FileTaskRepository
from backend.core.task_store import TaskStore


class E2EInterruptFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._test_client_cls = TestClient

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)

        # 准备真实 CSV 测试文件
        self.data_path = temp_path / "test_data.csv"
        with open(self.data_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["年份", "地区", "碳排放总量", "农业产值", "农药使用量"])
            writer.writerow([2020, "浙江", 10.5, 5.2, 0.8])
            writer.writerow([2021, "浙江", 11.2, 5.8, 0.9])
            writer.writerow([2022, "江苏", 9.8, 4.9, 0.7])

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

    def test_full_interrupt_flow_approved_all_nodes(self) -> None:
        """完整流程：所有节点都 approve，直到 done"""
        # Step 1: 创建任务（停在 data_mapping）
        create_resp = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "我想分析农业产值对碳排放的影响，同时控制农药使用量",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [],
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        task = create_resp.json()
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["current_node"], "data_mapping")
        self.assertEqual(task["interrupt_reason"], "data_mapping_required")

        # 验证 data_mapping 读取了真实 CSV 列
        dm_result = task["result"]["data_mapping_result"]
        self.assertIn("年份", dm_result["columns"])
        self.assertIn("地区", dm_result["columns"])
        self.assertGreater(len(dm_result["preview"]), 0)
        task_id = task["task_id"]

        # Step 2: 继续到 literature（approve data_mapping）
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "approved", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["current_node"], "literature")
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["interrupt_reason"], "literature_review_required")

        # Step 3: 继续到 novelty（approve literature）
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "approved", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["current_node"], "novelty")
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["interrupt_reason"], "novelty_result_ready")

        # Step 4: 继续到 analysis（approve novelty）
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "approved", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["current_node"], "analysis")
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["interrupt_reason"], "code_plan_ready")

        # Step 5: 继续到 brief（approve analysis）
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "approved", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["current_node"], "brief")
        self.assertEqual(task["status"], "interrupted")
        self.assertEqual(task["interrupt_reason"], "brief_ready_for_review")

        # Step 6: 继续到 writing（approve brief）
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "approved", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["current_node"], "writing")
        self.assertEqual(task["status"], "done")
        self.assertIsNotNone(task["result"]["writing_result"])

        # Step 7: 验证 checkpoints 历史
        cp_resp = self.client.get(f"/tasks/{task_id}/checkpoints")
        self.assertGreaterEqual(len(cp_resp.json()["checkpoints"]), 6)

    def test_interrupt_flow_with_modified_payload(self) -> None:
        """中断后用 modified payload 修改数据映射，然后继续"""
        # Step 1: 创建任务
        create_resp = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "分析农业产值与碳排放的关系",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [],
            },
        )
        task = create_resp.json()
        task_id = task["task_id"]

        # Step 2: 用 modified payload 修改映射
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={
                "decision": "modified",
                "payload": {
                    "dependent_var": "碳排放总量",
                    "independent_vars": ["农业产值"],
                    "control_vars": ["农药使用量"],
                },
            },
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        # modified 后跳到 literature（不在 data_mapping 停留）
        self.assertEqual(task["current_node"], "literature")

        # Step 3: approved 后续节点直到 done（literature→novelty→analysis→brief→writing，共4步）
        for i in range(1, 5):
            continue_resp = self.client.post(
                f"/tasks/{task_id}/continue",
                json={"decision": "approved", "payload": {}},
            )
            task = continue_resp.json()
            if task["status"] == "done":
                break

        self.assertEqual(task["status"], "done")
        self.assertEqual(task["current_node"], "writing")

    def test_rejected_decision_aborts(self) -> None:
        """在任意节点 reject 则任务 aborted"""
        # Step 1: 创建任务
        create_resp = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "分析农业产值与碳排放",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [],
            },
        )
        task = create_resp.json()
        task_id = task["task_id"]

        # Step 2: 在 data_mapping 拒绝
        continue_resp = self.client.post(
            f"/tasks/{task_id}/continue",
            json={"decision": "rejected", "payload": {}},
        )
        self.assertEqual(continue_resp.status_code, 200)
        task = continue_resp.json()
        self.assertEqual(task["status"], "aborted")
        self.assertEqual(task["interrupt_reason"], "user_rejected_current_stage")

    def test_abort_mid_pipeline(self) -> None:
        """在任意节点调用 abort，任务立即停止"""
        # Step 1: 创建并走到 literature
        create_resp = self.client.post(
            "/tasks",
            json={
                "task_type": "analysis",
                "user_query": "分析碳排放",
                "data_files": [str(self.data_path.resolve())],
                "paper_files": [],
            },
        )
        task = create_resp.json()
        task_id = task["task_id"]

        # Step 2: approve 到 literature
        self.client.post(f"/tasks/{task_id}/continue", json={"decision": "approved", "payload": {}})
        task = self.client.get(f"/tasks/{task_id}").json()
        self.assertEqual(task["current_node"], "literature")

        # Step 3: abort
        abort_resp = self.client.post(
            f"/tasks/{task_id}/abort",
            json={"reason": "用户主动停止"},
        )
        self.assertEqual(abort_resp.status_code, 200)
        self.assertEqual(abort_resp.json()["status"], "aborted")


if __name__ == "__main__":
    unittest.main()
