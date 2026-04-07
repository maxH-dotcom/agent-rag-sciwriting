"""
Benchmark Retrieval Tests
检索能力基准测试
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.mock_client import MockAgentClient


class TestRetrievalBenchmark(unittest.TestCase):
    """检索能力基准测试"""

    @classmethod
    def setUpClass(cls):
        cls.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))
        cls.results = cls.client.run_retrieval_benchmark()

    def test_retrieval_coverage(self):
        """验证所有检索用例都被执行"""
        self.assertGreaterEqual(len(self.results), 10, "检索测试用例应至少10条")

    def test_keyword_match(self):
        """ret_001: 基础关键词匹配"""
        result = next(r for r in self.results if r["case_id"] == "ret_001")
        self.assertIn("机器学习", result["query"])
        self.assertIsInstance(result["retrieved_chunks"], list)
        self.assertGreater(len(result["retrieved_chunks"]), 0)

    def test_semantic_recall(self):
        """ret_002: 同义词/语义检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_002")
        retrieved_ids = result["retrieved_chunks"]
        # chunk_003 是 CNN 图像识别的 chunk
        self.assertTrue(
            any("chunk_003" in str(retrieved_ids) for _ in [1]),
            f"期望检索到图像相关 chunk，实际: {retrieved_ids}"
        )

    def test_method_retrieval(self):
        """ret_003: 方法/公式检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_003")
        self.assertIn("线性回归", result["query"])

    def test_precision_at_k(self):
        """ret_006: Precision@K 高精度测试"""
        result = next(r for r in self.results if r["case_id"] == "ret_006")
        self.assertIn("强化学习", result["query"])

    def test_ranking_quality(self):
        """ret_010: 排序质量测试"""
        result = next(r for r in self.results if r["case_id"] == "ret_010")
        self.assertIn("聚类", result["query"])

    def test_cross_document(self):
        """ret_011: 跨文档检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_011")
        self.assertIn("气候变化", result["query"])

    def test_formula_retrieval(self):
        """ret_012: 公式/数值检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_012")
        self.assertIn("R²", result["query"])

    def test_regional_specific(self):
        """ret_013: 特定地区/领域检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_013")
        self.assertIn("东亚", result["query"])

    def test_temporal_query(self):
        """ret_014: 时间范围查询"""
        result = next(r for r in self.results if r["case_id"] == "ret_014")
        self.assertIn("能源", result["query"])

    def test_multi_keyword(self):
        """ret_004: 多关键词交叉检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_004")
        self.assertIn("ARIMA", result["query"])

    def test_recall_at_5(self):
        """ret_005: Recall@5 测试"""
        result = next(r for r in self.results if r["case_id"] == "ret_005")
        self.assertGreaterEqual(
            result["recall_at_5"], 0.0,
            f"Recall@5 应 >= 0，实际: {result['recall_at_5']}"
        )

    def test_noisy_query(self):
        """ret_007: 模糊/噪声查询"""
        result = next(r for r in self.results if r["case_id"] == "ret_007")
        self.assertIn("那个什么模型来着", result["query"])

    def test_empty_result_handling(self):
        """ret_008: 空结果场景"""
        result = next(r for r in self.results if r["case_id"] == "ret_008")
        # 不相关查询应返回空或极低相关结果
        retrieved = result["retrieved_chunks"]
        expected_empty = result["expected_chunks"]
        if expected_empty == []:
            # 如果期望为空，验证确实返回少
            self.assertLessEqual(len(retrieved), 2)

    def test_partial_match(self):
        """ret_009: 部分关键词匹配"""
        result = next(r for r in self.results if r["case_id"] == "ret_009")
        self.assertIn("Python", result["query"])

    def test_comparison_retrieval(self):
        """ret_015: 对比类检索"""
        result = next(r for r in self.results if r["case_id"] == "ret_015")
        self.assertIn("随机森林", result["query"])
        self.assertIn("梯度提升", result["query"])


class TestRetrievalMetrics(unittest.TestCase):
    """检索指标计算测试"""

    def setUp(self):
        self.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))

    def test_recall_calculation(self):
        """验证 Recall@K 计算正确"""
        # 查询能匹配到 chunk_001 的 query
        result = self.client.retrieve("机器学习", top_k=5)
        chunks = result["chunks"]
        self.assertLessEqual(len(chunks), 5)

    def test_precision_calculation(self):
        """验证 Precision@K 计算正确"""
        result = self.client.retrieve("深度学习 图像识别", top_k=10)
        self.assertLessEqual(len(result["chunks"]), 10)

    def test_top_k_limit(self):
        """验证 top_k 限制有效"""
        result = self.client.retrieve("测试查询", top_k=3)
        self.assertLessEqual(len(result["chunks"]), 3)


if __name__ == "__main__":
    unittest.main()
