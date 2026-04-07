"""Text-to-Code Bridge — 证据驱动的代码生成 + 安全检查 + 沙箱执行.

MVP 阶段：基于规则的代码模板生成（后续可接入 LLM）。
"""

from __future__ import annotations

from typing import Any

from backend.agents.models.code_generation import (
    CodeCheckResult,
    EvidenceBinding,
    EvidenceChunk,
    EvidencePackage,
    ExecutionResult,
    GeneratedCode,
)
from backend.core.sandbox import check_code, execute_in_sandbox


# ---------------------------------------------------------------------------
# 1. 证据提取 — 从 literature_result 构建 EvidencePackage
# ---------------------------------------------------------------------------

def extract_evidence(state: dict[str, Any]) -> EvidencePackage:
    """从流水线上游结果中提取证据包."""
    task_id = state.get("task_id", "unknown")
    lit = state.get("literature_result") or {}
    chunks_raw = lit.get("all_chunks") or []

    evidence_chunks = [
        EvidenceChunk(
            chunk_id=c.get("chunk_id", f"ev_{i}"),
            source=c.get("source", "unknown"),
            text=c.get("text", ""),
            relevance_score=c.get("relevance_score", 0.0),
        )
        for i, c in enumerate(chunks_raw)
    ]

    return EvidencePackage(
        task_id=task_id,
        evidence_chunks=evidence_chunks,
        quality_score=lit.get("quality_score", 0.0),
        quality_warning=lit.get("quality_warning"),
        missing_aspects=_identify_missing(state),
    )


def _identify_missing(state: dict[str, Any]) -> list[str]:
    """简单规则检查证据缺失面."""
    missing: list[str] = []
    mapping = state.get("data_mapping_result") or {}
    lit = state.get("literature_result") or {}

    if not mapping.get("dependent_var"):
        missing.append("因变量未确认")
    if not mapping.get("independent_vars"):
        missing.append("自变量未确认")
    if not lit.get("all_chunks"):
        missing.append("无文献证据")

    method_meta = lit.get("method_metadata") or []
    has_known_method = any(
        m.get("method_name") not in ("待解析", None, "")
        for m in method_meta
    )
    if not has_known_method:
        missing.append("未识别到具体研究方法")

    return missing


# ---------------------------------------------------------------------------
# 2. 代码生成 — 基于数据映射 + 证据 + 模型推荐
# ---------------------------------------------------------------------------

def generate_code(state: dict[str, Any], evidence: EvidencePackage) -> GeneratedCode:
    """根据上游信息生成可执行的分析脚本."""
    mapping = state.get("data_mapping_result") or {}
    novelty = state.get("novelty_result") or {}
    data_files = state.get("data_files") or []

    dep_var = mapping.get("dependent_var", "y")
    indep_vars = mapping.get("independent_vars") or ["x1"]
    control_vars = mapping.get("control_vars") or []
    entity_col = mapping.get("entity_column", "")
    time_col = mapping.get("time_column", "")
    has_panel = bool(entity_col and time_col)

    # 从 novelty 中获取推荐方法
    transfers = novelty.get("transfer_assessments") or []
    recommended_method = transfers[0]["method_name"] if transfers else None

    # 从证据中辅助判断方法
    if not recommended_method:
        lit = state.get("literature_result") or {}
        methods = lit.get("method_metadata") or []
        for m in methods:
            if m.get("method_name") not in ("待解析", None, ""):
                recommended_method = m["method_name"]
                break

    if not recommended_method:
        recommended_method = "固定效应模型" if has_panel else "OLS回归"

    # 选择数据文件
    data_file = _pick_data_file(data_files)

    # 根据方法选择代码模板
    code, plan, bindings = _build_code(
        method=recommended_method,
        data_file=data_file,
        dep_var=dep_var,
        indep_vars=indep_vars,
        control_vars=control_vars,
        entity_col=entity_col,
        time_col=time_col,
        has_panel=has_panel,
        evidence=evidence,
    )

    imports = _extract_imports(code)

    explanation = (
        f"核心方法：{recommended_method}。"
        f"因变量={dep_var}，自变量={indep_vars}。"
    )
    if control_vars:
        explanation += f"控制变量={control_vars}。"
    if has_panel:
        explanation += f"面板结构：实体列={entity_col}，时间列={time_col}。"

    return GeneratedCode(
        code_script=code,
        imports=imports,
        execution_plan=plan,
        evidence_bindings=bindings,
        adaptation_explanation=explanation,
    )


