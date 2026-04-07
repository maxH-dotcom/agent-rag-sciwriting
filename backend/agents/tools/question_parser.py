from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# 方法偏好类型
# ---------------------------------------------------------------------------
MethodPreference = Literal["时间序列", "面板回归", "机器学习", None]

# ---------------------------------------------------------------------------
# 方法偏好检测关键词
# ---------------------------------------------------------------------------
METHOD_PATTERNS: dict[str, list[str]] = {
    "时间序列": [
        "时间序列", "arima", "预测", "趋势", "序列分析",
        "forecast", "预测未来", "sarima", "holt-winters", "prophet",
    ],
    "面板回归": [
        "面板", "固定效应", "随机效应", "did", "双重差分", "panel",
        "差分", "政策评估", "固定效应模型",
    ],
    "机器学习": [
        "机器学习", "xgb", "lstm", "随机森林", "神经网络", "预测模型",
        "xgboost", "深度学习", "random forest", "人工智能",
    ],
}


# ---------------------------------------------------------------------------
# 变量名别名映射表（来自 scw agent mvp — 增量合并）
# 用户可能用的不同说法 → 数据中的实际列名
# ---------------------------------------------------------------------------
VAR_ALIASES: dict[str, list[str]] = {
    "碳排放总量": ["碳排放总量", "碳排放总量 10*3t", "CO2排放", "碳排放"],
    "碳排放强度": ["碳排放强度", "碳排放强度指标"],
    "农业产值": ["农业产值", "农业产值 亿元", "农业总产出", "农业增加值"],
    "农民人均年收入": ["农民人均年收入", "农民人均收入", "农村居民收入", "农民收入"],
    "化肥使用量": ["化肥使用量", "农用化肥施用量 万t", "化肥施用量", "农用化肥"],
    "农药使用量": ["农药使用量", "农药使用量 吨", "农药"],
    "粮食产量": ["粮食产量", "粮食作物产量 吨", "粮食总产"],
    "灌溉面积": ["灌溉面积", "灌溉面积电 kha", "有效灌溉面积"],
    "地区": ["地区", "城市", "地级市"],
    "年份": ["年份", "年", "年度"],
    "GDP": ["GDP", "国内生产总值", "地区GDP", "区域GDP"],
    "FDI": ["FDI", "外商直接投资", "外资"],
    "人口": ["人口", "常住人口", "总人口"],
    "耕地面积": ["耕地面积", "农作物播种面积", "播种面积"],
    "农业机械": ["农业机械", "农机总动力", "农业机械化"],
    "森林覆盖率": ["森林覆盖率", "森林面积", "绿化覆盖"],
}


@dataclass
class ParsedQuestion:
    dependent_var: str
    independent_vars: list[str]
    control_vars: list[str]
    confidence: float
    method_preference: MethodPreference = None


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def normalize_var_name(var_name: str, available_columns: list[str]) -> Optional[str]:
    """
    将用户输入的变量名标准化为数据中的实际列名。

    匹配策略（按优先级）：
    1. 精确匹配（清理换行/空格后）
    2. 别名映射匹配（VAR_ALIASES）
    3. 子串包含匹配
    """
    if not var_name:
        return None

    var_lower = var_name.lower().strip()

    # 预处理：清理列名中的换行符和空格
    clean_columns: list[tuple[str, str]] = [
        (col, col.replace("\n", "").replace(" ", "").lower()) for col in available_columns
    ]

    # 策略1：精确匹配
    for col, clean_col in clean_columns:
        if var_lower == clean_col:
            return col

    # 策略2：别名映射
    for _standard_name, aliases in VAR_ALIASES.items():
        if var_lower in [a.lower() for a in aliases]:
            for col, clean_col in clean_columns:
                std_clean = _standard_name.lower().replace(" ", "")
                if std_clean in clean_col or clean_col in std_clean:
                    return col
            for col, clean_col in clean_columns:
                if any(alias.lower() in clean_col for alias in aliases):
                    return col

    # 策略3：子串包含
    for col, clean_col in clean_columns:
        if var_lower in clean_col or clean_col in var_lower:
            return col

    return None


