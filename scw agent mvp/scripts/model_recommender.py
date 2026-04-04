"""
模型推荐引擎 - 基于规则映射表
"""

from typing import TypedDict, Literal, List


class ModelRecommendation(TypedDict):
    model_name: str
    model_code: str
    适用条件: str
    文献依据: str
    文献出处: str
    confidence: float


# 领域规则映射表
MODEL_RULES: list[dict] = [
    {
        "研究问题类型": "面板数据，X对Y影响",
        "推荐模型": "固定效应模型 (FE)",
        "model_code": "PanelOLS",
        "适用条件": "不可观测的异质性，需要控制地区或时间固定效应",
        "文献依据": "The fixed effects estimator controls for all time-invariant characteristics of the entity",
        "文献出处": "Wooldridge, Econometric Analysis of Cross Section and Panel Data, 2002, p.312",
    },
    {
        "研究问题类型": "面板数据 + 政策冲击",
        "推荐模型": "双重差分 (DID)",
        "model_code": "DID",
        "适用条件": "有明确的政策实施时间点，需要评估政策效果",
        "文献依据": "The difference-in-differences estimator compares the changes in outcomes over time between a treatment and control group",
        "文献出处": "Angrist & Pischke, Mostly Harmless Econometrics, 2009, Ch. 5",
    },
    {
        "研究问题类型": "时间序列预测",
        "推荐模型": "ARIMA / Holt-Winters",
        "model_code": "ARIMA",
        "适用条件": "单变量时间序列，需要预测未来趋势",
        "文献依据": "ARIMA models combine autoregression with moving averages for time series forecasting",
        "文献出处": "Box & Jenkins, Time Series Analysis, 1976",
    },
    {
        "研究问题类型": "截面数据，X对Y影响",
        "推荐模型": "OLS 回归",
        "model_code": "OLS",
        "适用条件": "横截面数据，不同时序或面板结构",
        "文献依据": "OLS provides the best linear unbiased estimator under classical assumptions",
        "文献出处": "Stock & Watson, Introduction to Econometrics, 2019, Ch. 4",
    },
    {
        "研究问题类型": "面板数据，随机效应",
        "推荐模型": "随机效应模型 (RE)",
        "model_code": "PanelOLS_random",
        "适用条件": "假设个体效应与解释变量不相关，可使用随机效应",
        "文献依据": "Random effects assumes the individual-specific effect is uncorrelated with the regressors",
        "文献出处": "Baltagi, Econometric Analysis of Panel Data, 2005, Ch. 2",
    },
    {
        "研究问题类型": "空间面板数据",
        "推荐模型": "空间杜宾模型 (SDM)",
        "model_code": "SDM",
        "适用条件": "存在空间相关性，需要考虑空间溢出效应",
        "文献依据": "The spatial Durbin model accounts for both dependent and independent variable spatial spillovers",
        "文献出处": "LeSage & Pace, Introduction to Spatial Econometrics, 2009",
    },
]


def recommend_models(
    data_structure: Literal["panel", "cross_section", "time_series"],
    has_policy_shock: bool = False,
    has_spatial_effect: bool = False,
) -> list[ModelRecommendation]:
    """
    根据数据结构和建议类型推荐模型

    Args:
        data_structure: 数据结构 (panel/cross_section/time_series)
        has_policy_shock: 是否有政策冲击
        has_spatial_effect: 是否有空间效应

    Returns:
        推荐的模型列表
    """
    recommendations = []

    if data_structure == "panel":
        if has_policy_shock:
            recommendations.append({
                "model_name": "双重差分 (DID)",
                "model_code": "DID",
                "适用条件": "有明确的政策实施时间点，需要评估政策效果",
                "文献依据": "The difference-in-differences estimator compares the changes in outcomes over time between a treatment and control group",
                "文献出处": "Angrist & Pischke, Mostly Harmless Econometrics, 2009, Ch. 5",
                "confidence": 0.9,
            })

        if has_spatial_effect:
            recommendations.append({
                "model_name": "空间杜宾模型 (SDM)",
                "model_code": "SDM",
                "适用条件": "存在空间相关性，需要考虑空间溢出效应",
                "文献依据": "The spatial Durbin model accounts for both dependent and independent variable spatial spillovers",
                "文献出处": "LeSage & Pace, Introduction to Spatial Econometrics, 2009",
                "confidence": 0.85,
            })

        # 默认推荐固定效应
        recommendations.append({
            "model_name": "固定效应模型 (FE)",
            "model_code": "PanelOLS",
            "适用条件": "不可观测的异质性，需要控制地区或时间固定效应",
            "文献依据": "The fixed effects estimator controls for all time-invariant characteristics of the entity",
            "文献出处": "Wooldridge, Econometric Analysis of Cross Section and Panel Data, 2002, p.312",
            "confidence": 0.88,
        })

        # 随机效应作为备选
        recommendations.append({
            "model_name": "随机效应模型 (RE)",
            "model_code": "PanelOLS_random",
            "适用条件": "假设个体效应与解释变量不相关",
            "文献依据": "Random effects assumes the individual-specific effect is uncorrelated with the regressors",
            "文献出处": "Baltagi, Econometric Analysis of Panel Data, 2005, Ch. 2",
            "confidence": 0.7,
        })

    elif data_structure == "time_series":
        recommendations.append({
            "model_name": "ARIMA / Holt-Winters",
            "model_code": "ARIMA",
            "适用条件": "单变量时间序列，需要预测未来趋势",
            "文献依据": "ARIMA models combine autoregression with moving averages for time series forecasting",
            "文献出处": "Box & Jenkins, Time Series Analysis, 1976",
            "confidence": 0.85,
        })

    elif data_structure == "cross_section":
        recommendations.append({
            "model_name": "OLS 回归",
            "model_code": "OLS",
            "适用条件": "横截面数据，不同时序或面板结构",
            "文献依据": "OLS provides the best linear unbiased estimator under classical assumptions",
            "文献出处": "Stock & Watson, Introduction to Econometrics, 2019, Ch. 4",
            "confidence": 0.85,
        })

    return recommendations


def infer_data_structure(df) -> tuple[str, dict]:
    """
    根据数据特征推断数据结构

    Returns:
        (data_structure, panel_dimensions)
    """
    columns = [c for c in df.columns if c not in ['年份', '地区', '地区·代码']]

    # 检查是否有重复的地区和年份（面板数据特征）
    if '年份' in df.columns and '地区' in df.columns:
        unique_years = df['年份'].nunique()
        unique_entities = df['地区'].nunique()
        total_rows = len(df)

        # 如果 year * entity 接近行数，则是面板数据
        if unique_years * unique_entities >= total_rows * 0.8:
            return "panel", {
                "entity": "地区",
                "time": "年份",
                "n_entities": unique_entities,
                "n_periods": unique_years
            }

    # 检查是否有明显的时间序列特征
    if '年份' in df.columns and df['年份'].nunique() > 5:
        if '地区' not in df.columns or df['地区'].nunique() == 1:
            return "time_series", {}

    return "cross_section", {}