def _pick_data_file(data_files: list[str]) -> str:
    """选取第一个 CSV 文件路径."""
    for f in data_files:
        if f.lower().endswith(".csv"):
            return f
    if data_files:
        return data_files[0]
    return "data.csv"


def _extract_imports(code: str) -> list[str]:
    import ast
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _build_code(
    *,
    method: str,
    data_file: str,
    dep_var: str,
    indep_vars: list[str],
    control_vars: list[str],
    entity_col: str,
    time_col: str,
    has_panel: bool,
    evidence: EvidencePackage,
) -> tuple[str, list[str], list[EvidenceBinding]]:
    """根据方法类型选择代码模板."""
    from pathlib import Path
    filename = Path(data_file).name

    all_x = indep_vars + control_vars
    x_list_str = repr(all_x)

    # 从证据中挑选第一个有意义的 chunk_id 作为绑定
    ev_id = None
    for chunk in evidence.evidence_chunks:
        if chunk.relevance_score > 0.5:
            ev_id = chunk.chunk_id
            break

    # 时间序列方法
    if method in ("ARIMA", "SARIMA", "Prophet", "VAR", "时间序列"):
        return _template_time_series(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str,
            entity_col=entity_col, time_col=time_col, has_panel=has_panel, ev_id=ev_id,
        )

    if method in ("固定效应模型", "PanelOLS") and has_panel:
        return _template_panel_fe(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str,
            entity_col=entity_col, time_col=time_col, ev_id=ev_id,
        )
    elif method in ("OLS回归", "OLS"):
        return _template_ols(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str, ev_id=ev_id,
        )
    elif method == "双重差分" and has_panel:
        return _template_did(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str,
            entity_col=entity_col, time_col=time_col, ev_id=ev_id,
        )
    elif "STIRPAT" in method:
        return _template_stirpat(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str,
            entity_col=entity_col, time_col=time_col, has_panel=has_panel, ev_id=ev_id,
        )
    else:
        # 默认回退到 OLS 或 Panel FE
        if has_panel:
            return _template_panel_fe(
                filename=filename, dep_var=dep_var, x_list_str=x_list_str,
                entity_col=entity_col, time_col=time_col, ev_id=ev_id,
            )
        return _template_ols(
            filename=filename, dep_var=dep_var, x_list_str=x_list_str, ev_id=ev_id,
        )


# ---------------------------------------------------------------------------
# 代码模板
# ---------------------------------------------------------------------------

