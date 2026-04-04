"""
测试文件 - 验证核心流程
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pandas as pd
from model_recommender import recommend_models, infer_data_structure
from parse_question import parse_question_fallback


def test_data_loading():
    """测试数据加载"""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "zhejiang_carbon.csv")
    df = pd.read_csv(data_path)
    assert df.shape[0] == 289
    assert df.shape[1] == 18
    print(f"数据加载测试通过: {df.shape}")


def test_data_structure_inference():
    """测试数据结构推断"""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "zhejiang_carbon.csv")
    df = pd.read_csv(data_path)

    structure, dims = infer_data_structure(df)
    assert structure == "panel"
    assert dims["entity"] == "地区"
    assert dims["time"] == "年份"
    print(f"数据结构推断测试通过: {structure}, {dims}")


def test_model_recommendation():
    """测试模型推荐"""
    recs = recommend_models("panel", has_policy_shock=False)
    assert len(recs) >= 2
    assert recs[0]["model_name"] == "固定效应模型 (FE)"
    print(f"模型推荐测试通过: {len(recs)} 个模型")


def test_question_parsing():
    """测试问题解析"""
    question = "我想分析农业产值对碳排放的影响，同时控制农药使用量"
    cols = ['年份', '地区', '碳排放总量 10*3t', '农业产值 亿元', '农药\n使用量\n(吨)']

    parsed = parse_question_fallback(question, cols)
    assert "碳排放" in parsed["dependent_var"]
    assert len(parsed["independent_vars"]) > 0
    print(f"问题解析测试通过: {parsed}")


def test_notebook_generation():
    """测试 Notebook 生成"""
    from notebook_generator import generate_notebook

    config = {
        "title": "测试分析",
        "dependent_var": "碳排放总量 10*3t",
        "independent_vars": ["农业产值 亿元"],
        "control_vars": [],
        "model_recommendation": {
            "model_name": "固定效应模型 (FE)",
            "model_code": "PanelOLS",
            "适用条件": "test",
            "文献依据": "test ref",
            "文献出处": "test source",
        },
        "literature_chunks": [],
        "data_file": "zhejiang_carbon.csv",
        "panel_dimensions": {"entity": "地区", "time": "年份"},
    }

    nb = generate_notebook(config)
    assert len(nb.cells) > 0
    print(f"Notebook 生成测试通过: {len(nb.cells)} 个 cell")


if __name__ == "__main__":
    print("运行测试...")
    test_data_loading()
    test_data_structure_inference()
    test_model_recommendation()
    test_question_parsing()
    test_notebook_generation()
    print("\n所有测试通过!")
