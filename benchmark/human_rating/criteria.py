"""
人工评分标准
Human Rating Criteria - 5分制专家评审
"""

from enum import Enum
from typing import Dict


class RatingDimension(str, Enum):
    RELEVANCE = "relevance"           # 相关性
    ACCURACY = "accuracy"             # 准确性
    COMPLETENESS = "completeness"     # 完整性
    COHERENCE = "coherence"           # 连贯性
    CITATION_QUALITY = "citation"     # 引用质量


RATING_CRITERIA: Dict[RatingDimension, Dict[str, str]] = {
    RatingDimension.RELEVANCE: {
        "5": "完全相关，精准命中用户需求",
        "4": "高度相关，只有轻微偏差",
        "3": "中度相关，存在部分偏差",
        "2": "低度相关，大部分不匹配",
        "1": "完全不相关"
    },
    RatingDimension.ACCURACY: {
        "5": "完全准确，无事实错误",
        "4": "基本准确，有微小误差",
        "3": "部分准确，存在明显错误",
        "2": "大部分不准确",
        "1": "完全错误"
    },
    RatingDimension.COMPLETENESS: {
        "5": "完整覆盖所有必要方面",
        "4": "覆盖大部分，只有轻微遗漏",
        "3": "覆盖中等，仍有重要遗漏",
        "2": "覆盖较少",
        "1": "严重缺失"
    },
    RatingDimension.COHERENCE: {
        "5": "逻辑清晰，行文流畅",
        "4": "基本流畅，有轻微跳跃",
        "3": "中等连贯，存在逻辑问题",
        "2": "较不连贯",
        "1": "混乱不堪"
    },
    RatingDimension.CITATION: {
        "5": "引用精准，完全可追溯",
        "4": "引用基本准确",
        "3": "引用有偏差",
        "2": "引用大多不准确",
        "1": "无引用或完全错误"
    }
}


def calculate_overall_score(ratings: Dict[str, int]) -> float:
    """
    计算加权总分 (0-1)
    权重: 准确性 30%, 相关性 25%, 完整性 20%, 引用 15%, 连贯性 10%
    """
    weights = {
        RatingDimension.RELEVANCE.value: 0.25,
        RatingDimension.ACCURACY.value: 0.30,
        RatingDimension.COMPLETENESS.value: 0.20,
        RatingDimension.COHERENCE.value: 0.10,
        RatingDimension.CITATION.value: 0.15
    }

    total = 0.0
    for dim, weight in weights.items():
        score = ratings.get(dim, 3)
        total += score * weight

    return total / 5.0  # 归一化到 0-1