def _template_time_series(
    *, filename: str, dep_var: str, x_list_str: str,
    entity_col: str, time_col: str, has_panel: bool, ev_id: str | None,
) -> tuple[str, list[str], list[EvidenceBinding]]:
    """时间序列预测模板：支持ARIMA、趋势分析、预测可视化."""
    code = f'''\
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ========== 第1步：读取数据 ==========
df = pd.read_csv('{filename}')
print(f"数据形状: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# ========== 第2步：准备变量 ==========
dep_var = '{dep_var}'
time_col = '{time_col}'

if dep_var not in df.columns:
    raise ValueError(f"因变量 '{{dep_var}}' 不在数据列中。可用列: {{list(df.columns)}}")
if time_col and time_col not in df.columns:
    raise ValueError(f"时间列 '{{time_col}}' 不在数据列中。可用列: {{list(df.columns)}}")

print(f"因变量: {{dep_var}}")

# ========== 第3步：数据预处理 ==========
# 将数据按时间排序
if time_col:
    df[time_col] = pd.to_numeric(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df = df.sort_values(time_col)

# 如果有entity_col，聚合为总量（省级预测）
entity_col = '{entity_col}'
if entity_col and entity_col in df.columns:
    agg_df = df.groupby(time_col)[dep_var].sum().reset_index()
    print(f"聚合后样本量: {{len(agg_df)}} (按 {{entity_col}} 聚合)")
else:
    agg_df = df[[time_col, dep_var]].copy()

agg_df = agg_df.dropna()
agg_df = agg_df.sort_values(time_col)
print(f"清洗后样本量: {{len(agg_df)}}")
print(f"时间范围: {{agg_df[time_col].min()}} - {{agg_df[time_col].max()}}")

# ========== 第4步：描述性统计 ==========
desc = agg_df[dep_var].describe()
print("\\n===== 描述性统计 =====")
print(desc)

# ========== 第5步：趋势可视化 ==========
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(agg_df[time_col], agg_df[dep_var], 'bo-', markersize=4)
plt.xlabel(time_col)
plt.ylabel(dep_var)
plt.title(f'{{dep_var}} 趋势图')
plt.grid(True, alpha=0.3)

plt.subplot(1, 2, 2)
pd.plotting.lag_plot(agg_df[dep_var], lag=1)
plt.title('自相关图')
plt.tight_layout()
plt.savefig('trend_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: trend_analysis.png")

# ========== 第6步：简单移动平均预测 ==========
window = min(3, len(agg_df) // 2)
agg_df['ma'] = agg_df[dep_var].rolling(window=window).mean()
agg_df['trend'] = np.polyfit(range(len(agg_df)), agg_df[dep_var], 1)[0]

# 未来5年预测
last_year = int(agg_df[time_col].max())
last_value = float(agg_df[dep_var].iloc[-1])
trend_slope = float(agg_df['trend'].iloc[-1])

forecast_years = list(range(last_year + 1, last_year + 6))
forecast_values = [last_value + trend_slope * (i + 1) for i in range(5)]

print("\\n===== 未来5年预测 =====")
for year, val in zip(forecast_years, forecast_values):
    print(f"  {{year}}年: {{val:.2f}}")

# ========== 第7步：预测可视化 ==========
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
historical_years = agg_df[time_col].values
historical_values = agg_df[dep_var].values
plt.plot(historical_years, historical_values, 'bo-', label='历史数据', markersize=4)
plt.plot(forecast_years, forecast_values, 'r^--', label='预测值', markersize=8)
plt.axvline(x=last_year, color='gray', linestyle=':', alpha=0.7, label='预测起点')
plt.xlabel(time_col)
plt.ylabel(dep_var)
plt.title('{{dep_var}} 历史与预测')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(1, 2, 2)
all_values = list(historical_values) + forecast_values
all_years = list(historical_years) + forecast_years
colors = ['blue'] * len(historical_values) + ['red'] * len(forecast_values)
plt.bar(all_years, all_values, color=colors, alpha=0.7)
plt.xlabel(time_col)
plt.ylabel(dep_var)
plt.title('{{dep_var}} 历年对比（含预测）')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('forecast_result.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: forecast_result.png")

# ========== 第8步：输出结构化结果 ==========
result = {{
    "method": "时间序列趋势预测",
    "n_obs": int(len(agg_df)),
    "time_range": ["{{int(agg_df[time_col].min())}}", "{{int(agg_df[time_col].max())}}"],
    "last_value": round(last_value, 4),
    "trend_slope": round(trend_slope, 4),
    "forecast": {{str(year): round(val, 2) for year, val in zip(forecast_years, forecast_values)}},
    "descriptive_stats": {{
        "mean": round(float(desc['mean']), 2) if 'mean' in desc else None,
        "std": round(float(desc['std']), 2) if 'std' in desc else None,
        "min": round(float(desc['min']), 2) if 'min' in desc else None,
        "max": round(float(desc['max']), 2) if 'max' in desc else None,
    }},
}}
print("\\n===== 结构化结果 (JSON) =====")
print(json.dumps(result, ensure_ascii=False, indent=2))
'''
    plan = ["读取数据", "准备变量", "数据预处理与聚合", "描述性统计", "趋势可视化", "移动平均预测", "预测可视化", "输出结构化结果"]
    bindings = [
        EvidenceBinding(step=5, operation="时间序列趋势可视化", evidence_chunk_id=ev_id, line_numbers=[35, 36, 37, 38]),
        EvidenceBinding(step=7, operation="未来5年预测", evidence_chunk_id=ev_id, line_numbers=[55, 56, 57]),
    ]
    return code, plan, bindings


