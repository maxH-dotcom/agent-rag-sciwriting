# Phase 3：评测体系建设设计文档

> **版本**：v0.1
> **日期**：2026-04-04
> **前置文档**：
> - `科研多Agent系统MVP实施计划.md`
> - `Phase1-Text-to-Code-Bridge-设计文档.md`

---

## 一、Phase 3 目标

**目标**：每次变更可验证

四大组成部分：
1. **黄金测试集**：覆盖核心能力的标准化测试用例
2. **离线评测框架**：自动化指标计算
3. **人工评分机制**：5 分制专家评审
4. **评测报告自动化**：可执行的报告生成

---

## 二、评测指标体系

### 2.1 核心指标

根据实施计划文档：

| 指标 | 阈值 | 说明 |
|------|------|------|
| RAG Recall@5 | > 0.9 | 关键证据召回率 |
| RAG Precision@10 | > 0.7 | 检索精度 |
| Text-to-Code 执行成功率 | > 0.85 | 代码能跑通 |
| Text-to-Code 结果准确率 | > 0.8 | 结果经验证正确 |
| 引用溯源 Trace Success Rate | > 0.9 | 论断能绑定来源 |
| 引用漂移 Drift Rate | < 0.05 | 引用准确性 |
| 风险拦截率 | > 0.95 | 高风险操作被拦截 |
| 路由准确率 | > 0.9 | 任务正确分发 |
| 端到端任务完成率 | > 0.7 | 5类任务中完成3类 |
| 端到端人工采纳率 | > 0.6 | 用户愿意使用输出 |

### 2.2 指标分类

```
评测指标
├── 检索类 (Retrieval)
│   ├── Recall@5
│   ├── Precision@10
│   └── MRR
├── Text-to-Code 类 (CodeGen)
│   ├── 执行成功率
│   ├── 结果准确率
│   └── 安全性
├── 引用溯源类 (Citation)
│   ├── Trace Success Rate
│   └── Drift Rate
└── 端到端类 (E2E)
    ├── 任务完成率
    └── 人工采纳率
```

---

## 三、黄金测试集

### 3.1 测试集结构

```
benchmark/
├── retrieval/
│   ├── cases.json          # 检索测试用例
│   └── expected/           # 期望结果
├── text_to_code/
│   ├── cases.json          # 代码生成测试用例
│   └── ground_truth/      # 标准答案
├── citation/
│   ├── cases.json          # 引用溯源测试用例
│   └── evidence_map/      # 标准证据映射
└── e2e/
    ├── cases.json          # 端到端测试用例
    └── evaluation/         # 评测结果
```

### 3.2 检索测试用例

```json
// benchmark/retrieval/cases.json

{
  "test_cases": [
    {
      "case_id": "ret_001",
      "category": "method_retrieval",
      "query": "STIRPAT 模型碳排放驱动机制",
      "expected_top_chunks": [
        "chunk_id_1",
        "chunk_id_2",
        "chunk_id_3"
      ],
      "required_keywords": ["STIRPAT", "碳排放", "驱动机制"],
      "min_relevant_count": 3
    },
    {
      "case_id": "ret_002",
      "category": "formula_retrieval",
      "query": "农业碳排放系数计算公式",
      "expected_top_chunks": [
        "chunk_id_5",
        "chunk_id_8"
      ],
      "required_keywords": ["碳排放系数", "农业"],
      "min_relevant_count": 2
    },
    {
      "case_id": "ret_003",
      "category": "regional_comparison",
      "query": "浙江省碳排放研究",
      "expected_top_chunks": [
        "chunk_id_10"
      ],
      "required_keywords": ["浙江", "碳排放"],
      "min_relevant_count": 1
    }
  ]
}
```

### 3.3 Text-to-Code 测试用例

