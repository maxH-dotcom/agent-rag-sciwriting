"""
Mock Agent Client - 模拟系统响应用于离线评测

用法:
    client = MockAgentClient(fixtures_dir="benchmark/fixtures")
    result = client.retrieve("机器学习 模型", top_k=5)
"""

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional


class MockAgentClient:
    """
    模拟 Agent 系统的各个模块响应
    支持 retrieval / citation / code_execution / e2e_flow
    """

    def __init__(self, fixtures_dir: str = "benchmark/fixtures"):
        self.fixtures_dir = Path(fixtures_dir)
        self._load_chunks()
        self._load_cases()

    def _load_chunks(self) -> None:
        """加载 chunk 数据"""
        chunks_path = self.fixtures_dir / "retrieval" / "chunks.json"
        if chunks_path.exists():
            with open(chunks_path) as f:
                data = json.load(f)
                self.chunks = {c["chunk_id"]: c for c in data.get("chunks", [])}
        else:
            self.chunks = {}

    def _load_cases(self) -> None:
        """加载测试用例定义"""
        self.cases = {}
        for category in ["retrieval", "text_to_code", "citation", "e2e"]:
            cases_path = self.fixtures_dir.parent / category / "cases.json"
            if cases_path.exists():
                with open(cases_path) as f:
                    data = json.load(f)
                    for case in data.get("test_cases", []):
                        self.cases[case["case_id"]] = case

    # ========== Retrieval ==========

    def _tokenize(self, text: str) -> set:
        """中英文混合分词：英文按空格，中文按字符bigram。"""
        text_lower = text.lower()
        tokens = set()
        for word in text_lower.split():
            tokens.add(word)
        # 中文字符bigram（处理连续中文字符）
        i = 0
        chars = []
        for c in text_lower:
            if '\u4e00' <= c <= '\u9fff':
                chars.append(c)
            else:
                if chars:
                    # 将连续的中文字符转为bigram token
                    for j in range(len(chars)):
                        if j + 1 < len(chars):
                            tokens.add(chars[j] + chars[j + 1])
                    chars = []
        if chars:
            for j in range(len(chars)):
                if j + 1 < len(chars):
                    tokens.add(chars[j] + chars[j + 1])
        return tokens

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        模拟检索 API
        基于关键词匹配模拟检索结果
        """
        query_keywords = self._tokenize(query)

        # 简单关键词匹配评分
        scored = []
        for chunk_id, chunk in self.chunks.items():
            text_keywords = self._tokenize(chunk["text"])
            score = len(query_keywords & text_keywords) / max(len(query_keywords), 1)
            if score > 0:
                scored.append((chunk_id, score, chunk))

        scored.sort(key=lambda x: -x[1])
        top_results = scored[:top_k]

        return {
            "chunks": [
                {"chunk_id": cid, "text": c["text"], "source": c["source"], "relevance_score": s}
                for cid, s, c in top_results
            ],
            "query": query,
            "total_chunks": len(self.chunks)
        }

    # ========== Citation ==========

    def trace_citation(self, claim: str) -> Dict[str, Any]:
        """
        模拟引用溯源 API
        简单基于 claim 关键词匹配溯源
        """
        claim_keywords = self._tokenize(claim)

        best_match = None
        best_score = 0.0

        for chunk_id, chunk in self.chunks.items():
            text_keywords = self._tokenize(chunk["text"])
            score = len(claim_keywords & text_keywords) / max(len(claim_keywords), 1)
            if score > best_score:
                best_score = score
                best_match = chunk

        if best_match and best_score > 0.05:
            return {
                "traced_source": best_match["chunk_id"],
                "traced_text": best_match["text"],
                "confidence": best_score
            }
        return {
            "traced_source": None,
            "traced_text": "",
            "confidence": 0.0
        }

    # ========== Code Execution ==========

    def execute_code(
        self,
        code: str,
        data_file: str,
        forbidden_operations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        模拟代码执行
        返回符合 ExecutionResult schema 的响应
        """
        from backend.core.sandbox import check_code, execute_in_sandbox

        # 1. 安全检查
        check_result = check_code(code)

        if not check_result.passed:
            return {
                "success": False,
                "error_message": f"安全检查失败: {', '.join(check_result.errors)}",
                "check_result": check_result.to_dict(),
                "execution_result": None
            }

        # 2. 真实执行（使用沙箱）
        data_path = self.fixtures_dir / "text_to_code" / data_file
        if data_path.exists():
            data_files = [str(data_path)]
        else:
            data_files = []

        exec_result = execute_in_sandbox(code, data_files=data_files)

        return {
            "success": exec_result.success,
            "error_message": exec_result.error_message,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "output_files": exec_result.output_files,
            "execution_time_ms": exec_result.execution_time_ms,
            "check_result": check_result.to_dict(),
            "execution_result": exec_result.to_dict()
        }

    # ========== E2E Flow ==========

    def run_e2e_flow(
        self,
        case_id: str,
        user_query: str,
        data_file: str,
        interrupt_at: Optional[str] = None,
        modified_payload: Optional[Dict[str, Any]] = None,
        reject_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        模拟端到端流程
        基于测试用例定义模拟 LangGraph 流程
        """
        case = self.cases.get(case_id)
        if not case:
            return {"error": f"Unknown case: {case_id}"}

        visited_nodes = []
        state = {
            "task_id": f"benchmark_{case_id}",
            "user_query": user_query,
            "data_file": data_file,
            "status": "running"
        }

        # 模拟节点序列
        node_sequence = ["data_mapping", "literature", "novelty", "analysis", "brief", "writing"]

        for node in node_sequence:
            visited_nodes.append(node)
            state["current_node"] = node

            # 检查是否在中断点
            if node == interrupt_at:
                state["status"] = "interrupted"
                state["interrupt_reason"] = f"{node}_required"
                if modified_payload:
                    # 模拟修改后继续
                    state.update(modified_payload)
                    state["status"] = "running"
                else:
                    break

            # 检查是否在拒绝点
            if node == reject_at:
                state["status"] = "aborted"
                state["interrupt_reason"] = "user_rejected"
                break

        if state["status"] == "running":
            if node_sequence[-1] in visited_nodes:
                state["status"] = "done"
                state["result"] = {"output": "generated"}

        return {
            "case_id": case_id,
            "visited_nodes": visited_nodes,
            "final_status": state["status"],
            "current_node": state.get("current_node"),
            "result": state.get("result"),
            "interrupt_reason": state.get("interrupt_reason")
        }

    # ========== Batch Runner ==========

    def run_retrieval_benchmark(self) -> List[Dict[str, Any]]:
        """运行检索基准测试"""
        results = []
        for case_id, case in self.cases.items():
            if not case_id.startswith("ret_"):
                continue

            query = case["query"]
            retrieved = self.retrieve(query, top_k=10)

            # 计算指标
            retrieved_ids = [c["chunk_id"] for c in retrieved["chunks"]]
            expected_ids = case.get("expected_top_chunks", [])

            k = 5
            top_k = retrieved_ids[:k]
            recall = len(set(top_k) & set(expected_ids)) / len(expected_ids) if expected_ids else 0.0

            results.append({
                "case_id": case_id,
                "query": query,
                "retrieved_chunks": retrieved_ids,
                "expected_chunks": expected_ids,
                "recall_at_5": recall,
                "passed": recall >= 0.8
            })

        return results

    def run_code_benchmark(self) -> List[Dict[str, Any]]:
        """运行代码生成基准测试"""
        from backend.agents.orchestrator.subgraphs.text_to_code_bridge import (
            extract_evidence,
            generate_code,
            run_bridge
        )

        results = []
        for case_id, case in self.cases.items():
            if not case_id.startswith("code_"):
                continue

            # 构建 mock state
            state = {
                "task_id": f"benchmark_{case_id}",
                "user_query": case["task"],
                "data_files": [str(self.fixtures_dir / "text_to_code" / case["data_file"])],
                "data_mapping_result": {
                    "dependent_var": "y",
                    "independent_vars": ["x"],
                    "control_vars": [],
                    "entity_column": "",
                    "time_column": "",
                },
                "literature_result": {
                    "all_chunks": [
                        {"chunk_id": ec, "source": "fixture", "text": "", "relevance_score": 0.8}
                        for ec in case.get("evidence_chunks", [])
                    ],
                    "quality_score": 0.7,
                    "method_metadata": [],
                },
                "novelty_result": {},
            }

            try:
                # 运行 bridge
                bridge_result = run_bridge(state)

                results.append({
                    "case_id": case_id,
                    "task": case["task"],
                    "bridge_status": bridge_result.get("bridge_status"),
                    "generated_code": bridge_result.get("generated_code"),
                    "check_result": bridge_result.get("check_result"),
                    "execution_result": bridge_result.get("execution_result"),
                    "passed": bridge_result.get("check_result", {}).get("passed", False)
                })
            except Exception as e:
                results.append({
                    "case_id": case_id,
                    "error": str(e),
                    "passed": False
                })

        return results

    def run_citation_benchmark(self) -> List[Dict[str, Any]]:
        """运行引用溯源基准测试"""
        results = []
        for case_id, case in self.cases.items():
            if not case_id.startswith("cite_"):
                continue

            trace_result = self.trace_citation(case["claim"])

            expected_source = case.get("expected_source")
            traced_source = trace_result.get("traced_source")

            # Drift 计算
            drift = 0.0
            if traced_source and expected_source and traced_source == expected_source:
                traced_text = trace_result.get("traced_text", "")
                gt_text = case.get("ground_truth", {}).get("text", "")
                if traced_text and gt_text:
                    from difflib import SequenceMatcher
                    similarity = SequenceMatcher(None, traced_text[:100], gt_text[:100]).ratio()
                    drift = 1.0 - similarity

            results.append({
                "case_id": case_id,
                "claim": case["claim"],
                "traced_source": traced_source,
                "expected_source": expected_source,
                "trace_success": traced_source == expected_source,
                "drift_rate": drift,
                "passed": (traced_source == expected_source) and drift < 0.05
            })

        return results
