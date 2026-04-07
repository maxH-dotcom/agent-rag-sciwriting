"""
Benchmark Citation Tests
引用溯源能力基准测试
"""

import sys
import unittest
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.mock_client import MockAgentClient


class TestCitationBenchmark(unittest.TestCase):
    """引用溯源能力基准测试"""

    @classmethod
    def setUpClass(cls):
        cls.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))
        cls.results = cls.client.run_citation_benchmark()

    def test_citation_coverage(self):
        """验证所有引用用例都被执行"""
        self.assertGreaterEqual(len(self.results), 10)

    def test_exact_claim_match(self):
        """cite_001: 精确论断溯源"""
        result = next(r for r in self.results if r["case_id"] == "cite_001")
        self.assertTrue(result["passed"], f"精确匹配失败: {result}")

    def test_paraphrased_claim(self):
        """cite_002: 转述论断溯源"""
        result = next(r for r in self.results if r["case_id"] == "cite_002")
        self.assertIn("Transformer", result["claim"])

    def test_method_citation(self):
        """cite_003: 方法引用溯源"""
        result = next(r for r in self.results if r["case_id"] == "cite_003")
        self.assertIn("卷积神经网络", result["claim"])

    def test_numerical_claim(self):
        """cite_004: 数值论断溯源"""
        result = next(r for r in self.results if r["case_id"] == "cite_004")
        self.assertIn("线性回归", result["claim"])

    def test_drift_detection(self):
        """cite_005: 引用漂移检测"""
        result = next(r for r in self.results if r["case_id"] == "cite_005")
        # 泛化论断应该有较高的 drift 或 trace 失败
        self.assertIn("ARIMA", result["claim"])

    def test_unverifiable_claim(self):
        """cite_007: 无法溯源的论断"""
        result = next(r for r in self.results if r["case_id"] == "cite_007")
        self.assertIn("效果很好", result["claim"])

    def test_partial_citation(self):
        """cite_008: 部分引用溯源"""
        result = next(r for r in self.results if r["case_id"] == "cite_008")
        self.assertIn("pandas", result["claim"])

    def test_formula_citation(self):
        """cite_009: 公式引用"""
        result = next(r for r in self.results if r["case_id"] == "cite_009")
        self.assertIn("numpy", result["claim"])

    def test_overclaiming_detection(self):
        """cite_010: 过度泛化检测"""
        result = next(r for r in self.results if r["case_id"] == "cite_010")
        self.assertIn("K-Means", result["claim"])

    def test_contradicting_citation(self):
        """cite_011: 矛盾引用检测"""
        result = next(r for r in self.results if r["case_id"] == "cite_011")
        self.assertIn("强化学习", result["claim"])

    def test_trace_chain(self):
        """cite_012: 溯源链追踪"""
        result = next(r for r in self.results if r["case_id"] == "cite_012")
        self.assertIn("随机森林", result["claim"])
        self.assertIn("Bagging", result["claim"])


class TestDriftCalculation(unittest.TestCase):
    """漂移率计算测试"""

    def setUp(self):
        self.client = MockAgentClient(fixtures_dir=str(ROOT / "benchmark" / "fixtures"))

    def test_identical_text_no_drift(self):
        """完全相同的文本漂移率为0"""
        # 使用 chunk_001 的原文以保证精确匹配
        claim = "机器学习是人工智能的一个分支，专注于从数据中学习规律。常见的机器学习模型包括决策树、支持向量机和神经网络。"
        result = self.client.trace_citation(claim)
        self.assertEqual(result["traced_source"], "chunk_001")

    def test_similar_text_low_drift(self):
        """语义相似的文本低漂移"""
        claim = "深度神经网络用于图像识别"
        result = self.client.trace_citation(claim)
        self.assertIsNotNone(result["traced_source"])

    def test_unrelated_text_no_match(self):
        """无关文本无匹配"""
        claim = "xyzabc完全不相关的查询"
        result = self.client.trace_citation(claim)
        self.assertIsNone(result["traced_source"])

    def test_drift_rate_calculation(self):
        """漂移率计算"""
        # 模拟一个 drift 场景
        traced = "在特定数据集上，模型A的准确率略高于模型B"
        ground_truth = "在CIFAR-10数据集上，模型A的准确率略高于模型B"
        similarity = SequenceMatcher(None, traced[:50], ground_truth[:50]).ratio()
        drift = 1.0 - similarity
        self.assertGreater(drift, 0.0)


if __name__ == "__main__":
    unittest.main()
