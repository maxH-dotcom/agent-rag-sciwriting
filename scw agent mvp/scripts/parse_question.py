"""
研究问题解析 - LLM 解析用户输入的研究问题
支持多种 LLM 提供者: Anthropic, OpenAI, Ollama (本地), Groq 等
"""

import json
import os
from typing import TypedDict, List, Optional

# LLM 配置
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")  # anthropic / openai / ollama / groq
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


class ParsedQuestion(TypedDict):
    dependent_var: str
    independent_vars: List[str]
    control_vars: List[str]
    data_structure: str
    panel_dimensions: dict
    confidence: float


# 变量名映射（用户可能用的不同说法）
VAR_ALIASES = {
    "碳排放总量": ["碳排放总量", "碳排放总量 10*3t", "CO2排放", "碳排放"],
    "碳排放强度": ["碳排放强度", "碳排放强度指标"],
    "农业产值": ["农业产值", "农业产值 亿元", "农业总产出", "农业增加值"],
    "农民人均年收入": ["农民人均年收入", "农民人均收入", "农村居民收入", "农民收入"],
    "化肥使用量": ["化肥使用量", "农用化肥施用量 万t", "化肥施用量", "农用化肥"],
    "农药使用量": ["农药使用量", "农药使用量 吨", "农药"],
    "粮食产量": ["粮食产量", "粮食作物产量 吨", "粮食总产"],
    "灌溉面积": ["灌溉面积", "灌溉面积电 kha", "有效灌溉面积"],
    "地区": ["地区", "城市", "地级市"],
    "年份": ["年份", "年", "年度", "年份"],
}


def normalize_var_name(var_name: str, available_columns: List[str]) -> Optional[str]:
    """将用户输入的变量名标准化为数据中的实际列名"""
    if not var_name:
        return None
    var_lower = var_name.lower().strip()

    # 预处理：去掉列名中的换行符
    clean_columns = []
    for col in available_columns:
        clean_col = col.replace("\n", "").replace(" ", "").lower()
        clean_columns.append((col, clean_col))

    # 首先精确匹配（去掉换行和空格后）
    for col, clean_col in clean_columns:
        if var_lower == clean_col:
            return col

    # 模糊匹配
    for standard_name, aliases in VAR_ALIASES.items():
        if var_lower in [a.lower() for a in aliases]:
            for col, clean_col in clean_columns:
                # 检查标准化名是否在清理后的列名中
                std_clean = standard_name.lower().replace(" ", "")
                if std_clean in clean_col or clean_col in std_clean:
                    return col
            # 返回第一个接近的
            for col, clean_col in clean_columns:
                if any(alias.lower() in clean_col for alias in aliases):
                    return col

    return None


def build_prompt(user_question: str, columns_str: str) -> str:
    """构建解析提示词"""
    return f"""用户的研究问题：{user_question}

数据中的列名：
{columns_str}

任务：解析这个研究问题，提取：
1. 因变量 (Y) - 被影响的变量
2. 自变量 (X) - 影响因子
3. 控制变量 - 需要控制的变量
4. 数据结构推断 (panel/cross_section/time_series)

注意：
- "对...的影响" 中，"对"后面的变量是因变量，前面的是自变量
- "与...的关系" 两者都可能是研究变量
- "控制..." 后面的是控制变量

返回 JSON 格式：
{{
    "dependent_var": "因变量名称（从数据列名中选择）",
    "independent_vars": ["自变量1", "自变量2"],
    "control_vars": ["控制变量1"]（如果没有填[]）,
    "data_structure": "panel/cross_section/time_series",
    "confidence": 0.0-1.0（解析置信度）
}}

只返回 JSON，不要其他内容。"""


def call_anthropic(prompt: str, model: str = "claude-opus-4-6") -> str:
    """调用 Anthropic Claude"""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """调用 OpenAI GPT"""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def call_ollama(prompt: str, model: str = "llama3") -> str:
    """调用 Ollama 本地模型"""
    import ollama
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()


def call_groq(prompt: str, model: str = "llama-3.1-8b-instant") -> str:
    """调用 Groq (免费高速)"""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def call_llm(prompt: str, provider: str = None, model: str = None) -> Optional[str]:
    """
    通用 LLM 调用接口

    Args:
        prompt: 提示词
        provider: 提供者 (anthropic/openai/ollama/groq)，默认从环境变量 LLM_PROVIDER 读取
        model: 模型名称，默认使用各提供者的高效模型

    Returns:
        LLM 响应文本，失败返回 None
    """
    if provider is None:
        provider = LLM_PROVIDER

    try:
        if provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                return None
            return call_anthropic(prompt, model or "claude-opus-4-6")

        elif provider == "openai":
            if not OPENAI_API_KEY:
                return None
            return call_openai(prompt, model or "gpt-4o-mini")

        elif provider == "ollama":
            return call_ollama(prompt, model or "llama3")

        elif provider == "groq":
            if not GROQ_API_KEY:
                return None
            return call_groq(prompt, model or "llama-3.1-8b-instant")

        else:
            print(f"Unknown LLM provider: {provider}")
            return None

    except Exception as e:
        print(f"LLM call failed ({provider}): {e}")
        return None


