from __future__ import annotations

from typing import Literal


# ---------------------------------------------------------------------------
# 模型规则库（来自 scw agent mvp — 增量合并）
# ---------------------------------------------------------------------------

MODEL_RULES: list[dict] = [
    {
        "model_name": "固定效应模型 (FE)",
        "model_code": "PanelOLS",
        "适用条件": "不可观测的异质性，需要控制地区或时间固定效应",
        "文献依据": "The fixed effects estimator controls for all time-invariant characteristics of the entity",
        "文献出处": "Wooldridge, Econometric Analysis of Cross Section and Panel Data, 2002, p.312",
        "研究问题类型": "面板数据，X对Y影响",
    },
    {
        "model_name": "双重差分 (DID)",
        "model_code": "DID",
        "适用条件": "有明确的政策实施时间点，需要评估政策效果",
        "文献依据": "The difference-in-differences estimator compares the changes in outcomes over time between a treatment and control group",
        "文献出处": "Angrist & Pischke, Mostly Harmless Econometrics, 2009, Ch. 5",
        "研究问题类型": "面板数据 + 政策冲击",
    },
    {
        "model_name": "随机效应模型 (RE)",
        "model_code": "PanelOLS_random",
        "适用条件": "假设个体效应与解释变量不相关，可使用随机效应",
        "文献依据": "Random effects assumes the individual-specific effect is uncorrelated with the regressors",
        "文献出处": "Baltagi, Econometric Analysis of Panel Data, 2005, Ch. 2",
        "研究问题类型": "面板数据，随机效应",
    },
    {
        "model_name": "ARIMA / Holt-Winters",
        "model_code": "ARIMA",
        "适用条件": "单变量时间序列，需要预测未来趋势",
        "文献依据": "ARIMA models combine autoregression with moving averages for time series forecasting",
        "文献出处": "Box & Jenkins, Time Series Analysis, 1976",
        "研究问题类型": "时间序列预测",
    },
    {
        "model_name": "OLS 回归",
        "model_code": "OLS",
        "适用条件": "横截面数据，不同时序或面板结构",
        "文献依据": "OLS provides the best linear unbiased estimator under classical assumptions",
        "文献出处": "Stock & Watson, Introduction to Econometrics, 2019, Ch. 4",
        "研究问题类型": "截面数据，X对Y影响",
    },
    {
        "model_name": "空间杜宾模型 (SDM)",
        "model_code": "SDM",
        "适用条件": "存在空间相关性，需要考虑空间溢出效应",
        "文献依据": "The spatial Durbin model accounts for both dependent and independent variable spatial spillovers",
        "文献出处": "LeSage & Pace, Introduction to Spatial Econometrics, 2009",
        "研究问题类型": "空间面板数据",
    },
    {
        "model_name": "STIRPAT 模型",
        "model_code": "STIRPAT",
        "适用条件": "碳排放驱动因素分解，弹性估计，非线性关系",
        "文献依据": "The STIRPAT model allows testing of the equality of error variances across groups",
        "文献出处": "Dietz & Rosa, Review of Social Economy, 1997",
        "研究问题类型": "环境经济学/碳排放",
    },
]


# ---------------------------------------------------------------------------
# 数据结构推断（来自 scw agent mvp — 增量合并）
# ---------------------------------------------------------------------------

