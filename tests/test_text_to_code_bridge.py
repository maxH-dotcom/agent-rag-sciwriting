"""Text-to-Code Bridge 测试."""

from __future__ import annotations

import textwrap
import unittest

from backend.agents.models.code_generation import (
    CodeCheckResult,
    EvidenceBinding,
    EvidenceChunk,
    EvidencePackage,
    ExecutionResult,
    GeneratedCode,
)
from backend.core.sandbox import check_code, execute_in_sandbox
from backend.agents.orchestrator.subgraphs.text_to_code_bridge import (
    extract_evidence,
    generate_code,
    run_bridge,
)


# ===== 安全检查测试 =====

class TestCodeCheck(unittest.TestCase):
    def test_valid_code_passes(self):
        code = textwrap.dedent("""\
            import pandas as pd
            import numpy as np
            df = pd.read_csv('data.csv')
            print(df.shape)
        """)
        result = check_code(code)
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, [])

    def test_syntax_error_fails(self):
        code = "def foo(\n"
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("语法错误" in e for e in result.errors))

    def test_os_system_blocked(self):
        code = "import os\nos.system('rm -rf /')"
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("os" in e for e in result.errors))

    def test_subprocess_blocked(self):
        code = "import subprocess\nsubprocess.run(['ls'])"
        result = check_code(code)
        self.assertFalse(result.passed)

    def test_eval_blocked(self):
        code = "x = eval('1+1')"
        result = check_code(code)
        self.assertFalse(result.passed)

    def test_exec_blocked(self):
        code = "exec('print(1)')"
        result = check_code(code)
        self.assertFalse(result.passed)

    def test_requests_blocked(self):
        code = "import requests\nrequests.get('http://evil.com')"
        result = check_code(code)
        self.assertFalse(result.passed)

    def test_allowed_imports_pass(self):
        code = textwrap.dedent("""\
            import pandas as pd
            import numpy as np
            import statsmodels.api as sm
            from scipy import stats
            import json
        """)
        result = check_code(code)
        self.assertTrue(result.passed)

    def test_forbidden_import_blocked(self):
        code = "import http.server"
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("http" in e for e in result.errors))

    def test_while_loop_warns(self):
        code = textwrap.dedent("""\
            import pandas as pd
            while True:
                break
        """)
        result = check_code(code)
        self.assertTrue(result.passed)  # passes, just warns
        self.assertTrue(any("while" in w for w in result.warnings))


# ===== 沙箱执行测试 =====

class TestSandboxExecution(unittest.TestCase):
    def test_simple_execution(self):
        code = "print('hello world')"
        result = execute_in_sandbox(code)
        self.assertTrue(result.success)
        self.assertIn("hello world", result.stdout)
        self.assertGreater(result.execution_time_ms, 0)

    def test_execution_with_error(self):
        code = "raise ValueError('test error')"
        result = execute_in_sandbox(code)
        self.assertFalse(result.success)
        self.assertIn("test error", result.stderr)

    def test_timeout_protection(self):
        code = "import time\ntime.sleep(10)"
        result = execute_in_sandbox(code, timeout=2)
        self.assertFalse(result.success)
        self.assertIn("超时", result.error_message)

    def test_output_files_collected(self):
        code = textwrap.dedent("""\
            with open('result.csv', 'w') as f:
                f.write('a,b\\n1,2\\n')
            print('done')
        """)
        result = execute_in_sandbox(code)
        self.assertTrue(result.success)
        self.assertTrue(any("result.csv" in f for f in result.output_files))


# ===== 证据提取测试 =====

class TestEvidenceExtraction(unittest.TestCase):
    def test_extract_from_literature_result(self):
        state = {
            "task_id": "test_001",
            "data_mapping_result": {
                "dependent_var": "carbon_emission",
                "independent_vars": ["gdp", "population"],
            },
            "literature_result": {
                "all_chunks": [
                    {
                        "chunk_id": "lit_001",
                        "source": "OpenAlex: Author (2020)",
                        "text": "固定效应模型适合面板数据",
                        "relevance_score": 0.9,
                    }
                ],
                "quality_score": 0.7,
                "quality_warning": None,
                "method_metadata": [
                    {"method_name": "固定效应模型"},
                ],
            },
        }
        pkg = extract_evidence(state)
        self.assertEqual(pkg.task_id, "test_001")
        self.assertEqual(len(pkg.evidence_chunks), 1)
        self.assertEqual(pkg.evidence_chunks[0].chunk_id, "lit_001")
        self.assertAlmostEqual(pkg.quality_score, 0.7)

    def test_missing_aspects_detected(self):
        state = {
            "task_id": "test_002",
            "data_mapping_result": {},
            "literature_result": {"all_chunks": [], "method_metadata": []},
        }
        pkg = extract_evidence(state)
        self.assertIn("因变量未确认", pkg.missing_aspects)
        self.assertIn("自变量未确认", pkg.missing_aspects)
        self.assertIn("无文献证据", pkg.missing_aspects)


# ===== 代码生成测试 =====

