from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedQuestion:
    dependent_var: str
    independent_vars: list[str]
    control_vars: list[str]
    confidence: float


def parse_question(user_query: str, columns: list[str]) -> ParsedQuestion:
    cleaned_columns = [column.replace("\n", "").strip() for column in columns]
    lower_query = user_query.lower()

    dependent = next((col for col in cleaned_columns if "碳排放" in col), cleaned_columns[0] if cleaned_columns else "结果变量")
    independent = [col for col in cleaned_columns if any(token in col for token in ["产值", "收入", "gdp", "fdi"])]
    if not independent and len(cleaned_columns) > 1:
        independent = [cleaned_columns[1]]
    controls = [col for col in cleaned_columns if any(token in col for token in ["农药", "化肥", "灌溉", "控制"])]

    if "控制" in lower_query and not controls:
        controls = [col for col in cleaned_columns if col not in {dependent, *independent}][:1]

    return ParsedQuestion(
        dependent_var=dependent,
        independent_vars=independent,
        control_vars=controls[:2],
        confidence=0.72 if columns else 0.35,
    )

