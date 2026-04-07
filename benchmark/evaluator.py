"""
离线评测引擎
Benchmark Evaluator - 自动化指标计算
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class EvaluationResult:
    case_id: str
    category: str
    passed: bool
    score: float
    metrics: Dict[str, Any]
    errors: List[str]
    details: Optional[Dict[str, Any]] = None


class BenchmarkEvaluator:
    """
    离线评测引擎
    支持 4 类评测：retrieval / text_to_code / citation / e2e
    """

    def __init__(self, benchmark_dir: str = "benchmark"):
        self.benchmark_dir = Path(benchmark_dir)
        self.results: List[EvaluationResult] = []

    # ========== 检索评测 ==========

    async def evaluate_retrieval(self, case: dict) -> EvaluationResult:
        """
        评测检索能力
        指标：Recall@5, Precision@10, MRR, Keyword Recall
        """
        from difflib import SequenceMatcher

        retrieved_chunks = case.get("retrieved_chunks", [])
        expected_chunks = case.get("expected_top_chunks", [])
        required_keywords = case.get("required_keywords", [])

        # 加载 chunk 文本（用于 keyword recall）
        chunks_text = self._load_chunks_text()

        # Recall@K
        k = 5
        top_k = retrieved_chunks[:k] if len(retrieved_chunks) >= k else retrieved_chunks
        relevant_in_top_k = len(set(top_k) & set(expected_chunks))
        recall = relevant_in_top_k / len(expected_chunks) if expected_chunks else 0.0

        # Precision@K
        precision_k = 10
        top_k10 = retrieved_chunks[:precision_k] if len(retrieved_chunks) >= precision_k else retrieved_chunks
        relevant_in_top_k10 = len(set(top_k10) & set(expected_chunks))
        precision = relevant_in_top_k10 / len(top_k10) if top_k10 else 0.0

        # MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, chunk_id in enumerate(retrieved_chunks, 1):
            if chunk_id in expected_chunks:
                mrr = 1.0 / i
                break

        # Keyword Recall — 在 chunk 文本而非 ID 中搜索关键词
        keyword_found = 0
        for kw in required_keywords:
            found = False
            for chunk_id in retrieved_chunks[:5]:
                chunk_text = chunks_text.get(chunk_id, "")
                if kw.lower() in chunk_text.lower():
                    found = True
                    break
            if found:
                keyword_found += 1
        keyword_recall = keyword_found / len(required_keywords) if required_keywords else 1.0

        # 通过判定
        passed = recall >= 0.8 and keyword_recall >= 0.6

        return EvaluationResult(
            case_id=case["case_id"],
            category="retrieval",
            passed=passed,
            score=recall * 0.5 + precision * 0.3 + mrr * 0.2,
            metrics={
                "recall_at_5": round(recall, 4),
                "precision_at_10": round(precision, 4),
                "mrr": round(mrr, 4),
                "keyword_recall": round(keyword_recall, 4),
                "relevant_count": relevant_in_top_k,
            },
            errors=[]
        )

    def _load_chunks_text(self) -> dict[str, str]:
        """加载 chunk_id -> text 映射，用于 keyword recall"""
        chunks_path = self.benchmark_dir / "fixtures" / "retrieval" / "chunks.json"
        if chunks_path.exists():
            with open(chunks_path) as f:
                data = json.load(f)
                return {c["chunk_id"]: c["text"] for c in data.get("chunks", [])}
        return {}

    # ========== 代码生成评测 ==========

    async def evaluate_code_generation(self, case: dict) -> EvaluationResult:
        """
        评测代码生成能力
        指标：执行成功率、结果准确率、安全拦截率
        """
        code_result = case.get("code_result", {})
        generated_code = code_result.get("code_script", "")
        execution_result = code_result.get("execution_result", {})
        expected_output = case.get("expected_output", {})

        errors = []

        # 1. 安全检查
        is_safe, violations = self._security_check(generated_code, case.get("forbidden_operations", []))
        if not is_safe:
            errors.append(f"安全违规: {violations}")
            return EvaluationResult(
                case_id=case["case_id"],
                category="text_to_code",
                passed=False,
                score=0.0,
                metrics={"is_safe": False, "violations": violations},
                errors=errors
            )

        # 2. 执行成功率
        execution_success = execution_result.get("success", False)

        # 3. 结果准确率
        accuracy = 1.0
        if expected_output:
            # 优先使用 output_data；若为空则尝试解析 stdout 中的 JSON
            actual = execution_result.get("output_data", {})
            if not actual and execution_result.get("stdout"):
                actual = self._parse_stdout_json(execution_result["stdout"])
            accuracy = self._calculate_accuracy(expected_output, actual, case)

        # 4. 禁止操作检查
        forbidden_blocked = case.get("note") == "系统必须拦截并拒绝执行"
        if forbidden_blocked and is_safe:
            passed = True  # 成功拦截
            accuracy = 1.0
        else:
            passed = is_safe and execution_success and accuracy >= 0.8

        return EvaluationResult(
            case_id=case["case_id"],
            category="text_to_code",
            passed=passed,
            score=accuracy if execution_success else 0.0,
            metrics={
                "is_safe": is_safe,
                "execution_success": execution_success,
                "accuracy": round(accuracy, 4),
                "violations": violations if not is_safe else []
            },
            errors=errors
        )

    def _security_check(self, code: str, forbidden: List[str]) -> tuple:
        """安全检查

        模式匹配来源：
        1. case 中显式传入的 forbidden 操作列表（优先级最高）
        2. 基础安全白名单（os.system / subprocess / eval / exec 等）

        Args:
            code: 待检查的代码字符串
            forbidden: case 中声明的禁止操作列表，如 ["os.system", "subprocess", "eval"]

        Returns:
            (is_safe: bool, violations: list[str])
        """
        import re
        violations: list[str] = []

        # 操作名 → (正则模式, 人类可读消息)
        OPERATION_PATTERNS: dict[str, tuple[str, str]] = {
            "os.system": (r"\bos\.system\b", "禁止使用 os.system"),
            "subprocess": (r"\bsubprocess\b", "禁止使用 subprocess"),
            "eval": (r"\beval\s*\(", "禁止使用 eval()"),
            "exec": (r"\bexec\s*\(", "禁止使用 exec()"),
            "__import__": (r"__import__\s*\(", "禁止使用 __import__()"),
            "requests": (r"\brequests\b", "禁止使用 requests"),
            "urllib": (r"\burllib\b", "禁止使用 urllib"),
            "http": (r"\bhttp\.", "禁止使用 http 请求"),
            "socket": (r"\bsocket\b", "禁止使用 socket"),
            "open": (r"\bopen\s*\([^)]*['\"][wrx]", "禁止直接写文件"),
            "os.chdir": (r"os\.chdir\b", "禁止切换工作目录"),
            "os.environ": (r"os\.environ\b", "禁止访问环境变量"),
            "os.remove": (r"os\.remove\b", "禁止删除文件"),
            "shutil.rmtree": (r"shutil\.rmtree\b", "禁止递归删除目录"),
        }

        # 步骤1：case 显式指定的 forbidden 操作（最严格）
        checked_patterns: set[str] = set()
        for op in forbidden:
            if op in OPERATION_PATTERNS:
                pattern, msg = OPERATION_PATTERNS[op]
                if pattern not in checked_patterns and re.search(pattern, code, re.IGNORECASE):
                    violations.append(msg)
                checked_patterns.add(pattern)

        # 步骤2：基础安全白名单（始终生效，与 forbidden 独立）
        BASE_PATTERNS: list[tuple[str, str]] = [
            (r"\bos\.system\b", "禁止使用 os.system"),
            (r"\bsubprocess\b", "禁止使用 subprocess"),
            (r"\beval\s*\(", "禁止使用 eval()"),
            (r"\bexec\s*\(", "禁止使用 exec()"),
            (r"__import__\s*\(", "禁止使用 __import__()"),
            (r"\brequests\b", "禁止使用 requests"),
            (r"\burllib\b", "禁止使用 urllib"),
            (r"\bopen\s*\([^)]*['\"][wrx]", "禁止直接写文件"),
        ]
        for pattern, msg in BASE_PATTERNS:
            if pattern not in checked_patterns and re.search(pattern, code):
                violations.append(msg)

        return len(violations) == 0, violations

    def _calculate_accuracy(self, expected: dict, actual: dict, case: dict) -> float:
        """计算结果准确率"""
        if not actual:
            return 0.0

        if expected.get("operation_blocked"):
            return 1.0  # 已拦截

        correct = 0
        total = 0

        for key, exp_val in expected.items():
            if key in ("has_mean", "has_std", "has_coefficients", "has_p_values",
                       "has_r_squared", "has_fe_model", "has_plot", "has_trend_line",
                       "has_groupby_result", "has_predictions", "has_accuracy",
                       "has_trend", "has_seasonal", "has_count", "has_median",
                       "has_min_max", "missing_filled", "has_imputation_method",
                       "has_corr_matrix", "has_t_statistic", "has_p_value",
                       "has_log_transform", "has_standardized", "has_outlier_flags",
                       "has_merged_data", "has_pivot_table", "operation_blocked"):
                if exp_val and key in actual:
                    correct += 1
                total += 1
            elif key == "correlation_range":
                if "correlation" in actual:
                    corr = actual["correlation"]
                    if isinstance(corr, (int, float)) and -1 <= corr <= 1:
                        correct += 1
                total += 1
            elif key == "group_count":
                if "group_count" in actual and actual["group_count"] == exp_val:
                    correct += 1
                total += 1
            elif key == "matrix_shape":
                if "corr_matrix" in actual:
                    shape = actual["corr_matrix"]
                    if isinstance(shape, list) and len(shape) == exp_val[0]:
                        correct += 1
                total += 1
            elif key == "outlier_count":
                if "outlier_count" in actual and actual["outlier_count"] == exp_val:
                    correct += 1
                total += 1

        return correct / total if total > 0 else 0.0

    def _parse_stdout_json(self, stdout: str) -> dict:
        """从 stdout 中提取 JSON 结构化输出"""
        import json
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
            # 尝试从 JSON 代码块中提取
            if "```json" in stdout:
                for block in stdout.split("```"):
                    if block.strip().startswith("{") and block.strip().endswith("}"):
                        try:
                            return json.loads(block.strip())
                        except json.JSONDecodeError:
                            continue
        return {}

    # ========== 引用溯源评测 ==========

    async def evaluate_citation(self, case: dict) -> EvaluationResult:
        """
        评测引用溯源能力
        指标：Trace Success Rate, Drift Rate
        """
        trace_result = case.get("trace_result", {})
        traced_source = trace_result.get("traced_source")
        expected_source = case.get("expected_source")
        ground_truth = case.get("ground_truth")

        errors = []

        # Trace Success Rate
        trace_success = (traced_source == expected_source) or (
            expected_source is None and traced_source is None
        )

        # Drift Rate
        drift = 0.0
        if trace_success and ground_truth and traced_source:
            traced_text = trace_result.get("traced_text", "")
            gt_text = ground_truth.get("text", "")
            if traced_text and gt_text:
                similarity = SequenceMatcher(None, traced_text[:100], gt_text[:100]).ratio()
                drift = 1.0 - similarity

        # 通过判定
        passed = trace_success and drift < 0.05

        return EvaluationResult(
            case_id=case["case_id"],
            category="citation",
            passed=passed,
            score=1.0 - drift,
            metrics={
                "trace_success": trace_success,
                "drift_rate": round(drift, 4),
                "traced_source": traced_source,
                "expected_source": expected_source
            },
            errors=[]
        )

    # ========== 端到端评测 ==========

    async def evaluate_e2e(self, case: dict) -> EvaluationResult:
        """
        评测端到端流程
        指标：任务完成率、节点覆盖率、状态正确性
        """
        flow_result = case.get("flow_result", {})
        expected = case.get("expected_outputs", {})

        errors = []

        # 检查最终状态
        final_status = flow_result.get("final_status")
        expected_status = expected.get("final_status", "done")
        status_correct = (final_status == expected_status)

        # 检查节点覆盖
        visited_nodes = flow_result.get("visited_nodes", [])
        expected_nodes = expected.get("node_sequence", [])
        node_coverage = len(set(visited_nodes) & set(expected_nodes)) / len(expected_nodes) if expected_nodes else 1.0

        # 检查特定输出
        output_checks = []
        for key, val in expected.items():
            if key in flow_result:
                if isinstance(val, bool):
                    output_checks.append(flow_result.get(key) == val)
                elif key == "final_status":
                    output_checks.append(flow_result.get("final_status") == val)
                elif key == "routed_to":
                    output_checks.append(flow_result.get("current_node") == val)

        # 通过判定
        passed = status_correct and node_coverage >= 0.8 and all(output_checks) if output_checks else status_correct

        return EvaluationResult(
            case_id=case["case_id"],
            category="e2e",
            passed=passed,
            score=node_coverage,
            metrics={
                "status_correct": status_correct,
                "node_coverage": round(node_coverage, 4),
                "visited_nodes": visited_nodes,
                "expected_nodes": expected_nodes
            },
            errors=errors
        )

    # ========== 批量运行 ==========

    async def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整评测"""
        results = []

        # 检索
        retrieval_cases = self._load_cases("retrieval")
        for case in retrieval_cases:
            result = await self.evaluate_retrieval(case)
            results.append(result)

        # 代码生成
        code_cases = self._load_cases("text_to_code")
        for case in code_cases:
            result = await self.evaluate_code_generation(case)
            results.append(result)

        # 引用溯源
        citation_cases = self._load_cases("citation")
        for case in citation_cases:
            result = await self.evaluate_citation(case)
            results.append(result)

        # 端到端
        e2e_cases = self._load_cases("e2e")
        for case in e2e_cases:
            result = await self.evaluate_e2e(case)
            results.append(result)

        self.results = results
        return self.generate_report()

    def _load_cases(self, category: str) -> List[dict]:
        """加载测试用例"""
        path = self.benchmark_dir / category / "cases.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return data.get("test_cases", [])
        return []

    def generate_report(self) -> Dict[str, Any]:
        """生成评测报告"""
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        summary = {}
        for category, cat_results in by_category.items():
            passed = sum(1 for r in cat_results if r.passed)
            avg_score = sum(r.score for r in cat_results) / len(cat_results) if cat_results else 0

            summary[category] = {
                "total": len(cat_results),
                "passed": passed,
                "pass_rate": round(passed / len(cat_results), 4) if cat_results else 0,
                "avg_score": round(avg_score, 4)
            }

        overall_passed = sum(1 for r in self.results if r.passed)
        overall_score = sum(r.score for r in self.results) / len(self.results) if self.results else 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": {
                "total": len(self.results),
                "passed": overall_passed,
                "pass_rate": round(overall_passed / len(self.results), 4) if self.results else 0,
                "avg_score": round(overall_score, 4)
            },
            "by_category": summary,
            "details": [
                {
                    "case_id": r.case_id,
                    "category": r.category,
                    "passed": r.passed,
                    "score": round(r.score, 4),
                    "metrics": r.metrics,
                    "errors": r.errors
                }
                for r in self.results
            ]
        }