def _template_ols(*, filename: str, dep_var: str, x_list_str: str, ev_id: str | None) -> tuple[str, list[str], list[EvidenceBinding]]:
    code = f'''\
import pandas as pd
import numpy as np
import statsmodels.api as sm
import json

# ========== 第1步：读取数据 ==========
df = pd.read_csv('{filename}')
print(f"数据形状: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# ========== 第2步：准备变量 ==========
dep_var = '{dep_var}'
x_vars = {x_list_str}

# 过滤存在的列
available_x = [v for v in x_vars if v in df.columns]
if dep_var not in df.columns:
    raise ValueError(f"因变量 '{{dep_var}}' 不在数据列中。可用列: {{list(df.columns)}}")
if not available_x:
    raise ValueError(f"自变量 {{x_vars}} 均不在数据列中。可用列: {{list(df.columns)}}")

print(f"因变量: {{dep_var}}")
print(f"自变量: {{available_x}}")

# ========== 第3步：数据清洗 ==========
cols = [dep_var] + available_x
df_clean = df[cols].dropna()
print(f"清洗后样本量: {{len(df_clean)}}")

# ========== 第4步：描述性统计 ==========
desc = df_clean.describe()
print("\\n===== 描述性统计 =====")
print(desc.to_string())

# ========== 第5步：OLS 回归 ==========
Y = df_clean[dep_var]
X = sm.add_constant(df_clean[available_x])
model = sm.OLS(Y, X).fit()
print("\\n===== OLS 回归结果 =====")
print(model.summary().as_text())

# ========== 第6步：可视化 ==========
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 系数条形图
coef_names = [n for n in model.params.index if n != 'const']
coef_vals = [float(model.params[n]) for n in coef_names]
colors = ['green' if model.pvalues[n] < 0.05 else 'gray' for n in coef_names]
axes[0].barh(coef_names, coef_vals, color=colors, alpha=0.7)
axes[0].set_xlabel('系数')
axes[0].set_title('OLS 回归系数')
axes[0].axvline(x=0, color='red', linestyle='--', alpha=0.5)
for i, (v, p) in enumerate(zip(coef_vals, [model.pvalues[n] for n in coef_names])):
    axes[0].text(v, i, f'p={{p:.3f}}', va='center', fontsize=8)

# 实际值 vs 预测值
if len(df_clean) <= 1000:
    y_pred = model.predict(X)
    axes[1].scatter(Y, y_pred, alpha=0.5, s=20)
    min_val = min(Y.min(), y_pred.min())
    max_val = max(Y.max(), y_pred.max())
    axes[1].plot([min_val, max_val], [min_val, max_val], 'r--', label='理想拟合线')
    axes[1].set_xlabel('实际值')
    axes[1].set_ylabel('预测值')
    axes[1].set_title('实际值 vs 预测值')
    axes[1].legend()

plt.tight_layout()
plt.savefig('ols_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: ols_results.png")

# ========== 第7步：输出结构化结果 ==========
result = {{
    "method": "OLS",
    "n_obs": int(model.nobs),
    "r_squared": round(model.rsquared, 4),
    "adj_r_squared": round(model.rsquared_adj, 4),
    "f_statistic": round(model.fvalue, 4) if model.fvalue else None,
    "coefficients": {{
        name: {{"coef": round(float(model.params[name]), 6), "pvalue": round(float(model.pvalues[name]), 6)}}
        for name in model.params.index
    }},
}}
print("\\n===== 结构化结果 (JSON) =====")
print(json.dumps(result, ensure_ascii=False, indent=2))
'''
    plan = ["读取 CSV 数据", "准备因变量和自变量", "数据清洗(去空值)", "描述性统计", "OLS 回归", "系数可视化", "输出结构化结果"]
    bindings = [
        EvidenceBinding(step=5, operation="OLS 回归", evidence_chunk_id=ev_id, line_numbers=[35, 36, 37]),
    ]
    return code, plan, bindings