class TestCodeGeneration(unittest.TestCase):
    def _make_state(self, **overrides):
        base = {
            "task_id": "test_gen",
            "user_query": "碳排放 农业 面板数据",
            "data_files": ["data.csv"],
            "data_mapping_result": {
                "dependent_var": "carbon",
                "independent_vars": ["gdp", "population"],
                "control_vars": ["urbanization"],
                "entity_column": "province",
                "time_column": "year",
            },
            "literature_result": {
                "all_chunks": [
                    {"chunk_id": "lit_001", "source": "test", "text": "FE model", "relevance_score": 0.9}
                ],
                "quality_score": 0.7,
                "method_metadata": [{"method_name": "固定效应模型"}],
            },
            "novelty_result": {
                "transfer_assessments": [
                    {"method_name": "固定效应模型", "transfer_feasibility": "高"}
                ],
            },
        }
        base.update(overrides)
        return base

    def test_generates_panel_fe_code(self):
        state = self._make_state()
        evidence = extract_evidence(state)
        gen = generate_code(state, evidence)
        self.assertIn("PanelOLS", gen.code_script)
        self.assertIn("carbon", gen.code_script)
        self.assertIn("province", gen.code_script)
        self.assertTrue(len(gen.execution_plan) > 0)
        self.assertTrue(len(gen.evidence_bindings) > 0)
        self.assertIn("固定效应", gen.adaptation_explanation)

    def test_generates_ols_for_cross_section(self):
        state = self._make_state(
            data_mapping_result={
                "dependent_var": "income",
                "independent_vars": ["education", "experience"],
                "control_vars": [],
                "entity_column": "",
                "time_column": "",
            },
            novelty_result={},
            literature_result={
                "all_chunks": [],
                "quality_score": 0.5,
                "method_metadata": [],
            },
        )
        evidence = extract_evidence(state)
        gen = generate_code(state, evidence)
        self.assertIn("OLS", gen.code_script)
        self.assertIn("income", gen.code_script)

    def test_generates_stirpat_code(self):
        state = self._make_state(
            novelty_result={
                "transfer_assessments": [
                    {"method_name": "STIRPAT模型", "transfer_feasibility": "高"}
                ],
            },
        )
        evidence = extract_evidence(state)
        gen = generate_code(state, evidence)
        self.assertIn("STIRPAT", gen.code_script)
        self.assertIn("ln_", gen.code_script)

    def test_generates_did_code(self):
        state = self._make_state(
            novelty_result={
                "transfer_assessments": [
                    {"method_name": "双重差分", "transfer_feasibility": "高"}
                ],
            },
        )
        evidence = extract_evidence(state)
        gen = generate_code(state, evidence)
        self.assertIn("DID", gen.code_script)
        self.assertIn("did_interaction", gen.code_script)

    def test_generated_code_passes_check(self):
        """生成的代码必须通过安全检查."""
        state = self._make_state()
        evidence = extract_evidence(state)
        gen = generate_code(state, evidence)
        result = check_code(gen.code_script)
        self.assertTrue(result.passed, f"安全检查失败: {result.errors}")


# ===== Bridge 完整流程测试 =====

class TestBridgeIntegration(unittest.TestCase):
    def test_bridge_full_flow(self):
        state = {
            "task_id": "bridge_test",
            "user_query": "碳排放 面板数据",
            "data_files": [],
            "data_mapping_result": {
                "dependent_var": "y",
                "independent_vars": ["x1", "x2"],
                "control_vars": [],
                "entity_column": "",
                "time_column": "",
            },
            "literature_result": {
                "all_chunks": [
                    {"chunk_id": "lit_001", "source": "test", "text": "OLS is fine", "relevance_score": 0.8}
                ],
                "quality_score": 0.65,
                "method_metadata": [],
            },
            "novelty_result": {},
        }
        result = run_bridge(state)
        self.assertIn(result["bridge_status"], ("success", "execution_failed"))
        self.assertIsNotNone(result["generated_code"])
        self.assertIsNotNone(result["check_result"])
        self.assertTrue(result["check_result"]["passed"])

    def test_bridge_integrated_in_analysis_node(self):
        """确认 analysis_node 输出包含 bridge 结果."""
        from backend.agents.orchestrator.subgraphs import analysis_node

        state = {
            "task_id": "node_test",
            "user_query": "test",
            "data_files": [],
            "data_mapping_result": {
                "dependent_var": "y",
                "independent_vars": ["x1"],
                "control_vars": [],
                "entity_column": "",
                "time_column": "",
            },
            "literature_result": {
                "all_chunks": [],
                "quality_score": 0.5,
                "method_metadata": [],
            },
            "novelty_result": {},
        }
        result = analysis_node.run(state)
        ar = result["analysis_result"]
        self.assertIn("bridge_status", ar)
        self.assertIn("code_script", ar)
        self.assertIn("execution_result", ar)
        self.assertIn("result_summary", ar)
        self.assertIn("check_result", ar)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["interrupt_reason"], "code_plan_ready")


# ===== Pydantic 模型测试 =====

class TestModels(unittest.TestCase):
    def test_evidence_package_serialization(self):
        pkg = EvidencePackage(
            task_id="t1",
            evidence_chunks=[EvidenceChunk(chunk_id="c1", source="s", text="t")],
        )
        d = pkg.to_dict()
        self.assertEqual(d["task_id"], "t1")
        self.assertEqual(len(d["evidence_chunks"]), 1)

    def test_execution_result_defaults(self):
        r = ExecutionResult(success=True)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.output_files, [])
        self.assertEqual(r.execution_time_ms, 0)


if __name__ == "__main__":
    unittest.main()