def _build_llm_prompt(user_question: str, columns_str: str) -> str:
    """构建 LLM 解析提示词（来自 scw agent mvp）。"""
    return f"""用户的研究问题：{user_question}

数据中的列名：
{columns_str}

任务：解析这个研究问题，提取：
1. 因变量 (Y) - 被影响的变量
2. 自变量 (X) - 影响因子
3. 控制变量 - 需要控制的变量
4. 数据结构 (panel/cross_section/time_series)
5. 方法偏好 - 分析方法类型（时间序列/面板回归/机器学习/无偏好）

注意：
- "对...的影响" 中，"对"后面的变量是因变量，前面的是自变量
- "与...的关系" 两者都可能是研究变量
- "控制..." 后面的是控制变量
- 方法偏好检测关键词：
  * 时间序列：预测未来、时间序列、ARIMA、趋势分析
  * 面板回归：面板数据、固定效应、随机效应、DID
  * 机器学习：机器学习、XGBoost、LSTM、随机森林

返回 JSON 格式：
{{
    "dependent_var": "因变量名称（从数据列名中选择）",
    "independent_vars": ["自变量1", "自变量2"],
    "control_vars": ["控制变量1"]（如果没有填[]）,
    "data_structure": "panel/cross_section/time_series",
    "method_preference": "时间序列/面板回归/机器学习/无偏好",
    "confidence": 0.0-1.0
}}

只返回 JSON，不要其他内容。"""