def _template_panel_fe(
    *, filename: str, dep_var: str, x_list_str: str,
    entity_col: str, time_col: str, ev_id: str | None,
) -> tuple[str, list[str], list[EvidenceBinding]]:
    code = f'''\
import pandas as pd
import numpy as np
import json

# ========== 第1步：读取数据 ==========
df = pd.read_csv('{filename}')
print(f"数据形状: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")

# ========== 第2步：准备变量 ==========
dep_var = '{dep_var}'
x_vars = {x_list_str}
entity_col = '{entity_col}'
time_col = '{time_col}'

available_x = [v for v in x_vars if v in df.columns]
if dep_var not in df.columns:
    raise ValueError(f"因变量 '{{dep_var}}' 不在数据列中。可用列: {{list(df.columns)}}")
if not available_x:
    raise ValueError(f"自变量 {{x_vars}} 均不在数据列中。可用列: {{list(df.columns)}}")

print(f"因变量: {{dep_var}}")
print(f"自变量: {{available_x}}")
print(f"面板结构: 实体={{entity_col}}, 时间={{time_col}}")

# ========== 第3步：数据清洗 ==========
cols = [dep_var, entity_col, time_col] + available_x
df_clean = df[cols].dropna()
print(f"清洗后样本量: {{len(df_clean)}}")
print(f"实体数: {{df_clean[entity_col].nunique()}}, 时间跨度: {{df_clean[time_col].nunique()}}")

# ========== 第4步：描述性统计 ==========
desc = df_clean[[dep_var] + available_x].describe()
print("\\n===== 描述性统计 =====")
print(desc.to_string())

# ========== 第5步：固定效应模型 ==========
try:
    from linearmodels.panel import PanelOLS
    df_clean = df_clean.set_index([entity_col, time_col])
    Y = df_clean[dep_var]
    X = df_clean[available_x]
    model = PanelOLS(Y, X, entity_effects=True).fit()
    print("\\n===== 固定效应模型结果 =====")
    print(model.summary)
    result = {{
        "method": "PanelOLS (固定效应)",
        "n_obs": int(model.nobs),
        "r_squared_within": round(float(model.rsquared_within), 4),
        "f_statistic": round(float(model.f_statistic.stat), 4),
        "coefficients": {{
            name: {{"coef": round(float(model.params[name]), 6), "pvalue": round(float(model.pvalues[name]), 6)}}
            for name in model.params.index
        }},
    }}
except ImportError:
    # 回退：用 statsmodels 实体虚拟变量
    import statsmodels.api as sm
    dummies = pd.get_dummies(df_clean[entity_col], prefix='_entity', drop_first=True)
    X = pd.concat([df_clean[available_x], dummies], axis=1)
    X = sm.add_constant(X)
    Y = df_clean[dep_var]
    model = sm.OLS(Y, X).fit()
    print("\\n===== 固定效应模型（LSDV回退）结果 =====")
    print(model.summary().as_text())
    result = {{
        "method": "LSDV (固定效应回退)",
        "n_obs": int(model.nobs),
        "r_squared": round(model.rsquared, 4),
        "adj_r_squared": round(model.rsquared_adj, 4),
        "coefficients": {{
            name: {{"coef": round(float(model.params[name]), 6), "pvalue": round(float(model.pvalues[name]), 6)}}
            for name in model.params.index if not name.startswith('_entity')
        }},
    }}

# ========== 第6步：可视化 ==========
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. 各城市碳排放趋势图
city_trend = df_clean.reset_index().pivot_table(values=dep_var, index=time_col, columns=entity_col, aggfunc='sum')
city_trend.plot(ax=axes[0, 0], marker='o', markersize=3, alpha=0.7)
axes[0, 0].set_xlabel(time_col)
axes[0, 0].set_ylabel(dep_var)
axes[0, 0].set_title('各城市 {{dep_var}} 趋势')
axes[0, 0].legend(fontsize=6, loc='best')
axes[0, 0].grid(True, alpha=0.3)

# 2. 回归系数条形图（不含城市虚拟变量）
coef_names = [n for n in model.params.index if not n.startswith('_entity')]
coef_vals = [float(model.params[n]) for n in coef_names]
colors_fe = ['green' if model.pvalues[n] < 0.05 else 'gray' for n in coef_names]
axes[0, 1].barh(coef_names, coef_vals, color=colors_fe, alpha=0.7)
axes[0, 1].set_xlabel('系数')
axes[0, 1].set_title('固定效应模型系数')
axes[0, 1].axvline(x=0, color='red', linestyle='--', alpha=0.5)
    for i, (v, p) in enumerate(zip(coef_vals, [float(model.pvalues[n]) for n in coef_names])):
        axes[0, 1].text(v, i, f'p={{p:.3f}}', va='center', fontsize=8)

# 3. 省级总量趋势
province_trend = df_clean.reset_index().groupby(time_col)[dep_var].sum()
axes[1, 0].plot(province_trend.index, province_trend.values, 'bo-', markersize=5)
axes[1, 0].set_xlabel(time_col)
axes[1, 0].set_ylabel(dep_var)
axes[1, 0].set_title('浙江省 {{dep_var}} 总量趋势')
axes[1, 0].grid(True, alpha=0.3)

# 4. 系数显著性饼图
sig_count = sum(1 for n in coef_names if float(model.pvalues[n]) < 0.05)
not_sig = len(coef_names) - sig_count
axes[1, 1].pie([sig_count, not_sig], labels=['显著 (p<0.05)', '不显著'], autopct='%1.0f%%', colors=['#2ecc71', '#95a5a6'])
axes[1, 1].set_title('系数显著性分布')

plt.tight_layout()
plt.savefig('panel_fe_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: panel_fe_results.png")

# ========== 第7步：输出结构化结果 ==========
print("\\n===== 结构化结果 (JSON) =====")
print(json.dumps(result, ensure_ascii=False, indent=2))
'''
    plan = ["读取面板数据", "准备变量和面板结构", "数据清洗", "描述性统计", "固定效应回归", "可视化图表", "输出结构化结果"]
    bindings = [
        EvidenceBinding(step=5, operation="Panel FE 固定效应回归", evidence_chunk_id=ev_id, line_numbers=[41, 42, 43, 44]),
    ]
    return code, plan, bindings