```json
// benchmark/text_to_code/cases.json

{
  "test_cases": [
    {
      "case_id": "code_001",
      "category": "indicator_construction",
      "task": "计算浙江省农业碳排放总量",
      "evidence_chunks": [
        "chunk_101",
        "chunk_145"
      ],
      "data_file": "zhejiang_agriculture.csv",
      "expected_output": {
        "total_carbon_2020": 523.41,
        "tolerance": 0.5
      },
      "forbidden_operations": ["os.system", "subprocess"]
    },
    {
      "case_id": "code_002",
      "category": "regression",
      "task": "分析 GDP 对碳排放的影响",
      "evidence_chunks": [
        "chunk_201",
        "chunk_202"
      ],
      "data_file": "panel_data.csv",
      "expected_output": {
        "coefficient_positive": true,
        "p_value_less_than_0.05": true
      },
      "forbidden_operations": ["os.system"]
    },
    {
      "case_id": "code_003",
      "category": "prediction",
      "task": "使用 ARIMA 预测未来5年碳排放",
      "evidence_chunks": [
        "chunk_301"
      ],
      "data_file": "time_series_data.csv",
      "expected_output": {
        "has_forecast": true,
        "forecast_years": 5
      },
      "forbidden_operations": ["os.system", "subprocess"]
    }
  ]
}
```

### 3.4 引用溯源测试用例

```json
// benchmark/citation/cases.json

{
  "test_cases": [
    {
      "case_id": "cite_001",
      "category": "method_citation",
      "claim": "农业碳排放应采用分项核算法",
      "expected_source": "chunk_101",
      "ground_truth": {
        "text": "农业碳排放需分项核算...",
        "source_file": "参考文献01.pdf",
        "page_ref": "p.45"
      }
    },
    {
      "case_id": "cite_002",
      "category": "result_citation",
      "claim": "浙江省碳排放呈上升趋势",
      "expected_source": "chunk_201",
      "ground_truth": {
        "text": "浙江省碳排放从2000年的...",
        "source_file": "参考文献02.pdf",
        "page_ref": "p.78"
      }
    }
  ]
}
```

### 3.5 端到端测试用例

```json
// benchmark/e2e/cases.json

{
  "test_cases": [
    {
      "case_id": "e2e_001",
      "task_type": "topic_novelty_check",
      "description": "判断浙江省农业碳排放预测是否与已有论文重复",
      "input": {
        "user_query": "浙江省农业碳排放趋势预测",
        "existing_papers": ["paper_001.pdf"],
        "uploaded_data": "zhejiang_panel.csv"
      },
      "expected_outputs": {
        "has_novelty_score": true,
        "novelty_score_min": 0.3,
        "has_differentiation_points": true,
        "human_approval_required": true
      },
      "evaluation_criteria": {
        "novelty_assessment_quality": "基于论据的创新性判断",
        "citation_relevance": "引用与选题相关"
      }
    },
    {
      "case_id": "e2e_002",
      "task_type": "analysis",
      "description": "基于面板数据分析 GDP 对碳排放的影响",
      "input": {
        "user_query": "GDP 对碳排放的影响",
        "uploaded_data": "panel_data.csv",
        "expected_method": "面板回归"
      },
      "expected_outputs": {
        "has_code_script": true,
        "code_executed": true,
        "has_results": true,
        "has_evidence_binding": true
      },
      "evaluation_criteria": {
        "code_correctness": "代码逻辑正确",
        "result_validity": "结果通过验证",
        "evidence_binding": "证据与代码绑定"
      }
    }
  ]
}
```

---

## 四、离线评测框架

### 4.1 评测引擎

