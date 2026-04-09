import tempfile
import unittest
from pathlib import Path
import sys
import csv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agents.orchestrator.main_graph import ResearchAssistantOrchestrator
from backend.agents.tools.literature_search import retrieve_literature
from backend.core.file_validation import FileValidationError, validate_user_files
from backend.core.checkpoint_repository import FileCheckpointRepository
from backend.core.task_repository import FileTaskRepository
from backend.core.task_store import TaskStore


class OrchestratorSmokeTest(unittest.TestCase):
    def test_interrupt_sequence(self) -> None:
        orchestrator = ResearchAssistantOrchestrator()
        state = orchestrator.create_initial_state(
            task_id="task_demo",
            task_type="analysis",
            user_query="我想分析农业产值对碳排放的影响，同时控制农药使用量",
            data_files=[],
            paper_files=[],
        )

        state = orchestrator.run_until_pause(state)
        self.assertEqual(state["current_node"], "data_mapping")
        self.assertEqual(state["status"], "interrupted")

        for expected_node in ["literature", "novelty", "analysis", "brief"]:
            state["human_decision"] = {"decision": "approved", "payload": {}}
            state = orchestrator.run_until_pause(state, resume=True)
            self.assertEqual(state["current_node"], expected_node)
            self.assertEqual(state["status"], "interrupted")

        state["human_decision"] = {"decision": "approved", "payload": {}}
        state = orchestrator.run_until_pause(state, resume=True)
        self.assertEqual(state["current_node"], "writing")
        self.assertEqual(state["status"], "done")


