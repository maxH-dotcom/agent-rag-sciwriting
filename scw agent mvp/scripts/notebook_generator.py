"""
Notebook 生成模块 - 使用 nbformat 生成 Colab notebook
"""

import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
from typing import TypedDict, List

from model_recommender import ModelRecommendation
from literature_retriever import LiteratureChunk


class NotebookConfig(TypedDict):
    title: str
    dependent_var: str
    independent_vars: List[str]
    control_vars: List[str]
    model_recommendation: ModelRecommendation
    literature_chunks: list[LiteratureChunk]
    data_file: str
    panel_dimensions: dict


def generate_notebook(config: NotebookConfig) -> nbformat.NotebookNode:
    """
    生成 Colab notebook

    Args:
        config: Notebook 配置

    Returns:
        nbformat NotebookNode
    """
    model = config["model_recommendation"]
    dep_var = config["dependent_var"]
    indep_vars = config["independent_vars"]
    control_vars = config["control_vars"]
    chunks = config["literature_chunks"]
    data_file = config["data_file"]

    nb = new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.11.0",
        },
    }

    cells = []

    # 1. 标题
    cells.append(new_markdown_cell(f"# {config['title']}"))

    # 2. 研究问题描述
    vars_text = " + ".join(indep_vars)
    control_text = f", 控制变量: {', '.join(control_vars)}" if control_vars else ""
    cells.append(
        new_markdown_cell(
            f"**研究问题**: 分析 {vars_text} 对 {dep_var} 的影响{control_text}\n\n"
            f"**推荐模型**: {model['model_name']}"
        )
    )

    # 3. 文献依据
    cells.append(new_markdown_cell("## 文献依据"))
    for chunk in chunks[:3]:
        cells.append(
            new_markdown_cell(
                f"- **{chunk['source_file']}** ({chunk['page_ref']}): {chunk['text'][:200]}..."
            )
        )

    # 4. 安装依赖
    cells.append(new_markdown_cell("## 安装依赖"))
    install_code = "!pip install linearmodels pandas openpyxl statsmodels"
    cells.append(new_code_cell(install_code))

    # 5. 导入库
    cells.append(new_markdown_cell("## 导入库"))
    import_code = """import pandas as pd
import numpy as np
from linearmodels.panel import PanelOLS
import statsmodels.api as sm"""
    cells.append(new_code_cell(import_code))

    # 6. 加载数据
    cells.append(new_markdown_cell("## 加载数据"))
    load_code = f"""# 加载数据（请确保 CSV 文件与本 notebook 在同一目录）
df = pd.read_csv('{data_file}')
print(f"数据形状: {{df.shape}}")
print(f"列名: {{list(df.columns)}}")
df.head()"""
    cells.append(new_code_cell(load_code))

    # 7. 数据预处理
    cells.append(new_markdown_cell("## 数据预处理"))
    preprocess_code = """# 检查缺失值
print("缺失值统计:")
print(df.isnull().sum())

# 描述性统计
df[['碳排放总量 10*3t', '农业产值 亿元']].describe()"""
    cells.append(new_code_cell(preprocess_code))

    # 8. 根据模型生成代码
    model_code = config["model_recommendation"]["model_code"]

    if model_code == "PanelOLS":
        # 固定效应模型
        cells.append(new_markdown_cell("## 固定效应回归"))

        all_vars = indep_vars + control_vars
        exog_vars = "', '".join(all_vars)

        reg_code = f"""# 设置面板索引
df_panel = df.set_index(['地区', '年份'])

# 准备变量
endog = df_panel['{dep_var}']
exog = df_panel[['{' '.join(all_vars)}']]

# 添加常数项
exog = sm.add_constant(exog)

# 固定效应回归（within transformation）
model = PanelOLS(endog, exog, entity_effects=True, time_effects=False)
result = model.fit(cov_type='clustered', cluster_entity=True)

print(result.summary)"""
        cells.append(new_code_cell(reg_code))

    elif model_code == "DID":
        # 双重差分
        cells.append(new_markdown_cell("## 双重差分 (DID) 回归"))
        did_code = """# DID 需要明确的政策实施时间点
# 请设置政策实施年份
POLICY_YEAR = 2015  # 修改为实际政策年份

# 生成处理组标识和时间标识
df['treated'] = (df['地区'].isin(['处理组城市'])).astype(int)  # 修改为实际处理组
df['post'] = (df['年份'] >= POLICY_YEAR).astype(int)
df['did'] = df['treated'] * df['post']

# DID 回归
reg = sm.OLS(df['{dep_var}'], sm.add_constant(df[['did', 'treated', 'post']])).fit()
print(reg.summary())""".format(dep_var=dep_var)
        cells.append(new_code_cell(did_code))

    elif model_code == "OLS":
        # OLS 回归
        cells.append(new_markdown_cell("## OLS 回归"))
        all_vars = indep_vars + control_vars
        ols_code = f"""# OLS 回归
X = df[['{"', '".join(all_vars)}']]
X = sm.add_constant(X)
y = df['{dep_var}']

model = sm.OLS(y, X).fit()
print(model.summary())"""
        cells.append(new_code_cell(ols_code))

    elif model_code == "ARIMA":
        # 时间序列
        cells.append(new_markdown_cell("## ARIMA 时间序列分析"))
        arima_code = f"""from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# 单变量时间序列（选择第一个地区）
ts_data = df[df['地区'] == df['地区'].unique()[0]]['{dep_var}'].dropna()

# ARIMA 模型
model = ARIMA(ts_data, order=(1, 1, 1))
result = model.fit()
print(result.summary())

# 预测
forecast = result.forecast(steps=5)
print("未来5期预测值:")
print(forecast)"""
        cells.append(new_code_cell(arima_code))

    else:
        # 通用回归
        cells.append(new_markdown_cell("## 回归分析"))
        gen_code = f"""# 回归分析
all_vars = {indep_vars + control_vars}
X = df[['{' '.join(all_vars)}']]
X = sm.add_constant(X)
y = df['{dep_var}']

model = sm.OLS(y, X).fit()
print(model.summary())"""
        cells.append(new_code_cell(gen_code))

    # 9. 结果解释
    cells.append(new_markdown_cell("## 结果解释"))
    cells.append(
        new_markdown_cell(
            f"""**注意**: 本 notebook 由 AI 自动生成，代码和结论可能需要人工验证。

关键步骤:
1. 固定效应模型控制了地区层面的不可观测异质性
2. 聚类标准误考虑了地区层面的序列相关
3. 如有内生性问题，建议使用工具变量法或双重差分

**参考文献**:
{model['文献出处']}"""
        )
    )

    nb.cells = cells
    return nb


def save_notebook(nb: nbformat.NotebookNode, output_path: str) -> None:
    """保存 notebook 到文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Notebook 已保存: {output_path}")