def parse_json_response(response_text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON"""
    text = response_text.strip()

    # 提取 ```json ... ``` 块
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        # 尝试找到 JSON 对象
        for i, c in enumerate(text):
            if c == "{":
                # 找到第一个 {
                for j in range(len(text) - 1, i - 1, -1):
                    if text[j] == "}":
                        try:
                            return json.loads(text[i:j + 1])
                        except json.JSONDecodeError:
                            pass
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def parse_question_with_llm(
    user_question: str,
    available_columns: List[str],
    provider: str = None,
    model: str = None,
) -> Optional[ParsedQuestion]:
    """
    使用 LLM 解析研究问题

    Args:
        user_question: 用户输入的研究问题
        available_columns: 数据中的可用列名
        provider: LLM 提供者 (anthropic/openai/ollama/groq)
        model: 模型名称

    Returns:
        解析结果，包含因变量、自变量、控制变量等
    """
    # 尝试 LLM 调用
    columns_str = "\n".join(f"- {c}" for c in available_columns)
    prompt = build_prompt(user_question, columns_str)

    response_text = call_llm(prompt, provider, model)

    if not response_text:
        print("WARNING: LLM call failed, using fallback parsing")
        return parse_question_fallback(user_question, available_columns)

    # 解析 JSON
    result = parse_json_response(response_text)
    if not result:
        print("WARNING: Failed to parse LLM response, using fallback")
        return parse_question_fallback(user_question, available_columns)

    # 标准化变量名
    dep_var = normalize_var_name(result.get("dependent_var", ""), available_columns)
    indep_vars = [
        normalize_var_name(v, available_columns)
        for v in result.get("independent_vars", [])
    ]
    control_vars = [
        normalize_var_name(v, available_columns)
        for v in result.get("control_vars", [])
    ]

    # 过滤空值
    indep_vars = [v for v in indep_vars if v]
    control_vars = [v for v in control_vars if v]
    # 去除重复
    indep_vars = [v for v in indep_vars if v != dep_var]
    control_vars = [v for v in control_vars if v != dep_var and v not in indep_vars]

    return ParsedQuestion(
        dependent_var=dep_var or "",
        independent_vars=indep_vars,
        control_vars=control_vars,
        data_structure=result.get("data_structure", "panel"),
        panel_dimensions={"entity": "地区", "time": "年份"},
        confidence=result.get("confidence", 0.8),
    )


def parse_question_fallback(
    user_question: str,
    available_columns: List[str],
) -> ParsedQuestion:
    """
    基于规则的降级解析方法
    """
    question = user_question.lower()

    dep_var = ""
    indep_vars = []
    control_vars = []

    # 模式1: "X对Y的影响"
    if "对" in question and "影响" in question:
        parts = question.split("对")
        if len(parts) >= 2:
            y_part = parts[1].split("的")[0].split("影响")[0].split("，")[0].split(" ")[0].strip()
            x_part = parts[0].replace("我分析", "").replace("我想分析", "").replace("分析", "").strip()

            dep_var = normalize_var_name(y_part, available_columns) or y_part
            indep_vars = [normalize_var_name(x_part, available_columns) or x_part]

    # 模式2: "与...的关系"
    elif "与" in question and "关系" in question:
        parts = question.split("与")
        if len(parts) >= 2:
            var1 = parts[0].replace("我分析", "").replace("分析", "").strip()
            var2 = parts[1].split("的")[0].split("关系")[0].strip()
            indep_vars.append(normalize_var_name(var1, available_columns) or var1)
            dep_var = normalize_var_name(var2, available_columns) or var2

    # 控制变量检测
    if "控制" in question:
        control_part = question.split("控制")[-1].strip()
        control_vars = [normalize_var_name(control_part, available_columns) or control_part]

    # 过滤
    indep_vars = [v for v in indep_vars if v and v != dep_var]
    control_vars = [v for v in control_vars if v != dep_var and v not in indep_vars]

    return ParsedQuestion(
        dependent_var=dep_var,
        independent_vars=indep_vars,
        control_vars=control_vars,
        data_structure="panel",
        panel_dimensions={"entity": "地区", "time": "年份"},
        confidence=0.6,
    )