```python
# benchmark/evaluator.py

import json
import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    case_id: str
    category: str
    passed: bool
    score: float
    metrics: Dict[str, Any]
    errors: List[str]

class BenchmarkEvaluator:
    """
    离线评测引擎
    """

    def __init__(self, system_api_url: str = "http://localhost:8000"):
        self.api_url = system_api_url
        self.results: List[EvaluationResult] = []

    async def evaluate_retrieval(self, case: dict) -> EvaluationResult:
        """评测检索能力"""
        # 调用系统执行检索
        result = await self._call_retrieval_api(case["query"])

        # 计算指标
        retrieved_chunks = result.get("chunks", [])
        expected_chunks = case.get("expected_top_chunks", [])

        # Recall@K
        k = 5
        top_k = retrieved_chunks[:k]
        relevant_in_top_k = len(set(top_k) & set(expected_chunks))
        recall = relevant_in_top_k / len(expected_chunks) if expected_chunks else 0

        # Precision@K
        precision = relevant_in_top_k / k if k > 0 else 0

        # 检查关键词
        keywords_found = sum(
            1 for kw in case.get("required_keywords", [])
            if any(kw in chunk.get("text", "") for chunk in top_k)
        )
        keyword_recall = keywords_found / len(case.get("required_keywords", []))

        passed = recall >= 0.9 and keyword_recall >= 0.8

        return EvaluationResult(
            case_id=case["case_id"],
            category="retrieval",
            passed=passed,
            score=recall * 0.6 + precision * 0.4,
            metrics={
                "recall_at_5": recall,
                "precision_at_10": precision,
                "keyword_recall": keyword_recall
            },
            errors=[]
        )

    async def evaluate_code_generation(self, case: dict) -> EvaluationResult:
        """评测代码生成能力"""
        from backend.core.sandbox.security import SecurityChecker

        # 准备输入
        code_result = await self._call_code_generation_api(
            task=case["task"],
            evidence_chunks=case["evidence_chunks"],
            data_file=case["data_file"]
        )

        generated_code = code_result.get("code_script", "")
        execution_result = code_result.get("execution_result", {})

        errors = []

        # 1. 安全检查
        is_safe, violations = SecurityChecker.check(generated_code)
        if not is_safe:
            errors.append(f"安全违规: {violations}")

        # 2. 执行成功率
        execution_success = execution_result.get("success", False)

        # 3. 结果准确率
        accuracy = 1.0
        if case.get("expected_output"):
            expected = case["expected_output"]
            actual = execution_result.get("output_data", {})

            for key, exp_value in expected.items():
                act_value = actual.get(key)
                if act_value is None:
                    accuracy = 0.0
                    break

                if isinstance(exp_value, float):
                    tolerance = expected.get("tolerance", 0.5)
                    if abs(act_value - exp_value) > tolerance:
                        accuracy = 0.0
                        break
                elif exp_value != act_value:
                    accuracy = 0.0
                    break

        passed = is_safe and execution_success and accuracy > 0.8

        return EvaluationResult(
            case_id=case["case_id"],
            category="code_generation",
            passed=passed,
            score=accuracy,
            metrics={
                "is_safe": is_safe,
                "execution_success": execution_success,
                "accuracy": accuracy,
                "violations": violations if not is_safe else []
            },
            errors=errors
        )

    async def evaluate_citation(self, case: dict) -> EvaluationResult:
        """评测引用溯源能力"""
        trace_result = await self._call_citation_api(
            claim=case["claim"],
            evidence_sources=case["expected_source"]
        )

        # Trace Success Rate
        traced_source = trace_result.get("traced_source")
        expected_source = case["expected_source"]

        trace_success = traced_source == expected_source

        # Drift Rate
        drift = 0.0
        if trace_success:
            traced_text = trace_result.get("traced_text", "")
            ground_truth_text = case["ground_truth"]["text"]

            # 计算文本相似度
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, traced_text[:100], ground_truth_text[:100]).ratio()
            drift = 1.0 - similarity

        passed = trace_success and drift < 0.05

        return EvaluationResult(
            case_id=case["case_id"],
            category="citation",
            passed=passed,
            score=1.0 - drift,
            metrics={
                "trace_success": trace_success,
                "drift_rate": drift
            },
            errors=[]
        )

    async def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整评测"""
        # 加载测试用例
        with open("benchmark/retrieval/cases.json") as f:
            retrieval_cases = json.load(f)["test_cases"]

        with open("benchmark/text_to_code/cases.json") as f:
            code_cases = json.load(f)["test_cases"]

        with open("benchmark/citation/cases.json") as f:
            citation_cases = json.load(f)["test_cases"]

        results = []

        # 评测检索
        for case in retrieval_cases:
            result = await self.evaluate_retrieval(case)
            results.append(result)

        # 评测代码生成
        for case in code_cases:
            result = await self.evaluate_code_generation(case)
            results.append(result)

        # 评测引用溯源
        for case in citation_cases:
            result = await self.evaluate_citation(case)
            results.append(result)

        self.results = results

        # 汇总报告
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """生成评测报告"""
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        summary = {}
        for category, results in by_category.items():
            passed = sum(1 for r in results if r.passed)
            avg_score = sum(r.score for r in results) / len(results)

            summary[category] = {
                "total": len(results),
                "passed": passed,
                "pass_rate": passed / len(results) if results else 0,
                "avg_score": avg_score
            }

        overall_passed = sum(1 for r in self.results if r.passed)
        overall_score = sum(r.score for r in self.results) / len(self.results) if self.results else 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": {
                "total": len(self.results),
                "passed": overall_passed,
                "pass_rate": overall_passed / len(self.results) if self.results else 0,
                "avg_score": overall_score
            },
            "by_category": summary,
            "details": [
                {
                    "case_id": r.case_id,
                    "category": r.category,
                    "passed": r.passed,
                    "score": r.score,
                    "metrics": r.metrics,
                    "errors": r.errors
                }
                for r in self.results
            ]
        }
```

