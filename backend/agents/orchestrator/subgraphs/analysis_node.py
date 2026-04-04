from __future__ import annotations

from backend.agents.models.state import MainState
from backend.agents.tools.model_recommender import recommend_models


def run(state: MainState) -> MainState:
    mapping = state.get("data_mapping_result", {})
    has_panel = bool(mapping.get("entity_column") and mapping.get("time_column"))
    models = recommend_models(has_panel)
    best = models[0]
    code_script = f"""# 自动生成的分析脚本草案
import pandas as pd

df = pd.read_csv('your_data.csv')

# 因变量
y = '{mapping.get("dependent_var", "结果变量")}'

# 自变量
x_vars = {mapping.get("independent_vars", [])}

# 控制变量
controls = {mapping.get("control_vars", [])}

# 推荐模型
model = '{best["model_code"]}'
"""
    state["analysis_result"] = {
        "recommended_models": models,
        "code_script": code_script,
        "analysis_plan": [
            "完成字段确认",
            "生成可审核代码",
            "执行前再做人审",
        ],
    }
    state["current_node"] = "analysis"
    state["status"] = "interrupted"
    state["next_action"] = "await_human_confirmation"
    state["interrupt_reason"] = "code_plan_ready"
    state["interrupt_data"] = state["analysis_result"]
    return state

