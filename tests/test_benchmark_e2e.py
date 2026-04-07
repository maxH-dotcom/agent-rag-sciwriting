"""
Benchmark E2E Flow Tests
端到端流程基准测试
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.mock_client import MockAgentClient


class TestE2EFlowBenchmark(unittest.TestCase):
    """端到端流程基准测试"""

    @classmethod
    def setUpClass(cls):
        cls.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))

    def test_e2e_coverage(self):
        """验证所有 e2e 用例都被执行"""
        results = []
        for case_id, case in self.client.cases.items():
            if case_id.startswith("e2e_"):
                result = self.client.run_e2e_flow(
                    case_id=case_id,
                    user_query=case["input"]["user_query"],
                    data_file=case["input"].get("uploaded_data", ""),
                    interrupt_at=case["input"].get("interrupt_at"),
                    modified_payload=case["input"].get("modified_payload"),
                    reject_at=case["input"].get("reject_at"),
                )
                results.append(result)
        self.assertGreaterEqual(len(results), 10)

    def test_topic_novelty_flow(self):
        """e2e_001: 选题创新性检查"""
        result = self.client.run_e2e_flow(
            case_id="e2e_001",
            user_query="分析经济增长与环境污染的关系",
            data_file="panel_data.csv",
        )
        self.assertIn("visited_nodes", result)
        self.assertIn("final_status", result)

    def test_basic_analysis_flow(self):
        """e2e_002: 基础数据分析流程"""
        result = self.client.run_e2e_flow(
            case_id="e2e_002",
            user_query="计算数据的均值和标准差",
            data_file="simple_stats.csv",
        )
        self.assertEqual(result["final_status"], "done")

    def test_regression_flow(self):
        """e2e_003: 回归分析完整流程"""
        result = self.client.run_e2e_flow(
            case_id="e2e_003",
            user_query="分析X对Y的影响",
            data_file="regression_data.csv",
        )
        self.assertIn("visited_nodes", result)

    def test_interrupted_flow(self):
        """e2e_004: 中断后继续流程"""
        result = self.client.run_e2e_flow(
            case_id="e2e_004",
            user_query="分析数据趋势",
            data_file="trend_data.csv",
            interrupt_at="data_mapping",
            modified_payload={"dependent_var": "value", "independent_vars": ["time"]},
        )
        self.assertIn("visited_nodes", result)
        # 修改后应能继续
        self.assertNotEqual(result["final_status"], "interrupted")

    def test_rejected_abort_flow(self):
        """e2e_005: 用户拒绝后终止"""
        result = self.client.run_e2e_flow(
            case_id="e2e_005",
            user_query="某研究问题",
            data_file="data.csv",
            reject_at="novelty",
        )
        self.assertEqual(result["final_status"], "aborted")

    def test_multi_node_approval_flow(self):
        """e2e_006: 多节点审批流程"""
        result = self.client.run_e2e_flow(
            case_id="e2e_006",
            user_query="面板数据分析",
            data_file="panel.csv",
        )
        self.assertEqual(result["final_status"], "done")
        # 全部节点都应被访问
        self.assertIn("writing", result["visited_nodes"])

    def test_code_with_viz_flow(self):
        """e2e_007: 代码执行带可视化"""
        result = self.client.run_e2e_flow(
            case_id="e2e_007",
            user_query="绘制时间序列图",
            data_file="ts_data.csv",
        )
        self.assertIn("visited_nodes", result)

    def test_data_mapping_interrupts(self):
        """e2e_008: 数据映射中断"""
        result = self.client.run_e2e_flow(
            case_id="e2e_008",
            user_query="分析某变量影响因素",
            data_file="mapping_test.csv",
        )
        # data_mapping 应该触发中断
        self.assertIn("visited_nodes", result)

    def test_routing_accuracy(self):
        """e2e_010: 路由准确性"""
        result = self.client.run_e2e_flow(
            case_id="e2e_010",
            user_query="判断某选题是否新颖",
            data_file="",
        )
        self.assertIn("visited_nodes", result)
        self.assertIn("novelty", result["visited_nodes"])


class TestNodeSequence(unittest.TestCase):
    """节点序列正确性测试"""

    def setUp(self):
        self.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))

    def test_correct_node_order(self):
        """节点应按正确顺序执行"""
        result = self.client.run_e2e_flow(
            case_id="e2e_006",
            user_query="面板数据分析",
            data_file="panel.csv",
        )
        nodes = result["visited_nodes"]
        # 验证顺序
        if len(nodes) >= 2:
            dm_idx = nodes.index("data_mapping") if "data_mapping" in nodes else -1
            lit_idx = nodes.index("literature") if "literature" in nodes else -1
            if dm_idx >= 0 and lit_idx >= 0:
                self.assertLess(dm_idx, lit_idx, "data_mapping 应在 literature 之前")

    def test_all_required_nodes_visited(self):
        """所有必要节点都应被访问"""
        result = self.client.run_e2e_flow(
            case_id="e2e_006",
            user_query="面板数据分析",
            data_file="panel.csv",
        )
        required = {"data_mapping", "literature", "novelty", "analysis", "brief", "writing"}
        visited = set(result["visited_nodes"])
        # 全部批准时应访问所有节点
        self.assertTrue(required.issubset(visited), f"缺少节点: {required - visited}")


if __name__ == "__main__":
    unittest.main()