### 4.2 评测命令

```bash
# benchmark/run_evaluation.py

import asyncio
from evaluator import BenchmarkEvaluator

async def main():
    evaluator = BenchmarkEvaluator()

    print("Starting benchmark evaluation...")
    report = await evaluator.run_full_benchmark()

    # 保存报告
    with open(f"benchmark/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=2)

    # 打印摘要
    print(f"\nOverall Pass Rate: {report['overall']['pass_rate']:.2%}")
    print(f"Overall Avg Score: {report['overall']['avg_score']:.2f}")

    for category, summary in report["by_category"].items():
        print(f"\n{category}:")
        print(f"  Pass Rate: {summary['pass_rate']:.2%}")
        print(f"  Avg Score: {summary['avg_score']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 五、人工评分机制

### 5.1 评分标准

```python
# benchmark/human_rating/criteria.py

from enum import Enum

class RatingDimension(str, Enum):
    RELEVANCE = "relevance"           # 相关性
    ACCURACY = "accuracy"             # 准确性
    COMPLETENESS = "completeness"     # 完整性
    COHERENCE = "coherence"           # 连贯性
    CITATION_QUALITY = "citation"     # 引用质量

RATING_CRITERIA = {
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

def calculate_overall_score(ratings: dict) -> float:
    """计算加权总分"""
    weights = {
        RatingDimension.RELEVANCE: 0.25,
        RatingDimension.ACCURACY: 0.30,
        RatingDimension.COMPLETENESS: 0.20,
        RatingDimension.COHERENCE: 0.10,
        RatingDimension.CITATION: 0.15
    }

    total = 0.0
    for dim, weight in weights.items():
        score = ratings.get(dim.value, 3)
        total += score * weight

    return total / 5.0  # 归一化到 0-1
```

### 5.2 人工评分 UI

```tsx
// frontend/components/human-rating.tsx

interface HumanRatingProps {
  taskId: string;
  caseId: string;
  content: {
    noveltyResult?: any;
    analysisResult?: any;
    draftSections?: any;
  };
  onSubmit: (rating: RatingSubmission) => void;
}

export function HumanRatingUI({ taskId, caseId, content, onSubmit }: HumanRatingProps) {
  const [ratings, setRatings] = useState<Record<RatingDimension, number>>({
    relevance: 3,
    accuracy: 3,
    completeness: 3,
    coherence: 3,
    citation: 3,
  });
  const [feedback, setFeedback] = useState("");

  const handleSubmit = () => {
    const overallScore = calculateOverallScore(ratings);
    onSubmit({
      taskId,
      caseId,
      ratings,
      overallScore,
      feedback,
      timestamp: new Date().toISOString()
    });
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto">
      <h2 className="text-xl font-bold mb-4">人工评分</h2>

      {content.noveltyResult && (
        <Section title="创新性评估">
          <NoveltyResultView data={content.noveltyResult} />
        </Section>
      )}

      {content.draftSections && (
        <Section title="论文草稿">
          <DraftView data={content.draftSections} />
        </Section>
      )}

      <div className="mt-6 space-y-4">
        {Object.entries(RATING_CRITERIA).map(([dimension, criteria]) => (
          <div key={dimension} className="border-b pb-4">
            <h3 className="font-semibold mb-2">{dimension}</h3>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((score) => (
                <button
                  key={score}
                  onClick={() => setRatings({ ...ratings, [dimension]: score })}
                  className={`px-4 py-2 rounded ${
                    ratings[dimension] === score
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200"
                  }`}
                >
                  {score}
                </button>
              ))}
            </div>
            <p className="text-sm text-gray-600 mt-1">{criteria[ratings[dimension]]}</p>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <label className="block font-semibold mb-2">反馈意见</label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          className="w-full border rounded p-2"
          rows={4}
          placeholder="请提供详细反馈..."
        />
      </div>

      <button
        onClick={handleSubmit}
        className="mt-6 px-6 py-2 bg-green-600 text-white rounded"
      >
        提交评分
      </button>
    </div>
  );
}
```

### 5.3 评分存储

```python
# benchmark/storage/rating_store.py

import sqlite3
import json
from datetime import datetime
from typing import List, Optional

class RatingStore:
    """
    人工评分存储
    """

    def __init__(self, db_path: str = "benchmark/ratings.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                case_id TEXT,
                evaluator_id TEXT,
                ratings_json TEXT NOT NULL,
                overall_score REAL NOT NULL,
                feedback TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def save_rating(self, rating: dict):
        """保存评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ratings
            (rating_id, task_id, case_id, evaluator_id, ratings_json, overall_score, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rating["rating_id"],
            rating["task_id"],
            rating.get("case_id"),
            rating.get("evaluator_id"),
            json.dumps(rating["ratings"]),
            rating["overall_score"],
            rating.get("feedback", ""),
            rating.get("timestamp", datetime.utcnow().isoformat())
        ))

        conn.commit()
        conn.close()

    def get_task_ratings(self, task_id: str) -> List[dict]:
        """获取任务的所有评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ratings WHERE task_id = ?
        """, (task_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "rating_id": row[0],
                "task_id": row[1],
                "case_id": row[2],
                "evaluator_id": row[3],
                "ratings": json.loads(row[4]),
                "overall_score": row[5],
                "feedback": row[6],
                "created_at": row[7]
            }
            for row in rows
        ]

    def get_average_score(self, case_id: str | None = None) -> float:
        """获取平均分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if case_id:
            cursor.execute("""
                SELECT AVG(overall_score) FROM ratings WHERE case_id = ?
            """, (case_id,))
        else:
            cursor.execute("SELECT AVG(overall_score) FROM ratings")

        avg = cursor.fetchone()[0]
        conn.close()

        return avg if avg else 0.0
```

---

## 六、评测报告自动化

### 6.1 报告生成器

```python
# benchmark/reporting/report_generator.py

from datetime import datetime
from typing import Dict, List
import json

class ReportGenerator:
    """
    评测报告生成器
    """

    def generate_markdown_report(self, evaluation_results: dict, human_ratings: list) -> str:
        """生成 Markdown 格式报告"""

        report = f"""# 评测报告

**生成时间**：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
**评测版本**：v1.0

---

## 一、执行摘要

| 指标 | 数值 |
|------|------|
| 总测试用例 | {evaluation_results['overall']['total']} |
| 通过数 | {evaluation_results['overall']['passed']} |
| 通过率 | {evaluation_results['overall']['pass_rate']:.2%} |
| 平均分 | {evaluation_results['overall']['avg_score']:.2f} |

---

## 二、自动评测结果

### 2.1 按类别统计

| 类别 | 通过率 | 平均分 |
|------|--------|--------|
"""

        for category, summary in evaluation_results.get("by_category", {}).items():
            report += f"| {category} | {summary['pass_rate']:.2%} | {summary['avg_score']:.2f} |\n"

        report += """

### 2.2 详细结果

| 用例 ID | 类别 | 状态 | 得分 | 详情 |
|---------|------|------|------|------|
"""

        for detail in evaluation_results.get("details", []):
            status = "✓ 通过" if detail["passed"] else "✗ 失败"
            metrics = ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                               for k, v in detail["metrics"].items())
            report += f"| {detail['case_id']} | {detail['category']} | {status} | {detail['score']:.2f} | {metrics} |\n"

        # 人工评分部分
        if human_ratings:
            avg_human_score = sum(r["overall_score"] for r in human_ratings) / len(human_ratings)

            report += f"""

## 三、人工评分结果

| 指标 | 数值 |
|------|------|
| 评分数量 | {len(human_ratings)} |
| 平均分 | {avg_human_score:.2f} |

"""

        # 问题汇总
        failures = [d for d in evaluation_results.get("details", []) if not d["passed"]]
        if failures:
            report += """

## 四、问题汇总

"""
            for failure in failures:
                report += f"""
### {failure['case_id']}

- **类别**：{failure['category']}
- **错误**：{', '.join(failure.get('errors', [])) or '未知'}
- **详情**：{json.dumps(failure.get('metrics', {}))}

"""

        report += """

---

## 五、建议

"""

        # 根据结果生成建议
        overall_pass_rate = evaluation_results['overall']['pass_rate']
        if overall_pass_rate >= 0.9:
            report += "系统整体表现优秀，建议继续维护并扩大测试集覆盖范围。\n"
        elif overall_pass_rate >= 0.7:
            report += "系统整体表现良好，但仍有改进空间。重点关注失败的测试用例。\n"
        else:
            report += "系统需要较大改进。建议优先解决高优先级的失败用例。\n"

        return report

    def generate_html_report(self, evaluation_results: dict, human_ratings: list) -> str:
        """生成 HTML 格式报告"""
        # 使用模板生成 HTML
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>评测报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>评测报告</h1>
            <p>生成时间：{timestamp}</p>

            <h2>执行摘要</h2>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>总测试用例</td><td>{total}</td></tr>
                <tr><td>通过数</td><td>{passed}</td></tr>
                <tr><td>通过率</td><td>{pass_rate}</td></tr>
            </table>
        </body>
        </html>
        """.format(
            timestamp=datetime.utcnow().isoformat(),
            total=evaluation_results['overall']['total'],
            passed=evaluation_results['overall']['passed'],
            pass_rate=f"{evaluation_results['overall']['pass_rate']:.2%}"
        )

        return template
```

### 6.2 报告 CI/CD 集成

```yaml
# .github/workflows/benchmark.yml

name: Benchmark

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run benchmark
        run: |
          python benchmark/run_evaluation.py

      - name: Generate report
        run: |
          python benchmark/generate_report.py

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-report
          path: benchmark/report_*.md
```

---

## 七、文件清单

| 文件路径 | 说明 |
|----------|------|
| `benchmark/retrieval/cases.json` | 检索测试用例 |
| `benchmark/text_to_code/cases.json` | 代码生成测试用例 |
| `benchmark/citation/cases.json` | 引用溯源测试用例 |
| `benchmark/e2e/cases.json` | 端到端测试用例 |
| `benchmark/evaluator.py` | 评测引擎 |
| `benchmark/human_rating/criteria.py` | 评分标准 |
| `benchmark/storage/rating_store.py` | 评分存储 |
| `benchmark/reporting/report_generator.py` | 报告生成器 |

---

## 八、实施检查清单

### 黄金测试集
- [ ] 检索测试用例（10-20条）
- [ ] 代码生成测试用例（10-20条）
- [ ] 引用溯源测试用例（10-20条）
- [ ] 端到端测试用例（10-15条）

### 评测框架
- [ ] 评测引擎实现
- [ ] 各指标计算逻辑
- [ ] 报告生成器

### 人工评分
- [ ] 评分标准定义
- [ ] 评分 UI 组件
- [ ] 评分存储

### 报告自动化
- [ ] Markdown 报告生成
- [ ] HTML 报告生成
- [ ] CI/CD 集成