def _parse_llm_json_response(response_text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON。"""
    text = response_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        for i, c in enumerate(text):
            if c == "{":
                for j in range(len(text) - 1, i - 1, -1):
                    if text[j] == "}":
                        try:
                            return __import__("json").loads(text[i:j + 1])
                        except Exception:
                            pass
        text = text.split("```")[1].split("```")[0]
    try:
        return __import__("json").loads(text.strip())
    except Exception:
        return None


def _call_llm_with_fallback(prompt: str) -> Optional[str]:
    """
    调用可用的 LLM Provider（多 Provider 支持）。

    优先级：ANTHROPIC_API_KEY → GROQ_API_KEY → OPENAI_API_KEY → None
    所有 Provider 共享同一个 prompt 格式（chat completion）。
    """
    import os

    # 按优先级尝试各 Provider
    providers = [
        ("anthropic", os.environ.get("ANTHROPIC_API_KEY"), _call_anthropic),
        ("groq", os.environ.get("GROQ_API_KEY"), _call_groq),
        ("openai", os.environ.get("OPENAI_API_KEY"), _call_openai),
    ]

    for name, api_key, caller in providers:
        if api_key:
            try:
                return caller(prompt, api_key)
            except Exception:
                continue

    return None


def _call_anthropic(prompt: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _call_groq(prompt: str, api_key: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def _call_openai(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def parse_question(user_query: str, columns: list[str]) -> ParsedQuestion:
    """
    解析研究问题，提取因变量、自变量、控制变量。

    增强版（来自 scw agent mvp 增量合并）：
    - 支持多 Provider LLM 解析（Anthropic > Groq > OpenAI）
    - 变量名别名标准化（VAR_ALIASES）
    - LLM 解析失败时自动降级到规则 fallback
    """
    cleaned_columns = [column.replace("\n", "").strip() for column in columns]
    lower_query = user_query.lower()

    # 优先尝试 LLM 解析
    columns_str = "\n".join(f"- {c}" for c in cleaned_columns)
    prompt = _build_llm_prompt(user_query, columns_str)
    llm_response = _call_llm_with_fallback(prompt)

    if llm_response:
        result = _parse_llm_json_response(llm_response)
        if result:
            # 使用别名标准化变量名
            dep_var = normalize_var_name(result.get("dependent_var", ""), cleaned_columns)
            indep_vars = [
                normalize_var_name(v, cleaned_columns)
                for v in result.get("independent_vars", [])
            ]
            control_vars = [
                normalize_var_name(v, cleaned_columns)
                for v in result.get("control_vars", [])
            ]

            indep_vars = [v for v in indep_vars if v]
            control_vars = [v for v in control_vars if v and v != dep_var and v not in indep_vars]

            if dep_var:
                return ParsedQuestion(
                    dependent_var=dep_var,
                    independent_vars=indep_vars,
                    control_vars=control_vars,
                    confidence=result.get("confidence", 0.8),
                    method_preference=result.get("method_preference"),
                )

    # LLM 不可用时降级到规则解析
    return _parse_question_fallback(user_query, cleaned_columns, lower_query)


def _parse_question_fallback(
    user_question: str,
    cleaned_columns: list[str],
    lower_query: str,
) -> ParsedQuestion:
    """
    基于规则的降级解析方法（来自 scw agent mvp）。
    """
    dep_var = ""
    indep_vars: list[str] = []
    control_vars: list[str] = []

    # 模式1: "X对Y的影响"
    if "对" in lower_query and "影响" in lower_query:
        parts = lower_query.split("对")
        if len(parts) >= 2:
            y_part = (
                parts[1]
                .split("的")[0]
                .split("影响")[0]
                .split("，")[0]
                .split(" ")[0]
                .strip()
            )
            x_part = (
                parts[0]
                .replace("我分析", "")
                .replace("我想分析", "")
                .replace("分析", "")
                .strip()
            )
            dep_var = normalize_var_name(y_part, cleaned_columns) or y_part
            indep_vars = [normalize_var_name(x_part, cleaned_columns) or x_part]

    # 模式2: "X与Y的关系"
    elif "与" in lower_query and "关系" in lower_query:
        parts = lower_query.split("与")
        if len(parts) >= 2:
            var1 = (
                parts[0]
                .replace("我分析", "")
                .replace("分析", "")
                .strip()
            )
            var2 = (
                parts[1]
                .split("的")[0]
                .split("关系")[0]
                .strip()
            )
            indep_vars.append(normalize_var_name(var1, cleaned_columns) or var1)
            dep_var = normalize_var_name(var2, cleaned_columns) or var2

    # 控制变量检测
    if "控制" in lower_query:
        control_part = lower_query.split("控制")[-1].strip()
        control_vars = [normalize_var_name(control_part, cleaned_columns) or control_part]

    # 过滤空值和重复
    indep_vars = [v for v in indep_vars if v and v != dep_var]
    control_vars = [v for v in control_vars if v != dep_var and v not in indep_vars]

    # 如果规则解析找不到，回退到关键词匹配（原有逻辑）
    if not dep_var:
        dep_var = next(
            (col for col in cleaned_columns if "碳排放" in col),
            cleaned_columns[0] if cleaned_columns else "结果变量",
        )

    if not indep_vars:
        indep_vars = [
            col for col in cleaned_columns
            if any(token in col for token in ["产值", "收入", "gdp", "fdi"])
        ]
        if not indep_vars and len(cleaned_columns) > 1:
            indep_vars = [cleaned_columns[1]]

    if not control_vars:
        control_vars = [
            col for col in cleaned_columns
            if any(token in col for token in ["农药", "化肥", "灌溉"])
        ]

    return ParsedQuestion(
        dependent_var=dep_var,
        independent_vars=indep_vars[:3],
        control_vars=control_vars[:2],
        confidence=0.6,
        method_preference=_detect_method_preference(lower_query),
    )


def _detect_method_preference(lower_query: str) -> MethodPreference:
    """检测用户指定的方法偏好类型."""
    for method_type, patterns in METHOD_PATTERNS.items():
        if any(pattern in lower_query for pattern in patterns):
            return method_type  # type: ignore
    return None

