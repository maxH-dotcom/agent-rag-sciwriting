from __future__ import annotations


def recommend_models(has_panel_structure: bool) -> list[dict[str, str | float]]:
    if has_panel_structure:
        return [
            {
                "model_name": "固定效应模型 (FE)",
                "model_code": "PanelOLS",
                "reason": "当前数据具备地区-年份面板结构，先用可解释、稳妥的基线模型。",
                "confidence": 0.88,
            },
            {
                "model_name": "双重差分 (DID)",
                "model_code": "DID",
                "reason": "如果后续识别到政策冲击和处理组，再升级到准实验设计。",
                "confidence": 0.58,
            },
        ]
    return [
        {
            "model_name": "OLS 回归",
            "model_code": "OLS",
            "reason": "当前更像截面数据，先从基础线性模型开始。",
            "confidence": 0.77,
        }
    ]

