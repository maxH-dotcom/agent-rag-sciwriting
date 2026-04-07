"""
评测报告生成器
Benchmark Report Generator - 自动生成 Markdown / HTML 评测报告
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 维度名称映射（中英文）
# ---------------------------------------------------------------------------

_CATEGORY_NAMES = {
    "retrieval": "检索类",
    "text_to_code": "代码生成类",
    "citation": "引用溯源类",
    "e2e": "端到端类",
}


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """
    评测报告生成器。

    支持：
    - Markdown 报告（详细版）
    - HTML 报告（可阅读版）
    - 自动整合人工评分数据（来自 RatingStore）

    用法：
        generator = ReportGenerator(
            benchmark_dir="benchmark",
            rating_store_path="benchmark/ratings.db"
        )
        md_report = generator.generate_markdown_report(evaluation_results)
        html_report = generator.generate_html_report(evaluation_results)
        generator.save_reports(evaluation_results, output_dir="benchmark/reports")
    """

    def __init__(
        self,
        benchmark_dir: str = "benchmark",
        rating_store_path: Optional[str] = None,
    ):
        self.benchmark_dir = Path(benchmark_dir)
        self.rating_store_path = rating_store_path

    # -------------------------------------------------------------------------
    # 公开 API
    # -------------------------------------------------------------------------

    def generate_markdown_report(self, evaluation_results: dict[str, Any]) -> str:
        """
        生成 Markdown 格式的详细评测报告。

        包含：执行摘要 → 按类别统计 → 详细结果 → 人工评分 → 问题汇总 → 建议
        """
        ts = evaluation_results.get("timestamp", datetime.utcnow().isoformat())
        overall = evaluation_results.get("overall", {})
        by_cat = evaluation_results.get("by_category", {})
        details = evaluation_results.get("details", [])

        # 加载人工评分（可选）
        human_ratings = self._load_human_ratings()

        lines: list[str] = []

        # ---- 头部 ----
        lines.append("# 评测报告")
        lines.append("")
        lines.append(f"**生成时间**: {ts}")
        lines.append(f"**评测版本**: v1.0")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ---- 一、执行摘要 ----
        lines.append("## 一、执行摘要")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总测试用例 | {overall.get('total', 0)} |")
        lines.append(f"| 通过数 | {overall.get('passed', 0)} |")
        lines.append(f"| 通过率 | {overall.get('pass_rate', 0) * 100:.1f}% |")
        lines.append(f"| 平均分 | {overall.get('avg_score', 0):.4f} |")
        lines.append("")

        # ---- 二、自动评测结果 ----
        lines.append("---")
        lines.append("")
        lines.append("## 二、自动评测结果")
        lines.append("")

        # 2.1 类别统计表
        lines.append("### 2.1 按类别统计")
        lines.append("")
        lines.append("| 类别 | 总数 | 通过 | 通过率 | 平均分 |")
        lines.append("|------|------|------|--------|--------|")
        for category, summary in by_cat.items():
            cat_name = _CATEGORY_NAMES.get(category, category)
            lines.append(
                f"| {cat_name} | {summary.get('total', 0)} | "
                f"{summary.get('passed', 0)} | "
                f"{summary.get('pass_rate', 0) * 100:.1f}% | "
                f"{summary.get('avg_score', 0):.4f} |"
            )
        lines.append("")

        # 2.2 详细结果表
        lines.append("### 2.2 详细结果")
        lines.append("")
        lines.append("| 用例 ID | 类别 | 状态 | 得分 | 关键指标 |")
        lines.append("|---------|------|------|------|----------|")
        for detail in details:
            status = "✓ 通过" if detail.get("passed") else "✗ 失败"
            metrics = detail.get("metrics", {})
            # 提取最有代表性的指标（不同类别指标不同）
            key_metrics = self._summarize_metrics(category=detail.get("category", ""), metrics=metrics)
            lines.append(
                f"| {detail.get('case_id', '')} | "
                f"{_CATEGORY_NAMES.get(detail.get('category', ''), detail.get('category', ''))} | "
                f"{status} | "
                f"{detail.get('score', 0):.4f} | "
                f"{key_metrics} |"
            )
        lines.append("")

        # ---- 三、人工评分结果 ----
        lines.append("---")
        lines.append("")
        lines.append("## 三、人工评分结果")
        lines.append("")
        if human_ratings:
            avg_human = sum(r["overall_score"] for r in human_ratings) / len(human_ratings)
            lines.append(f"| 指标 | 数值 |")
            lines.append("|------|------|")
            lines.append(f"| 评分数量 | {len(human_ratings)} |")
            lines.append(f"| 平均分 | {avg_human:.4f} |")
            lines.append("")
            lines.append("**各维度平均分**：")
            lines.append("")
            dim_totals: dict[str, list[float]] = {}
            for r in human_ratings:
                for dim, score in r.get("ratings", {}).items():
                    dim_totals.setdefault(dim, []).append(score)
            if dim_totals:
                lines.append("| 维度 | 平均分 |")
                lines.append("|------|--------|")
                for dim, scores in sorted(dim_totals.items()):
                    avg_dim = sum(scores) / len(scores)
                    lines.append(f"| {dim} | {avg_dim:.2f} |")
            lines.append("")
        else:
            lines.append("*暂无人工评分数据*")
            lines.append("")

        # ---- 四、问题汇总 ----
        failures = [d for d in details if not d.get("passed")]
        if failures:
            lines.append("---")
            lines.append("")
            lines.append("## 四、问题汇总")
            lines.append("")
            lines.append(f"共 {len(failures)} 个失败用例：")
            lines.append("")
            for failure in failures:
                lines.append(f"### {failure.get('case_id', 'unknown')}")
                lines.append(f"- **类别**: {_CATEGORY_NAMES.get(failure.get('category', ''), failure.get('category', ''))}")
                errors = failure.get("errors", [])
                lines.append(f"- **错误**: {', '.join(errors) if errors else '无'}")
                metrics = failure.get("metrics", {})
                if metrics:
                    lines.append(f"- **指标**: {json.dumps(metrics, ensure_ascii=False, default=str)}")
                lines.append("")
            lines.append("")

        # ---- 五、建议 ----
        lines.append("---")
        lines.append("")
        lines.append("## 五、建议")
        lines.append("")
        pass_rate = overall.get("pass_rate", 0)
        if pass_rate >= 0.9:
            lines.append("系统整体表现**优秀**（≥90%），建议继续维护并扩大测试集覆盖范围。")
        elif pass_rate >= 0.7:
            lines.append("系统整体表现**良好**（≥70%），但仍有改进空间。重点关注失败的测试用例。")
        elif pass_rate >= 0.5:
            lines.append("系统整体表现**一般**（≥50%），需要关注中高优先级的失败用例，建议优先解决代码生成和引用溯源类问题。")
        else:
            lines.append("系统需要**较大改进**（<50%），建议优先解决高频失败用例，再逐步扩展测试覆盖率。")

        # 人工评分建议
        if human_ratings:
            avg_human = sum(r["overall_score"] for r in human_ratings) / len(human_ratings)
            if avg_human < 0.6:
                lines.append("")
                lines.append("**人工评审反馈**：用户采纳率偏低，建议重点提升输出的完整性和引用准确性。")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*本报告由评测体系自动生成 | 生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def generate_html_report(self, evaluation_results: dict[str, Any]) -> str:
        """
        生成 HTML 格式的可阅读评测报告。
        """
        ts = evaluation_results.get("timestamp", datetime.utcnow().isoformat())
        overall = evaluation_results.get("overall", {})
        by_cat = evaluation_results.get("by_category", {})
        details = evaluation_results.get("details", [])
        human_ratings = self._load_human_ratings()

        # 通过率颜色
        pass_rate = overall.get("pass_rate", 0)
        if pass_rate >= 0.9:
            status_color = "#22c55e"  # green
            status_label = "优秀"
        elif pass_rate >= 0.7:
            status_color = "#f59e0b"  # amber
            status_label = "良好"
        elif pass_rate >= 0.5:
            status_color = "#f97316"  # orange
            status_label = "一般"
        else:
            status_color = "#ef4444"  # red
            status_label = "需改进"

        # 类别行
        cat_rows = ""
        for category, summary in by_cat.items():
            cat_name = _CATEGORY_NAMES.get(category, category)
            cat_pass_rate = summary.get("pass_rate", 0)
            cat_color = "#22c55e" if cat_pass_rate >= 0.8 else "#f59e0b" if cat_pass_rate >= 0.6 else "#ef4444"
            cat_rows += f"""
            <tr>
                <td>{cat_name}</td>
                <td>{summary.get('total', 0)}</td>
                <td>{summary.get('passed', 0)}</td>
                <td style="color:{cat_color};font-weight:bold">{cat_pass_rate*100:.1f}%</td>
                <td>{summary.get('avg_score', 0):.4f}</td>
            </tr>"""

        # 详情行
        detail_rows = ""
        for detail in details:
            status = "✓ 通过" if detail.get("passed") else "✗ 失败"
            row_color = "#dcfce7" if detail.get("passed") else "#fee2e2"
            metrics = detail.get("metrics", {})
            key_metrics = self._summarize_metrics(detail.get("category", ""), metrics)
            detail_rows += f"""
            <tr style="background:{row_color}">
                <td>{detail.get('case_id', '')}</td>
                <td>{_CATEGORY_NAMES.get(detail.get('category', ''), detail.get('category', ''))}</td>
                <td>{status}</td>
                <td>{detail.get('score', 0):.4f}</td>
                <td><small>{key_metrics}</small></td>
            </tr>"""

        # 人工评分
        human_section = ""
        if human_ratings:
            avg_human = sum(r["overall_score"] for r in human_ratings) / len(human_ratings)
            human_section = f"""
            <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-top:16px">
                <h3 style="margin-top:0">人工评分摘要</h3>
                <p>共 {len(human_ratings)} 条人工评分，平均分 <strong>{avg_human:.4f}</strong></p>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>评测报告</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 1100px; margin: 40px auto; padding: 0 20px; color: #1f2937; }}
  h1 {{ border-bottom: 3px solid #3b82f6; padding-bottom: 8px; }}
  h2 {{ color: #1e40af; margin-top: 32px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 12px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th {{ background: #3b82f6; color: white; padding: 10px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }}
  tr:last-child td {{ border-bottom: none; }}
  .summary-card {{ background: #f8fafc; border-radius: 12px; padding: 20px; margin: 16px 0;
                   display: flex; gap: 16px; flex-wrap: wrap; }}
  .metric {{ text-align: center; min-width: 100px; }}
  .metric-value {{ font-size: 28px; font-weight: bold; color: #1f2937; }}
  .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
  .status-badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
                   font-size: 12px; font-weight: bold; }}
  .pass-badge {{ background: #dcfce7; color: #166534; }}
  .fail-badge {{ background: #fee2e2; color: #991b1b; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb;
             color: #9ca3af; font-size: 12px; }}
</style>
</head>
<body>

<h1>评测报告</h1>
<p>生成时间: {ts}</p>

<div class="summary-card">
  <div class="metric">
    <div class="metric-value">{overall.get('total', 0)}</div>
    <div class="metric-label">总用例</div>
  </div>
  <div class="metric">
    <div class="metric-value">{overall.get('passed', 0)}</div>
    <div class="metric-label">通过</div>
  </div>
  <div class="metric">
    <div class="metric-value" style="color:{status_color}">{overall.get('pass_rate', 0)*100:.1f}%</div>
    <div class="metric-label">通过率</div>
  </div>
  <div class="metric">
    <div class="metric-value">{overall.get('avg_score', 0):.4f}</div>
    <div class="metric-label">平均分</div>
  </div>
  <div class="metric">
    <div class="metric-value" style="color:{status_color}">{status_label}</div>
    <div class="metric-label">综合评级</div>
  </div>
</div>

<h2>一、自动评测结果</h2>
<h3>1.1 按类别统计</h3>
<table>
  <thead>
    <tr><th>类别</th><th>总数</th><th>通过</th><th>通过率</th><th>平均分</th></tr>
  </thead>
  <tbody>
    {cat_rows}
  </tbody>
</table>

<h3>1.2 详细结果</h3>
<table>
  <thead>
    <tr><th>用例 ID</th><th>类别</th><th>状态</th><th>得分</th><th>关键指标</th></tr>
  </thead>
  <tbody>
    {detail_rows}
  </tbody>
</table>

<h2>二、建议</h2>
<p>{"系统整体表现优秀，建议继续维护并扩大测试集覆盖范围。" if pass_rate >= 0.9 else "系统整体表现良好，但仍有改进空间。重点关注失败的测试用例。" if pass_rate >= 0.7 else "系统需要较大改进，建议优先解决高优先级的失败用例。" if pass_rate >= 0.5 else "系统需要较大改进，建议优先解决高频失败用例，再逐步扩展测试覆盖率。"}</p>

{human_section}

<div class="footer">
  本报告由评测体系自动生成 | 生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
</div>

</body>
</html>"""
        return html

    def save_reports(
        self,
        evaluation_results: dict[str, Any],
        output_dir: str = "benchmark/reports",
    ) -> tuple[Path, Path]:
        """
        生成并保存 Markdown 和 HTML 报告。

        Returns:
            (markdown_path, html_path)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        md_path = output_path / f"report_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.generate_markdown_report(evaluation_results))

        html_path = output_path / f"report_{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.generate_html_report(evaluation_results))

        return md_path, html_path

    # -------------------------------------------------------------------------
    # 内部工具
    # -------------------------------------------------------------------------

    def _load_human_ratings(self) -> list[dict]:
        """从 RatingStore 加载人工评分（无数据时不报错）"""
        if not self.rating_store_path:
            return []
        try:
            from benchmark.storage.rating_store import RatingStore
            store = RatingStore(self.rating_store_path)
            return store.get_all_ratings()
        except Exception:
            return []

    @staticmethod
    def _summarize_metrics(category: str, metrics: dict[str, Any]) -> str:
        """从 metrics 字典中提取最有代表性的 1-2 个指标摘要。"""
        if not metrics:
            return "-"

        if category == "retrieval":
            recall = metrics.get("recall_at_5", metrics.get("recall"))
            precision = metrics.get("precision_at_10", metrics.get("precision"))
            parts = []
            if recall is not None:
                parts.append(f"R@5={recall:.2f}")
            if precision is not None:
                parts.append(f"P@10={precision:.2f}")
            return " ".join(parts) if parts else str(list(metrics.items())[0])

        if category == "text_to_code":
            safe = metrics.get("is_safe")
            exec_ok = metrics.get("execution_success")
            acc = metrics.get("accuracy")
            parts = []
            if safe is not None:
                parts.append(f"安全={'✓' if safe else '✗'}")
            if exec_ok is not None:
                parts.append(f"执行={'✓' if exec_ok else '✗'}")
            if acc is not None:
                parts.append(f"准={acc:.2f}")
            return " ".join(parts) if parts else str(list(metrics.items())[0])

        if category == "citation":
            ts = metrics.get("trace_success")
            drift = metrics.get("drift_rate")
            parts = []
            if ts is not None:
                parts.append(f"溯源={'✓' if ts else '✗'}")
            if drift is not None:
                parts.append(f"漂移={drift:.2f}")
            return " ".join(parts) if parts else str(list(metrics.items())[0])

        if category == "e2e":
            cov = metrics.get("node_coverage")
            status = metrics.get("status_correct")
            parts = []
            if cov is not None:
                parts.append(f"覆盖={cov:.2f}")
            if status is not None:
                parts.append(f"状态={'✓' if status else '✗'}")
            return " ".join(parts) if parts else str(list(metrics.items())[0])

        # Fallback
        first_key = next(iter(metrics), "")
        first_val = metrics.get(first_key)
        if first_val is not None:
            val_str = f"{first_val:.4f}" if isinstance(first_val, float) else str(first_val)
            return f"{first_key}={val_str}"
        return "-"