def _template_did(
    *, filename: str, dep_var: str, x_list_str: str,
    entity_col: str, time_col: str, ev_id: str | None,
) -> tuple[str, list[str], list[EvidenceBinding]]:
    code = f'''\
import pandas as pd
import numpy as np
import statsmodels.api as sm
import json

# ========== 第1步：读取数据 ==========
df = pd.read_csv('{filename}')
print(f"数据形状: {{df.shape}}")

# ========== 第2步：准备变量 ==========
dep_var = '{dep_var}'
x_vars = {x_list_str}
entity_col = '{entity_col}'
time_col = '{time_col}'

available_x = [v for v in x_vars if v in df.columns]
if dep_var not in df.columns:
    raise ValueError(f"因变量 '{{dep_var}}' 不在数据列中。")

# ========== 第3步：DID 交互项 ==========
# 需要处理组(treated)和政策时间(post)变量
# 自动检测: 如果 x_vars 中有类似 treated/post 的列
did_candidates = [v for v in available_x if any(k in v.lower() for k in ['treat', 'post', 'policy', 'reform', 'did'])]
if len(did_candidates) >= 2:
    treat_var = did_candidates[0]
    post_var = did_candidates[1]
    df['did_interaction'] = df[treat_var] * df[post_var]
    print(f"DID 交互项: {{treat_var}} x {{post_var}}")
else:
    print("警告: 未自动识别到处理组/政策时间变量，使用全部自变量进行回归")
    treat_var = None
    post_var = None

# ========== 第4步：数据清洗 ==========
cols_needed = [dep_var, entity_col, time_col] + available_x
if 'did_interaction' in df.columns:
    cols_needed.append('did_interaction')
df_clean = df[[c for c in cols_needed if c in df.columns]].dropna()
print(f"清洗后样本量: {{len(df_clean)}}")

# ========== 第5步：DID 回归 ==========
Y = df_clean[dep_var]
x_cols = available_x.copy()
if 'did_interaction' in df_clean.columns:
    x_cols.append('did_interaction')
X = sm.add_constant(df_clean[x_cols])
model = sm.OLS(Y, X).fit(cov_type='cluster', cov_kwds={{'groups': df_clean[entity_col]}})
print("\\n===== DID 回归结果 =====")
print(model.summary().as_text())

# ========== 第6步：可视化 ==========
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 1. DID 系数条形图
coef_names = list(model.params.index)
coef_vals = [float(model.params[n]) for n in coef_names]
colors_did = ['#e74c3c' if 'did_interaction' in n else ('#3498db' if 'post' in n or 'treat' in n else '#95a5a6') for n in coef_names]
axes[0].barh(coef_names, coef_vals, color=colors_did, alpha=0.7)
axes[0].set_xlabel('系数')
axes[0].set_title('DID 回归系数')
axes[0].axvline(x=0, color='red', linestyle='--', alpha=0.5)

# 标注显著性
for i, (v, n) in enumerate(zip(coef_vals, coef_names)):
    pval = float(model.pvalues[n])
    sig = '***' if pval < 0.01 else '**' if pval < 0.05 else '*' if pval < 0.1 else ''
    axes[0].text(v, i, f'{{sig}}p={pval:.3f}', va='center', fontsize=8)

# 2. 处理组 vs 对照组趋势对比
if treat_var and post_var and entity_col in df_clean.columns:
    df_viz = df_clean.reset_index()
    treated = df_viz.groupby(time_col)[dep_var].mean() if 'treated' in treat_var.lower() or 'treat' in treat_var.lower() else None
    if treated is not None:
        ctrl_mask = df_viz[treat_var] == 0 if treat_var in df_viz.columns else pd.Series(True, index=df_viz.index)
        control = df_viz[ctrl_mask].groupby(time_col)[dep_var].mean()
        axes[1].plot(treated.index, treated.values, 'r-', label='处理组', linewidth=2)
        axes[1].plot(control.index, control.values, 'b--', label='对照组', linewidth=2)
        axes[1].set_xlabel(time_col)
        axes[1].set_ylabel(dep_var)
        axes[1].set_title('处理组 vs 对照组趋势')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
    else:
        axes[1].text(0.5, 0.5, '处理组数据不足', ha='center', va='center', transform=axes[1].transAxes)
else:
    axes[1].text(0.5, 0.5, '趋势数据不可用', ha='center', va='center', transform=axes[1].transAxes)

plt.tight_layout()
plt.savefig('did_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: did_results.png")

# ========== 第7步：输出结构化结果 ==========
result = {{
    "method": "DID (双重差分)",
    "n_obs": int(model.nobs),
    "r_squared": round(model.rsquared, 4),
    "coefficients": {{
        name: {{"coef": round(float(model.params[name]), 6), "pvalue": round(float(model.pvalues[name]), 6)}}
        for name in model.params.index
    }},
    "did_interaction_coef": round(float(model.params.get('did_interaction', 0)), 6) if 'did_interaction' in model.params.index else None,
}}
print("\\n===== 结构化结果 (JSON) =====")
print(json.dumps(result, ensure_ascii=False, indent=2))
'''
    plan = ["读取数据", "准备变量", "构建 DID 交互项", "数据清洗", "DID 回归(聚类标准误)", "可视化图表", "输出结构化结果"]
    bindings = [
        EvidenceBinding(step=5, operation="DID 双重差分回归", evidence_chunk_id=ev_id, line_numbers=[47, 48, 49, 50]),
    ]
    return code, plan, bindings