def infer_data_structure(df) -> tuple[Literal["panel", "cross_section", "time_series"], dict]:
    """
    根据数据 DataFrame 特征推断数据结构。

    Returns:
        (data_structure, panel_dimensions)
        data_structure: "panel" | "cross_section" | "time_series"
        panel_dimensions: {"entity": str, "time": str, "n_entities": int, "n_periods": int}
    """
    columns = [c for c in df.columns if c not in ("年份", "地区", "地区·代码")]

    # 检查面板数据特征
    if "年份" in df.columns and "地区" in df.columns:
        unique_years = df["年份"].nunique()
        unique_entities = df["地区"].nunique()
        total_rows = len(df)

        # 如果 year * entity 接近行数，则是面板数据
        if unique_years * unique_entities >= total_rows * 0.8:
            return "panel", {
                "entity": "地区",
                "time": "年份",
                "n_entities": int(unique_entities),
                "n_periods": int(unique_years),
            }

    # 检查时间序列特征
    if "年份" in df.columns and df["年份"].nunique() > 5:
        if "地区" not in df.columns or df["地区"].nunique() == 1:
            return "time_series", {}

    return "cross_section", {}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def recommend_models_by_method_preference(
    method_preference: str,
    has_panel_structure: bool = False,
) -> list[dict]:
    """
    根据用户指定的方法偏好推荐模型.

    Args:
        method_preference: 方法偏好类型 ("时间序列" / "面板回归" / "机器学习")
        has_panel_structure: 是否有面板数据结构

    Returns:
        推荐模型列表，每项包含 model_name, model_code, reason, 文献依据, 文献出处, confidence
    """
    if method_preference == "时间序列":
        return [
            {
                "model_name": "ARIMA / Holt-Winters",
                "model_code": "ARIMA",
                "reason": "单变量时间序列，适合预测未来趋势",
                "文献依据": MODEL_RULES[3]["文献依据"],
                "文献出处": MODEL_RULES[3]["文献出处"],
                "confidence": 0.9,
            },
            {
                "model_name": "SARIMA (季节ARIMA)",
                "model_code": "SARIMA",
                "reason": "具有季节性成分的时间序列数据",
                "文献依据": "Seasonal ARIMA models extend ARIMA with seasonal differencing and seasonal AR/MA terms",
                "文献出处": "Hyndman & Athanasopoulos, Forecasting: Principles and Practice, 2018",
                "confidence": 0.85,
            },
            {
                "model_name": "Prophet",
                "model_code": "Prophet",
                "reason": "业务场景时间序列，有假期效应和季节性分解",
                "文献依据": "Prophet enables analysts to produce forecasts without deep technical knowledge",
                "文献出处": "Taylor & Letham, PeerJ Preprints, 2017",
                "confidence": 0.8,
            },
        ]

    elif method_preference == "面板回归":
        return recommend_models(has_panel_structure)

    elif method_preference == "机器学习":
        return [
            {
                "model_name": "XGBoost",
                "model_code": "XGBoost",
                "reason": "高精度预测，可处理非线性关系和特征交互",
                "文献依据": "XGBoost achieves state-of-the-art results on many regression tasks",
                "文献出处": "Chen & Guestrin, KDD 2016",
                "confidence": 0.9,
            },
            {
                "model_name": "Random Forest",
                "model_code": "RandomForest",
                "reason": "高维特征空间，需要特征重要性分析",
                "文献依据": "Random forests provide excellent accuracy and feature importance estimation",
                "文献出处": "Breiman, Machine Learning, 2001",
                "confidence": 0.85,
            },
            {
                "model_name": "LSTM",
                "model_code": "LSTM",
                "reason": "长期依赖的时间序列，复杂非线性模式",
                "文献依据": "LSTM networks are designed to learn long-term dependencies",
                "文献出处": "Hochreiter & Schmidhuber, Neural Computation, 1997",
                "confidence": 0.8,
            },
        ]

    return recommend_models(has_panel_structure)


def recommend_models(
    has_panel_structure: bool,
    has_policy_shock: bool = False,
    has_spatial_effect: bool = False,
) -> list[dict]:
    """
    根据数据结构和研究问题推荐合适的计量模型。

    增强版（来自 scw agent mvp — 增量合并）：
    - 使用完整 MODEL_RULES 规则库（6 种模型 + 文献出处）
    - 支持 policy_shock 和 spatial_effect 标志
    - 返回模型推荐理由和文献依据

    Args:
        has_panel_structure: 是否有面板数据结构
        has_policy_shock: 是否有政策冲击（DID 场景）
        has_spatial_effect: 是否有空间溢出效应

    Returns:
        推荐模型列表，每项包含 model_name, model_code, reason, 文献依据, 文献出处, confidence
    """
    recommendations: list[dict] = []

    if has_panel_structure:
        if has_policy_shock:
            recommendations.append({
                "model_name": "双重差分 (DID)",
                "model_code": "DID",
                "reason": "有明确的政策实施时间点，适合评估政策效果",
                "文献依据": MODEL_RULES[1]["文献依据"],
                "文献出处": MODEL_RULES[1]["文献出处"],
                "confidence": 0.9,
            })

        if has_spatial_effect:
            recommendations.append({
                "model_name": "空间杜宾模型 (SDM)",
                "model_code": "SDM",
                "reason": "存在空间相关性，需要考虑空间溢出效应",
                "文献依据": MODEL_RULES[5]["文献依据"],
                "文献出处": MODEL_RULES[5]["文献出处"],
                "confidence": 0.85,
            })

        # 默认推荐固定效应
        recommendations.append({
            "model_name": "固定效应模型 (FE)",
            "model_code": "PanelOLS",
            "reason": "面板数据结构，固定效应可控制地区不可观测异质性",
            "文献依据": MODEL_RULES[0]["文献依据"],
            "文献出处": MODEL_RULES[0]["文献出处"],
            "confidence": 0.88,
        })

        # 随机效应作为备选
        recommendations.append({
            "model_name": "随机效应模型 (RE)",
            "model_code": "PanelOLS_random",
            "reason": "若 Hausman 检验拒绝固定效应，可考虑随机效应",
            "文献依据": MODEL_RULES[2]["文献依据"],
            "文献出处": MODEL_RULES[2]["文献出处"],
            "confidence": 0.7,
        })

    elif "time_series" in str(has_panel_structure):
        recommendations.append({
            "model_name": "ARIMA / Holt-Winters",
            "model_code": "ARIMA",
            "reason": "单变量时间序列，适合预测未来趋势",
            "文献依据": MODEL_RULES[3]["文献依据"],
            "文献出处": MODEL_RULES[3]["文献出处"],
            "confidence": 0.85,
        })

    else:
        recommendations.append({
            "model_name": "OLS 回归",
            "model_code": "OLS",
            "reason": "截面数据，使用普通最小二乘估计",
            "文献依据": MODEL_RULES[4]["文献依据"],
            "文献出处": MODEL_RULES[4]["文献出处"],
            "confidence": 0.85,
        })

    return recommendations

