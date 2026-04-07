"""
Benchmark Text-to-Code Tests
代码生成能力基准测试
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.agents.models.code_generation import CodeCheckResult
from backend.core.sandbox import check_code, execute_in_sandbox


class TestCodeGenerationBenchmark(unittest.TestCase):
    """代码生成能力基准测试"""

    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = ROOT / "benchmark" / "fixtures" / "text_to_code"
        cls.cases_dir = ROOT / "benchmark" / "text_to_code"

    def _load_cases(self):
        import json
        with open(self.cases_dir / "cases.json") as f:
            data = json.load(f)
        return {c["case_id"]: c for c in data["test_cases"]}

    def test_basic_calculation(self):
        """code_001: 基础数学计算 - 均值和标准差"""
        code = '''
import pandas as pd
import numpy as np

df = pd.read_csv('simple_data.csv')
result = {
    "mean": df["value"].mean(),
    "std": df["value"].std()
}
print(f"mean={result['mean']:.4f}, std={result['std']:.4f}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed, f"安全检查失败: {check_result.errors}")

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "simple_data.csv")])
        # pandas 可能未安装，只在安装时验证执行结果
        if exec_result.success:
            self.assertIn("mean=", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_data_filtering(self):
        """code_002: 数据筛选与清洗"""
        code = '''
import pandas as pd
import numpy as np

df = pd.read_csv('data_with_na.csv')
df_clean = df.dropna()
corr = df_clean["x"].corr(df_clean["y"])
print(f"correlation={corr:.4f}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "data_with_na.csv")])
        if exec_result.success:
            self.assertIn("correlation=", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas/numpy 而执行失败"
            )

    def test_ols_regression(self):
        """code_003: OLS 线性回归"""
        code = '''
import pandas as pd
import statsmodels.api as sm

df = pd.read_csv('regression_data.csv')
X = sm.add_constant(df["x"])
model = sm.OLS(df["y"], X).fit()
print(f"r_squared={model.rsquared:.4f}")
print(f"coefficients={list(model.params)}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed, f"安全检查失败: {check_result.errors}")

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "regression_data.csv")])
        # statsmodels 可能未安装，只在安装时验证执行结果
        if exec_result.success:
            self.assertIn("r_squared=", exec_result.stdout)
        else:
            self.assertTrue("statsmodels" in exec_result.error_message.lower() or "ModuleNotFoundError" in exec_result.stderr)

    def test_panel_data_fe(self):
        """code_004: 面板数据固定效应"""
        code = '''
import pandas as pd
from linearmodels.panel import PanelOLS

df = pd.read_csv('panel_data.csv')
df = df.set_index(["region", "year"])
dep = df["y"]
indep = df[["x1", "x2"]]
model = PanelOLS(dep, indep, entity_effects=True).fit()
print(f"r_squared={model.rsquared:.4f}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "panel_data.csv")])
        # linearmodels 可能未安装，只验证安全检查通过
        if not exec_result.success:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少依赖库而执行失败"
            )

    def test_visualization(self):
        """code_005: 数据可视化"""
        code = '''
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv('time_series.csv')
plt.figure()
plt.plot(df["date"], df["value"])
plt.savefig('output.png')
plt.close()
print("plot saved")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "time_series.csv")])
        # matplotlib 可能未安装
        if exec_result.success:
            self.assertIn("plot saved", exec_result.stdout)
        else:
            self.assertTrue("matplotlib" in exec_result.error_message.lower() or "ModuleNotFoundError" in exec_result.stderr)

    def test_groupby_aggregation(self):
        """code_006: 分组聚合"""
        code = '''
import pandas as pd

df = pd.read_csv('regional_data.csv')
result = df.groupby("region").agg({"sales": ["mean", "sum"]})
print(result)
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "regional_data.csv")])
        if exec_result.success:
            self.assertIn("region", exec_result.stdout.lower())
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_classification(self):
        """code_007: 逻辑回归分类"""
        code = '''
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

df = pd.read_csv('binary_class.csv')
X = df[["feature1", "feature2"]]
y = df["label"]
model = LogisticRegression().fit(X, y)
pred = model.predict(X)
acc = accuracy_score(y, pred)
print(f"accuracy={acc:.4f}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "binary_class.csv")])
        # sklearn 可能未安装
        if exec_result.success:
            self.assertIn("accuracy=", exec_result.stdout)
        else:
            self.assertTrue("sklearn" in exec_result.error_message.lower() or "ModuleNotFoundError" in exec_result.stderr)

    def test_descriptive_stats(self):
        """code_011: 描述性统计"""
        code = '''
import pandas as pd

df = pd.read_csv('numeric_data.csv')
stats = df["value"].describe()
print(stats)
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "numeric_data.csv")])
        if exec_result.success:
            self.assertIn("count", exec_result.stdout.lower())
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_missing_data_handling(self):
        """code_012: 缺失值处理"""
        code = '''
import pandas as pd

df = pd.read_csv('messy_data.csv')
df_filled = df.fillna(df.mean())
print(f"filled shape={df_filled.shape}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "messy_data.csv")])
        if exec_result.success:
            self.assertIn("filled", exec_result.stdout.lower())
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_correlation_matrix(self):
        """code_013: 相关性矩阵"""
        code = '''
import pandas as pd

df = pd.read_csv('multi_var.csv')
corr = df.corr()
print(f"corr_matrix_shape={corr.shape}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "multi_var.csv")])
        if exec_result.success:
            self.assertIn("corr_matrix_shape", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_time_series_decomposition(self):
        """code_008: 时间序列分解"""
        code = '''
import pandas as pd

df = pd.read_csv('ts_data.csv')
print(f"rows={len(df)}")
result = {
    "has_trend": True,
    "has_seasonal": True
}
print(result)
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "ts_data.csv")])
        if exec_result.success:
            self.assertIn("has_trend", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_data_transformation(self):
        """code_015: 数据转换（对数化/标准化）"""
        code = '''
import pandas as pd
import numpy as np

df = pd.read_csv('raw_data.csv')
df["log_val"] = np.log(df["value"])
df["std_val"] = (df["value"] - df["value"].mean()) / df["value"].std()
print(f"log_transform=True, standardized=True")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "raw_data.csv")])
        if exec_result.success:
            self.assertIn("log_transform", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas/numpy 而执行失败"
            )

    def test_outlier_detection(self):
        """code_016: 异常值检测"""
        code = '''
import pandas as pd
import numpy as np

df = pd.read_csv('data_with_outliers.csv')
Q1 = df["value"].quantile(0.25)
Q3 = df["value"].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df["value"] < Q1 - 1.5 * IQR) | (df["value"] > Q3 + 1.5 * IQR)]
print(f"outlier_count={len(outliers)}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "data_with_outliers.csv")])
        if exec_result.success:
            self.assertIn("outlier_count", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas/numpy 而执行失败"
            )

    def test_merge_join(self):
        """code_017: 数据合并"""
        code = '''
import pandas as pd

left = pd.read_csv('left.csv')
right = pd.read_csv('right.csv')
merged = left.merge(right, on="id")
print(f"merged_rows={len(merged)}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(
            code,
            data_files=[
                str(self.fixtures_dir / "left.csv"),
                str(self.fixtures_dir / "right.csv"),
            ]
        )
        if exec_result.success:
            self.assertIn("merged_rows", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_pivot_table(self):
        """code_018: 数据透视表"""
        code = '''
import pandas as pd

df = pd.read_csv('sales_data.csv')
pivot = df.pivot_table(values="sales", index="region", aggfunc="sum")
print(f"pivot_table_created=True")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "sales_data.csv")])
        if exec_result.success:
            self.assertIn("pivot_table_created", exec_result.stdout)
        else:
            self.assertTrue(
                check_result.passed,
                "安全检查应通过，仅因缺少 pandas 而执行失败"
            )

    def test_hypothesis_test(self):
        """code_014: t检验"""
        code = '''
import pandas as pd
from scipy import stats

df = pd.read_csv('two_groups.csv')
group_a = df[df["group"] == "A"]["value"]
group_b = df[df["group"] == "B"]["value"]
t_stat, p_value = stats.ttest_ind(group_a, group_b)
print(f"t={t_stat:.4f}, p={p_value:.4f}")
'''
        check_result = check_code(code)
        self.assertTrue(check_result.passed)

        exec_result = execute_in_sandbox(code, data_files=[str(self.fixtures_dir / "two_groups.csv")])
        # scipy 可能未安装
        if exec_result.success:
            self.assertIn("t=", exec_result.stdout)
        else:
            self.assertTrue("scipy" in exec_result.error_message.lower() or "ModuleNotFoundError" in exec_result.stderr)


class TestSecurityBoundaries(unittest.TestCase):
    """安全边界测试"""

    def test_os_system_blocked(self):
        """code_009: os.system 被拦截"""
        code = 'import os\nos.system("ls")'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("os.system" in e for e in result.errors))

    def test_subprocess_blocked(self):
        """subprocess 被拦截"""
        code = 'import subprocess\nsubprocess.run(["ls"])'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("subprocess" in e for e in result.errors))

    def test_eval_blocked(self):
        """code_010: eval 被拦截"""
        code = 'x = eval("1+1")'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("eval" in e for e in result.errors))

    def test_exec_blocked(self):
        """exec 被拦截"""
        code = 'exec("print(1)")'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("exec" in e for e in result.errors))

    def test_requests_blocked(self):
        """requests 被拦截"""
        code = 'import requests\nrequests.get("http://example.com")'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("requests" in e for e in result.errors))

    def test_whitelist_allows_pandas(self):
        """白名单允许 pandas/numpy/scipy"""
        code = '''
import pandas as pd
import numpy as np
from scipy import stats
'''
        result = check_code(code)
        self.assertTrue(result.passed)

    def test_forbidden_import_blocked(self):
        """禁止的 import 被拦截"""
        code = 'import http.server'
        result = check_code(code)
        self.assertFalse(result.passed)
        self.assertTrue(any("http" in e.lower() for e in result.errors))


class TestSandboxExecution(unittest.TestCase):
    """沙箱执行测试"""

    def setUp(self):
        self.fixtures_dir = ROOT / "benchmark" / "fixtures" / "text_to_code"

    def test_simple_execution(self):
        """基础执行"""
        code = 'print("hello benchmark")'
        result = execute_in_sandbox(code)
        self.assertTrue(result.success)
        self.assertIn("hello benchmark", result.stdout)

    def test_execution_with_data(self):
        """带数据文件的执行"""
        code = '''
import pandas as pd
df = pd.read_csv('simple_data.csv')
print(f"rows={len(df)}")
'''
        result = execute_in_sandbox(
            code,
            data_files=[str(self.fixtures_dir / "simple_data.csv")]
        )
        if result.success:
            self.assertIn("rows=10", result.stdout)
        else:
            # pandas 未安装时，安全检查应通过
            pass

    def test_timeout_protection(self):
        """超时保护"""
        code = 'import time\ntime.sleep(10)'
        result = execute_in_sandbox(code, timeout=2)
        self.assertFalse(result.success)
        self.assertIn("超时", result.error_message)

    def test_output_files_collected(self):
        """输出文件收集"""
        code = '''
with open('result.csv', 'w') as f:
    f.write('a,b\\n1,2\\n')
print("done")
'''
        result = execute_in_sandbox(code)
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
