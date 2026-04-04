"""
科研助手 MVP - 主程序

用法:
    python scripts/main.py                              # 交互模式
    python scripts/main.py "研究问题"                    # 直接运行
    python scripts/main.py "研究问题" --run-local       # 本地直接运行回归
"""

import os
import sys

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from model_recommender import recommend_models, infer_data_structure
from parse_question import parse_question_with_llm
from literature_retriever import retrieve_literature
from notebook_generator import generate_notebook, save_notebook

try:
    from linearmodels.panel import PanelOLS
    import statsmodels.api as sm
    HAS_LINEARMODELS = True
except ImportError:
    HAS_LINEARMODELS = False


def run_regression(df, parsed, model_rec):
    """直接运行回归并输出结果"""
    if not HAS_LINEARMODELS:
        print("错误: 需要安装 linearmodels 和 statsmodels")
        print("运行: pip install linearmodels statsmodels")
        return

    print("\n" + "=" * 60)
    print("开始回归分析...")
    print("=" * 60)

    dep_var = parsed["dependent_var"]
    indep_vars = parsed["independent_vars"]
    control_vars = parsed["control_vars"]
    all_vars = indep_vars + control_vars

    try:
        # 设置面板索引
        df_panel = df.set_index(["地区", "年份"])

        # 转换年份为数值型（linearmodels 要求）
        df_panel = df_panel.reset_index("年份")
        df_panel["年份"] = pd.to_numeric(df_panel["年份"], errors="coerce")
        df_panel = df_panel.set_index("年份", append=True)

        # 删除缺失值
        required_cols = [dep_var] + all_vars
        df_panel = df_panel.dropna(subset=required_cols)

        # 准备变量
        endog = df_panel[dep_var]
        exog = df_panel[all_vars]
        exog = sm.add_constant(exog)

        model_code = model_rec["model_code"]

        if model_code in ["PanelOLS", "PanelOLS_random"]:
            # 固定效应或随机效应
            entity_effects = model_code == "PanelOLS"
            model = PanelOLS(endog, exog, entity_effects=entity_effects)
            result = model.fit(cov_type="clustered", cluster_entity=True)

        elif model_code == "OLS":
            # 普通 OLS
            model = sm.OLS(endog, exog)
            result = model.fit()

        else:
            # 默认用固定效应
            model = PanelOLS(endog, exog, entity_effects=True)
            result = model.fit(cov_type="clustered", cluster_entity=True)

        print("\n" + "=" * 60)
        print("回归结果")
        print("=" * 60)
        print(result.summary)

        # 解读
        print("\n" + "=" * 60)
        print("结果解读")
        print("=" * 60)

        if hasattr(result, "params"):
            print(f"\n因变量: {dep_var}")
            print(f"自变量: {indep_vars}")
            print(f"控制变量: {control_vars}")
            print(f"\n模型: {model_rec['model_name']}")
            print(f"文献依据: {model_rec['文献出处']}")

            print("\n显著性说明:")
            print("  *** p < 0.01  极其显著")
            print("  **  p < 0.05  显著")
            print("  *   p < 0.10  边缘显著")

    except Exception as e:
        print(f"回归运行出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主流程"""
    print("=" * 60)
    print("科研助手 MVP - 面板数据分析工具")
    print("=" * 60)

    # 检查命令行参数
    run_local = "--run-local" in sys.argv or "--local" in sys.argv
    if run_local:
        sys.argv = [a for a in sys.argv if not a.startswith("--")]

    # Step 1: 加载数据
    print("\n[Step 1] 加载数据...")
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "zhejiang_carbon.csv")

    if not os.path.exists(data_path):
        print(f"错误: 数据文件不存在: {data_path}")
        return

    df = pd.read_csv(data_path)
    print(f"数据形状: {df.shape}")
    print(f"列名: {list(df.columns)}")

    # Step 2: 解析研究问题
    print("\n[Step 2] 解析研究问题...")

    default_question = "我想分析农业产值对碳排放的影响，同时控制农药使用量"

    if len(sys.argv) > 1:
        user_question = sys.argv[1]
    else:
        user_question = input(f"\n请输入研究问题 [{default_question}]: ").strip()
        if not user_question:
            user_question = default_question

    print(f"研究问题: {user_question}")

    # 解析问题
    parsed = parse_question_with_llm(user_question, list(df.columns))

    if not parsed:
        print("错误: 无法解析研究问题")
        return

    print(f"因变量 (Y): {parsed['dependent_var']}")
    print(f"自变量 (X): {parsed['independent_vars']}")
    print(f"控制变量: {parsed['control_vars']}")
    print(f"数据结构: {parsed['data_structure']}")
    print(f"置信度: {parsed['confidence']:.2f}")

    # Step 3: 推断数据结构
    print("\n[Step 3] 推断数据结构...")
    data_structure, panel_dims = infer_data_structure(df)
    print(f"数据结构: {data_structure}")
    if panel_dims:
        print(f"面板维度: {panel_dims}")

    # Step 4: 推荐模型
    print("\n[Step 4] 模型推荐...")
    recommendations = recommend_models(
        data_structure=data_structure,
        has_policy_shock=False,
        has_spatial_effect=False,
    )

    for i, rec in enumerate(recommendations, 1):
        print(f"\n推荐 {i}: {rec['model_name']}")
        print(f"  代码: {rec['model_code']}")
        print(f"  适用条件: {rec['适用条件']}")
        print(f"  文献依据: {rec['文献依据'][:100]}...")

    best_model = recommendations[0]

    # Step 5: 文献检索
    print("\n[Step 5] 文献检索...")
    query = f"{' '.join(parsed['independent_vars'])} {parsed['dependent_var']} {best_model['model_name']}"
    print(f"检索词: {query}")

    literature = retrieve_literature(query, top_k=5)
    print(f"找到 {len(literature)} 篇相关文献")

    for chunk in literature[:3]:
        print(f"\n  [{chunk['chunk_id']}] {chunk['source_file']}")
        print(f"  {chunk['text'][:150]}...")

    # Step 6: 选择输出方式
    if run_local:
        # 直接运行回归
        run_regression(df, parsed, best_model)
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)
    else:
        # 生成 Notebook
        print("\n[Step 6] 生成 Notebook...")

        confirm = input("\n是否生成 Notebook? (y/n): ").strip().lower()
        if confirm == "y":
            config = {
                "title": f"基于{best_model['model_name']}的{parsed['dependent_var']}影响因素分析",
                "dependent_var": parsed["dependent_var"],
                "independent_vars": parsed["independent_vars"],
                "control_vars": parsed["control_vars"],
                "model_recommendation": best_model,
                "literature_chunks": literature,
                "data_file": "zhejiang_carbon.csv",
                "panel_dimensions": panel_dims,
            }

            nb = generate_notebook(config)

            output_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "output")
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, "analysis_notebook.ipynb")
            save_notebook(nb, output_path)

            print("\n" + "=" * 60)
            print("完成! Notebook 已生成.")
            print(f"文件位置: {output_path}")
            print("=" * 60)
        else:
            # 询问是否直接运行
            run_now = input("\n是否直接在本地运行回归? (y/n): ").strip().lower()
            if run_now == "y":
                run_regression(df, parsed, best_model)
                print("\n" + "=" * 60)
                print("分析完成!")
                print("=" * 60)
            else:
                print("已退出")


if __name__ == "__main__":
    main()