class TaskStorePersistenceTest(unittest.TestCase):
    def test_store_persists_task_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "tasks.json"
            checkpoint_path = Path(temp_dir) / "checkpoints.json"
            store = TaskStore(FileTaskRepository(store_path), FileCheckpointRepository(checkpoint_path))
            data_path = Path(temp_dir) / "demo.csv"
            paper_path = Path(temp_dir) / "paper.pdf"
            with open(data_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["年份", "地区", "碳排放总量"])
                writer.writerow([2024, "杭州", 10])
            paper_path.write_text("paper body", encoding="utf-8")

            request = type(
                "Req",
                (),
                {
                    "task_type": "analysis",
                    "user_query": "测试任务",
                    "data_files": [str(data_path.resolve())],
                    "paper_files": [str(paper_path.resolve())],
                },
            )()
            task = store.create_task(request)

            reloaded_store = TaskStore(FileTaskRepository(store_path), FileCheckpointRepository(checkpoint_path))
            reloaded_task = reloaded_store.get_task(task["task_id"])

            self.assertIsNotNone(reloaded_task)
            self.assertEqual(reloaded_task["data_files"], [str(data_path.resolve())])
            self.assertEqual(reloaded_task["paper_files"], [str(paper_path.resolve())])
            self.assertTrue(reloaded_task["created_at"])
            self.assertEqual(reloaded_task["history"][0]["event"], "task_created")

    def test_modified_continue_updates_mapping_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "tasks.json"
            store = TaskStore(
                FileTaskRepository(store_path),
                FileCheckpointRepository(Path(temp_dir) / "checkpoints.json"),
            )
            request = type(
                "Req",
                (),
                {
                    "task_type": "analysis",
                    "user_query": "测试任务",
                    "data_files": [],
                    "paper_files": [],
                },
            )()
            task = store.create_task(request)

            response = store.continue_task(
                task["task_id"],
                type(
                    "Req",
                    (),
                    {
                        "decision": "modified",
                        "payload": {
                            "dependent_var": "自定义因变量",
                            "time_column": "年份",
                        },
                    },
                )(),
            )

            # modified 后跳到 literature（新增了 literature 中断点）
            self.assertEqual(response["current_node"], "literature")
            self.assertEqual(response["result"]["human_decision"]["decision"], "modified")
            self.assertEqual(response["result"]["data_mapping_result"]["dependent_var"], "自定义因变量")
            self.assertEqual(response["history"][-1]["event"], "task_continued")

    def test_modified_continue_updates_literature_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "tasks.json"
            store = TaskStore(
                FileTaskRepository(store_path),
                FileCheckpointRepository(Path(temp_dir) / "checkpoints.json"),
            )
            request = type(
                "Req",
                (),
                {
                    "task_type": "analysis",
                    "user_query": "测试任务",
                    "data_files": [],
                    "paper_files": [],
                },
            )()
            task = store.create_task(request)

            store.continue_task(
                task["task_id"],
                type("Req", (), {"decision": "approved", "payload": {}})(),
            )
            literature_task = store.get_task(task["task_id"])
            references = literature_task["result"]["literature_result"]["references"]

            response = store.continue_task(
                task["task_id"],
                type(
                    "Req",
                    (),
                    {
                        "decision": "modified",
                        "payload": {
                            "references": references[:1],
                            "selected_reference_ids": [references[0]["reference_id"]],
                        },
                    },
                )(),
            )

            self.assertEqual(response["current_node"], "novelty")
            self.assertEqual(len(response["result"]["literature_result"]["references"]), 1)
            self.assertEqual(
                response["result"]["literature_result"]["selected_reference_ids"],
                [references[0]["reference_id"]],
            )

    def test_modified_continue_updates_novelty_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "tasks.json"
            store = TaskStore(
                FileTaskRepository(store_path),
                FileCheckpointRepository(Path(temp_dir) / "checkpoints.json"),
            )
            request = type(
                "Req",
                (),
                {
                    "task_type": "analysis",
                    "user_query": "测试任务",
                    "data_files": [],
                    "paper_files": [],
                },
            )()
            task = store.create_task(request)

            store.continue_task(
                task["task_id"],
                type("Req", (), {"decision": "approved", "payload": {}})(),
            )
            store.continue_task(
                task["task_id"],
                type("Req", (), {"decision": "approved", "payload": {}})(),
            )

            response = store.continue_task(
                task["task_id"],
                type(
                    "Req",
                    (),
                    {
                        "decision": "modified",
                        "payload": {
                            "recommended_direction": {
                                "summary": "优先做更保守的固定效应验证。",
                                "why": "先拿到稳定基线，再讨论扩展模型。",
                            },
                            "differentiation_points": [
                                "人工保留关键审核节点",
                                "先沉淀可复现基线流程",
                            ],
                        },
                    },
                )(),
            )

            self.assertEqual(response["current_node"], "analysis")
            self.assertEqual(
                response["result"]["novelty_result"]["recommended_direction"]["summary"],
                "优先做更保守的固定效应验证。",
            )
            self.assertEqual(
                response["result"]["novelty_result"]["differentiation_points"][0],
                "人工保留关键审核节点",
            )

    def test_abort_appends_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "tasks.json"
            store = TaskStore(
                FileTaskRepository(store_path),
                FileCheckpointRepository(Path(temp_dir) / "checkpoints.json"),
            )
            request = type(
                "Req",
                (),
                {
                    "task_type": "analysis",
                    "user_query": "测试任务",
                    "data_files": [],
                    "paper_files": [],
                },
            )()
            task = store.create_task(request)
            aborted = store.abort_task(task["task_id"], "manual_stop")

            self.assertEqual(aborted["status"], "aborted")
            self.assertEqual(aborted["history"][-1]["event"], "task_aborted")

    def test_file_repository_backend_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = FileTaskRepository(Path(temp_dir) / "tasks.json")
            checkpoint_repository = FileCheckpointRepository(Path(temp_dir) / "checkpoints.json")
            store = TaskStore(repository, checkpoint_repository)
            self.assertEqual(store.repository.backend_name, "file")
            self.assertEqual(store.checkpoint_repository.backend_name, "file")


class LiteratureIntegrationSmokeTest(unittest.TestCase):
    def test_literature_result_contains_source_stats(self) -> None:
        result = retrieve_literature("碳排放 面板数据 固定效应模型", paper_files=["/tmp/demo.pdf"])
        self.assertIn("source_stats", result)
        self.assertIn("quality_score", result)
        self.assertGreaterEqual(result["source_stats"]["fallback"], 1)


class FileValidationTest(unittest.TestCase):
    def test_validate_user_files_accepts_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "demo.csv"
            paper_path = Path(temp_dir) / "paper.pdf"
            with open(data_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["年份", "地区", "碳排放总量"])
                writer.writerow([2024, "杭州", 10])
            paper_path.write_text("paper body", encoding="utf-8")

            manifest = validate_user_files([str(data_path)], [str(paper_path)])
            self.assertEqual(manifest["data_files"][0]["suffix"], ".csv")
            self.assertEqual(manifest["paper_files"][0]["suffix"], ".pdf")

    def test_validate_user_files_rejects_relative_path(self) -> None:
        with self.assertRaises(FileValidationError):
            validate_user_files(["relative.csv"], [])


if __name__ == "__main__":
    unittest.main()