def _template_stirpat(
    *, filename: str, dep_var: str, x_list_str: str,
    entity_col: str, time_col: str, has_panel: bool, ev_id: str | None,
) -> tuple[str, list[str], list[EvidenceBinding]]:
    code = f'''\
import pandas as pd
import numpy as np
import statsmodels.api as sm
import json

# ========== 第1步：读取数据 ==========
df = pd.read_csv('{filename}')
print(f"数据形状: {{df.shape}}")

# ========== 第2步：准备变量 ==========
dep_var = '{dep_var}'
x_vars = {x_list_str}
entity_col = '{entity_col}'
time_col = '{time_col}'

available_x = [v for v in x_vars if v in df.columns]
if dep_var not in df.columns:
    raise ValueError(f"因变量 '{{dep_var}}' 不在数据列中。")

# ========== 第3步：STIRPAT 对数变换 ==========
# STIRPAT: ln(I) = a + b*ln(P) + c*ln(A) + d*ln(T) + e
# 对所有变量取自然对数（要求正值）
cols_to_log = [dep_var] + available_x
for col in cols_to_log:
    if col in df.columns:
        if (df[col] <= 0).any():
            min_pos = df[col][df[col] > 0].min() if (df[col] > 0).any() else 1
            df[f'ln_{{col}}'] = np.log(df[col].clip(lower=min_pos * 0.01))
            print(f"警告: {{col}} 含非正值，已 clip 处理后取对数")
        else:
            df[f'ln_{{col}}'] = np.log(df[col])

ln_dep = f'ln_{{dep_var}}'
ln_x = [f'ln_{{v}}' for v in available_x if f'ln_{{v}}' in df.columns]
print(f"对数因变量: {{ln_dep}}")
print(f"对数自变量: {{ln_x}}")

# ========== 第4步：数据清洗 ==========
all_cols = [ln_dep] + ln_x
if entity_col and entity_col in df.columns:
    all_cols += [entity_col]
if time_col and time_col in df.columns:
    all_cols += [time_col]
df_clean = df[all_cols].dropna()
print(f"清洗后样本量: {{len(df_clean)}}")

# ========== 第5步：STIRPAT 回归 ==========
Y = df_clean[ln_dep]
X = sm.add_constant(df_clean[ln_x])
model = sm.OLS(Y, X).fit()
print("\\n===== STIRPAT 回归结果 =====")
print(model.summary().as_text())

# ========== 第6步：弹性解读 ==========
print("\\n===== 弹性系数解读 =====")
for var in ln_x:
    original = var.replace('ln_', '')
    coef = model.params[var]
    pval = model.pvalues[var]
    sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
    print(f"  {{original}}: 弹性 = {{coef:.4f}}{{sig}} ({{original}} 增加1%，{{dep_var}} 变化约 {{coef:.4f}}%)")

# ========== 第7步：可视化 ==========
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 1. 弹性系数条形图
orig_names = [v.replace('ln_', '') for v in ln_x]
elasticities = [float(model.params[v]) for v in ln_x]
pvalues = [float(model.pvalues[v]) for v in ln_x]
colors_sp = ['#e74c3c' if p < 0.05 else '#95a5a6' for p in pvalues]
axes[0].barh(orig_names, elasticities, color=colors_sp, alpha=0.7)
axes[0].set_xlabel('弹性系数')
axes[0].set_title('STIRPAT 弹性系数 (p<0.05 红色)')
axes[0].axvline(x=0, color='red', linestyle='--', alpha=0.5)
for i, (e, p) in enumerate(zip(elasticities, pvalues)):
    sig = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''
    axes[0].text(e, i, f'{{sig}} {{e:.3f}}', va='center', fontsize=9)

# 2. 实际值 vs 预测值
if len(df_clean) <= 2000:
    y_pred = model.predict(X)
    y_actual = Y.values
    axes[1].scatter(y_actual, y_pred, alpha=0.5, s=20, color='#3498db')
    min_val = min(y_actual.min(), y_pred.min())
    max_val = max(y_actual.max(), y_pred.max())
    axes[1].plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='理想拟合线')
    axes[1].set_xlabel('实际值 (ln)')
    axes[1].set_ylabel('预测值 (ln)')
    axes[1].set_title('STIRPAT 实际 vs 预测')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('stirpat_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存: stirpat_results.png")

# ========== 第8步：输出结构化结果 ==========
result = {{
    "method": "STIRPAT",
    "n_obs": int(model.nobs),
    "r_squared": round(model.rsquared, 4),
    "adj_r_squared": round(model.rsquared_adj, 4),
    "elasticities": {{
        var.replace('ln_', ''): {{
            "elasticity": round(float(model.params[var]), 6),
            "pvalue": round(float(model.pvalues[var]), 6),
        }}
        for var in ln_x
    }},
}}
print("\\n===== 结构化结果 (JSON) =====")
print(json.dumps(result, ensure_ascii=False, indent=2))
'''
    plan = ["读取数据", "准备变量", "STIRPAT 对数变换", "数据清洗", "STIRPAT 回归", "弹性系数解读", "可视化图表", "输出结构化结果"]
    bindings = [
        EvidenceBinding(step=3, operation="STIRPAT 对数变换 (ln(I) = a + b*ln(P) + ...)", evidence_chunk_id=ev_id, line_numbers=[23, 24, 25]),
        EvidenceBinding(step=5, operation="STIRPAT OLS 回归", evidence_chunk_id=ev_id, line_numbers=[47, 48, 49]),
    ]
    return code, plan, bindings


