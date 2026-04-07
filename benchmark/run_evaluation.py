#!/usr/bin/env python3
"""
评测运行脚本
Usage: python benchmark/run_evaluation.py
"""
from __future__ import annotations

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.evaluator import BenchmarkEvaluator
from benchmark.reporting.report_generator import ReportGenerator


async def run_evaluation(
    benchmark_dir: str = "benchmark",
    output_dir: str = "benchmark/reports",
    rating_store_path: str | None = "benchmark/ratings.db",
):
    """运行评测并生成报告（JSON / Markdown / HTML）"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    evaluator = BenchmarkEvaluator(benchmark_dir=benchmark_dir)
    generator = ReportGenerator(
        benchmark_dir=benchmark_dir,
        rating_store_path=rating_store_path,
    )

    print("=" * 60)
    print("科研多Agent系统 - 评测体系")
    print("=" * 60)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    report = await evaluator.run_full_benchmark()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存 JSON 报告
    json_path = output_path / f"evaluation_report_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 生成 Markdown 报告
    md_path = output_path / f"evaluation_report_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generator.generate_markdown_report(report))

    # 生成 HTML 报告
    html_path = output_path / f"evaluation_report_{timestamp}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generator.generate_html_report(report))

    # 打印摘要
    print_summary(report)

    print(f"\n详细报告已保存至:")
    print(f"  JSON:    {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  HTML:    {html_path}")

    return report


def print_summary(report: dict):
    """打印评测摘要"""
    overall = report["overall"]
    by_cat = report["by_category"]

    print(f"\n{'类别':<20} {'总数':<8} {'通过':<8} {'通过率':<12} {'平均分':<10}")
    print("-" * 60)

    cat_names = {
        "retrieval": "检索类",
        "text_to_code": "代码生成类",
        "citation": "引用溯源类",
        "e2e": "端到端类",
    }

    for category, summary in by_cat.items():
        cat_name = cat_names.get(category, category)
        print(
            f"{cat_name:<20} {summary['total']:<8} {summary['passed']:<8} "
            f"{summary['pass_rate']*100:>6.1f}%     {summary['avg_score']:.4f}"
        )

    print("-" * 60)
    print(
        f"{'总体':<20} {overall['total']:<8} {overall['passed']:<8} "
        f"{overall['pass_rate']*100:>6.1f}%     {overall['avg_score']:.4f}"
    )

    failures = [d for d in report["details"] if not d["passed"]]
    if failures:
        print(f"\n失败用例 ({len(failures)}):")
        for f in failures:
            print(f"  - {f['case_id']} ({f['category']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行评测")
    parser.add_argument("--benchmark-dir", default="benchmark", help="评测数据目录")
    parser.add_argument("--output-dir", default="benchmark/reports", help="报告输出目录")
    parser.add_argument(
        "--no-human-ratings",
        action="store_true",
        help="跳过人工评分数据",
    )
    args = parser.parse_args()

    asyncio.run(
        run_evaluation(
            args.benchmark_dir,
            args.output_dir,
            rating_store_path=None if args.no_human_ratings else "benchmark/ratings.db",
        )
    )
