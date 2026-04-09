from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app


BAD_CASE_DIR = ROOT / "bad case"
CSV_PATH = ROOT / "scw agent mvp" / "data" / "zhejiang_carbon.csv"
XLSX_PATH = ROOT / "scw agent mvp" / "data" / "浙江省各城市粮食，碳排放及农业经济发展情况.xlsx"


@dataclass
class AcceptanceCase:
    case_id: str
    mode: str
    data_path: Path
    question: str
    min_final_status: str = "done"


CASES = [
    AcceptanceCase(
        case_id="Q1",
        mode="direct",
        data_path=CSV_PATH,
        question="请基于浙江碳排放数据，识别可能的因变量、自变量和控制变量，并给出推荐映射。",
    ),
    AcceptanceCase(
        case_id="Q2",
        mode="direct",
        data_path=CSV_PATH,
        question="请对农业产值与碳排放之间的关系做描述性统计，并总结主要特征。",
    ),
    AcceptanceCase(
        case_id="Q3",
        mode="direct",
        data_path=CSV_PATH,
        question="请以碳排放为因变量、农业产值为核心自变量、农药使用量为控制变量，生成并执行一个基础回归分析。",
    ),
    AcceptanceCase(
        case_id="Q4",
        mode="direct",
        data_path=CSV_PATH,
        question="如果这是面板数据，请尝试固定效应模型，并解释核心系数方向与显著性。",
    ),
    AcceptanceCase(
        case_id="Q5",
        mode="direct",
        data_path=XLSX_PATH,
        question="请比较粮食产量、农业经济发展水平与碳排放之间的关系，给出哪一个变量更值得重点讨论。",
    ),
    AcceptanceCase(
        case_id="Q6",
        mode="direct",
        data_path=CSV_PATH,
        question="请输出一段可以直接放入论文“结果分析”部分的中文草稿，概括关键发现。",
    ),
    AcceptanceCase(
        case_id="Q7",
        mode="upload",
        data_path=XLSX_PATH,
        question="请基于上传的 Excel 数据，自动识别字段含义，并说明哪些字段适合作为被解释变量、解释变量和控制变量。",
    ),
    AcceptanceCase(
        case_id="Q8",
        mode="upload",
        data_path=XLSX_PATH,
        question="请检查这份数据是否更适合做 OLS、DID 还是面板固定效应，并解释原因。",
    ),
]


def build_client() -> TestClient:
    return TestClient(app)


def create_task(client: TestClient, case: AcceptanceCase) -> dict[str, Any]:
    if case.mode == "upload":
        upload_response = client.post(
            "/upload",
            files=[
                (
                    "files",
                    (
                        case.data_path.name,
                        case.data_path.read_bytes(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                )
            ],
        )
        upload_response.raise_for_status()
        data_files = [upload_response.json()["files"][0]["path"]]
    else:
        data_files = [str(case.data_path.resolve())]

    response = client.post(
        "/tasks",
        json={
            "task_type": "analysis",
            "user_query": case.question,
            "data_files": data_files,
            "paper_files": [],
        },
    )
    response.raise_for_status()
    return response.json()


def continue_until_terminal(client: TestClient, task: dict[str, Any]) -> dict[str, Any]:
    current = task
    while current["status"] == "interrupted":
        response = client.post(
            f"/tasks/{current['task_id']}/continue",
            json={"decision": "approved", "payload": {}},
        )
        response.raise_for_status()
        current = response.json()
    return current


def case_passed(task: dict[str, Any]) -> bool:
    if task["status"] != "done":
        return False
    result = task.get("result") or {}
    if result.get("final_output"):
        return True
    if result.get("writing_result"):
        return True
    return False


def write_bad_case(case: AcceptanceCase, task: dict[str, Any] | None, error: str) -> Path:
    BAD_CASE_DIR.mkdir(parents=True, exist_ok=True)
    task_id = task["task_id"] if task else "unknown"
    failure_node = task["current_node"] if task else "unknown"
    filename = f"{date.today().isoformat()}-{case.data_path.stem}-{case.case_id}-{failure_node}.md"
    path = BAD_CASE_DIR / filename
    content = f"""# 真实数据验收失败：{case.case_id}

- 日期：{date.today().isoformat()}
- 数据文件：{case.data_path}
- 问题编号：{case.case_id}
- 用户问题：{case.question}
- 失败节点：{failure_node}
- 相关任务 ID：{task_id}

## 复现步骤
1. 使用 `{case.mode}` 模式创建任务。
2. 数据文件：`{case.data_path}`。
3. 问题：`{case.question}`。
4. 对所有中断节点执行 approved 继续。

## 预期结果

任务应稳定完成，并返回可读结果。

## 实际结果

{error}

## 报错信息

```text
{error}
```

## 根因分析

待补充。

## 解决方案

待补充。

## 修复后回归结果

待补充。

## 备注

- 模式：{case.mode}
"""
    path.write_text(content, encoding="utf-8")
    return path


def run_case(client: TestClient, case: AcceptanceCase) -> dict[str, Any]:
    task = create_task(client, case)
    final_task = continue_until_terminal(client, task)
    success = case_passed(final_task)
    bad_case_path = None
    if not success:
        bad_case_path = write_bad_case(
            case,
            final_task,
            json.dumps(
                {
                    "status": final_task.get("status"),
                    "current_node": final_task.get("current_node"),
                    "interrupt_reason": final_task.get("interrupt_reason"),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return {
        "case_id": case.case_id,
        "mode": case.mode,
        "data_file": str(case.data_path),
        "task_id": final_task["task_id"],
        "status": final_task["status"],
        "current_node": final_task["current_node"],
        "passed": success,
        "bad_case_path": str(bad_case_path) if bad_case_path else None,
    }


def main() -> None:
    client = build_client()
    results = [run_case(client, case) for case in CASES]
    passed = sum(1 for item in results if item["passed"])
    payload = {
        "date": date.today().isoformat(),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