# ---------------------------------------------------------------------------
# 3. Bridge 完整流程
# ---------------------------------------------------------------------------

def run_bridge(state: dict[str, Any]) -> dict[str, Any]:
    """Text-to-Code Bridge 完整执行流程.

    Returns:
        dict with keys: evidence_package, generated_code, check_result,
        execution_result, bridge_status, bridge_error
    """
    # Step 1: 提取证据
    evidence = extract_evidence(state)

    # Step 2: 生成代码
    generated = generate_code(state, evidence)

    # Step 3: 安全检查
    check_result = check_code(generated.code_script)
    generated.check_result = check_result

    if not check_result.passed:
        return {
            "evidence_package": evidence.to_dict(),
            "generated_code": generated.to_dict(),
            "check_result": check_result.to_dict(),
            "execution_result": None,
            "bridge_status": "check_failed",
            "bridge_error": "; ".join(check_result.errors),
        }

    # Step 4: 沙箱执行
    data_files = state.get("data_files") or []
    exec_result = execute_in_sandbox(
        code=generated.code_script,
        data_files=data_files,
        timeout=60,
    )

    return {
        "evidence_package": evidence.to_dict(),
        "generated_code": generated.to_dict(),
        "check_result": check_result.to_dict(),
        "execution_result": exec_result.to_dict(),
        "bridge_status": "success" if exec_result.success else "execution_failed",
        "bridge_error": exec_result.error_message,
    }
