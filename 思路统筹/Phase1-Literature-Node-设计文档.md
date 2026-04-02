# Phase 1：Literature Node 技术设计文档

> **版本**：v0.1
> **日期**：2026-04-02
> **前置文档**：
> - `Phase0-最小可运行骨架-实施计划.md`
> - `Phase1-Text-to-Code-Bridge-设计文档.md`

---

## 一、定位与职责

### 1.1 Literature Node 定位

Literature Node 是系统的**文献检索与证据聚合中心**，负责：
- 为 Novelty Node 提供选题查重所需的文献证据
- 为 Text-to-Code Bridge 提供方法依据和公式来源
- 为后续节点提供结构化的文献元数据

### 1.2 与其他节点的关系

```
                    ┌──────────────────┐
                    │  Literature Node │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────┐    ┌──────────────┐   ┌──────────────┐
    │ Novelty   │    │ Text-to-Code │   │   Writing    │
    │  Node     │    │   Bridge     │   │    Node      │
    └──────────┘    └──────────────┘   └──────────────┘
```

**数据流向**：
- Literature Node 输出 `literature_result` 存入 MainState
- Novelty Node 读取 `literature_result` 进行选题比对
- Text-to-Code Bridge 读取 `literature_result` 获取 evidence_package
- Brief Builder 汇总 `literature_result` 到 Research_Brief

---

## 二、关键设计决策（已确认）

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Literature vs Novelty | 分离设计 | 各自独立，灵活组合 |
| 检索优先级 | 本地优先，外部补充 | 减少外部依赖，提高相关性 |
| Metadata Store | SQLite | 轻量内嵌，无需运维 |
| Node 输出 | 完整 evidence package | method_decision + references + metadata |
| 文献索引 | 上传时自动索引 | 用户体验优先 |

---

## 三、数据结构

### 3.1 Literature Result（输出结构）

```python
# backend/agents/models/literature.py

from typing import TypedDict, Optional, List
from pydantic import BaseModel

class LiteratureChunk(BaseModel):
    """文献片段"""
    chunk_id: str
    source_type: str  # "local" | "openalex"
    source_file: str | None  # 本地文件路径
    openalex_id: str | None  # OpenAlex ID
    title: str
    authors: List[str]
    year: int
    text: str  # 检索到的文本片段
    page_ref: str | None  # 页码引用
    relevance_score: float

class MethodDecision(BaseModel):
    """方法决策"""
    recommended_methods: List[str]  # ["DID", "STIRPAT", "面板回归"]
    rejected_methods: List[str]
    reasoning: str
    evidence_source_ids: List[str]  # 证据来源 chunk_id 列表

class Reference(BaseModel):
    """参考文献条目"""
    reference_id: str
    citation: str  # 完整引用格式
    title: str
    authors: List[str]
    year: int
    source: str  # "local" | "openalex"
    url: str | None
    relevance: str  # "核心参考" | "相关" | "补充"

class LiteratureResult(BaseModel):
    """Literature Node 输出"""
    task_id: str
    query: str

    # 检索结果
    local_chunks: List[LiteratureChunk]  # 本地文献片段
    openalex_chunks: List[LiteratureChunk]  # 外部文献片段
    all_chunks: List[LiteratureChunk]  # 合并后的片段

    # 方法决策
    method_decision: MethodDecision

    # 参考文献
    references: List[Reference]

    # 检索统计
    total_local_hits: int
    total_openalex_hits: int
    retrieval_time_ms: int

    # 质量评估
    quality_score: float  # 0-1
    quality_warning: str | None

    # 元数据
    created_at: str
```

### 3.2 Metadata Store Schema

```sql
-- backend/agents/tools/metadata_store.py (SQLite)

CREATE TABLE papers (
    paper_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,  -- JSON array
    year INTEGER,
    abstract TEXT,
    file_path TEXT,  -- 本地文件路径
    openalex_id TEXT,  -- OpenAlex ID
    indexed_at TEXT,
    -- 元数据字段
    region TEXT,
    method TEXT,
    data_type TEXT,
    dependent_vars TEXT,  -- JSON array
    independent_vars TEXT,  -- JSON array
    keywords TEXT  -- JSON array
);

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    paper_id TEXT,
    chunk_index INTEGER,
    text TEXT,
    page_ref TEXT,
    indexed_at TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
);

CREATE TABLE paper_embeddings (
    paper_id TEXT,
    chunk_id TEXT,
    embedding BLOB,  -- SQLite blob for vector
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);

-- 索引
CREATE INDEX idx_papers_method ON papers(method);
CREATE INDEX idx_papers_region ON papers(region);
CREATE INDEX idx_papers_year ON papers(year);
CREATE INDEX idx_chunks_paper ON chunks(paper_id);
```

---

## 四、Literature Node 子图设计

### 4.1 子图状态

```python
# backend/agents/orchestrator/subgraphs/literature_state.py

from typing import TypedDict, Optional, List

class LiteratureState(TypedDict):
    task_id: str

    # 输入
    query: str
    filters: dict  # {"method": "DID", "region": "浙江", "year_range": (2020, 2025)}
    existing_paper_ids: List[str]  # 已有论文ID（用于Novelty查重）

    # 本地检索结果
    local_chunks: List[dict]
    local_search_error: str | None

    # 外部检索结果
    openalex_chunks: List[dict]
    openalex_search_error: str | None

    # 合并与去重
    merged_chunks: List[dict]

    # 方法决策
    method_decision: dict | None

    # 参考文献
    references: List[dict]

    # 质量评估
    quality_score: float
    quality_warning: str | None

    # 状态
    status: str  # "local_search" | "openalex_search" | "merging" | "method_decision" | "done" | "error"
    error_message: str | None
```

### 4.2 子图节点设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Literature Node 子图                           │
│                                                                  │
│  ┌──────────────┐                                                │
│  │    start    │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────┐                                            │
│  │ local_search     │  ← paper-qa 检索本地文献                    │
│  │ (paper-qa)       │     基于 query + filters                    │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │ openalex_search  │────▶│  merge_chunks    │  ← 合并去重      │
│  │ (pyopenalex)     │     └────────┬─────────┘                  │
│  └──────────────────┘              │                              │
│                                    ▼                              │
│                         ┌──────────────────┐                   │
│                         │ method_decision   │  ← LLM 生成        │
│                         │ (LLM 分析)        │     方法建议       │
│                         └────────┬─────────┘                   │
│                                   │                              │
│                                   ▼                              │
│                         ┌──────────────────┐                   │
│                         │ quality_evaluate  │  ← 质量评分       │
│                         └────────┬─────────┘                   │
│                                   │                              │
│                                   ▼                              │
│                         ┌──────────────────┐                   │
│                         │      end        │                   │
│                         └──────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、核心组件实现

### 5.1 paper-qa 封装

```python
# backend/agents/tools/paperqa_wrapper.py

import paperqa
from paperqa import Docs, Answer
from typing import List, Optional
import asyncio

class PaperQATool:
    """
    paper-qa 封装
    提供文献检索和问答能力
    """

    def __init__(self, docs_path: str = "./data/papers"):
        self.docs_path = docs_path
        self.docs = Docs()  # paper-qa 的文档对象

    async def index_paper(self, file_path: str, paper_id: str) -> dict:
        """
        索引一篇本地文献
        上传时自动调用
        """
        try:
            # paper-qa 自动解析 PDF
            await self.docs.add_file(file_path, paper=paper_id)

            # 提取元数据
            metadata = await self._extract_metadata(paper_id)

            return {
                "success": True,
                "paper_id": paper_id,
                "metadata": metadata
            }
        except Exception as e:
            return {
                "success": False,
                "paper_id": paper_id,
                "error": str(e)
            }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None
    ) -> List[dict]:
        """
        检索本地文献片段
        """
        try:
            # 构建 paper-qa 查询
            answer: Answer = await self.docs.aquery(
                query,
                k=top_k,
                max_sources=10
            )

            # 提取结果
            chunks = []
            for i, source in enumerate(answer.sources):
                chunk = {
                    "chunk_id": f"local_{source.paper}_{source chunk_idx}",
                    "source_type": "local",
                    "source_file": source.path,
                    "title": source.title,
                    "authors": source.authors,
                    "year": source.year,
                    "text": source.text,
                    "page_ref": source.page,
                    "relevance_score": 1.0 - (i * 0.1)  # paper-qa 不提供评分，用排名估算
                }
                chunks.append(chunk)

            # 应用过滤器（如果有）
            if filters:
                chunks = self._apply_filters(chunks, filters)

            return chunks

        except Exception as e:
            return []

    async def similarity_search(
        self,
        text: str,
        top_k: int = 5
    ) -> List[dict]:
        """
        基于文本相似度检索
        用于查找与某篇论文相似的其他论文
        """
        # paper-qa 支持 embedding 相似度搜索
        chunks = await self.search(text, top_k=top_k)
        return chunks

    def _apply_filters(self, chunks: List[dict], filters: dict) -> List[dict]:
        """应用过滤器"""
        filtered = chunks

        if filters.get("year_range"):
            min_year, max_year = filters["year_range"]
            filtered = [
                c for c in filtered
                if min_year <= c.get("year", 0) <= max_year
            ]

        if filters.get("method"):
            method = filters["method"].lower()
            filtered = [
                c for c in filtered
                if method in c.get("text", "").lower()
            ]

        return filtered
```

### 5.2 pyopenalex 封装

```python
# backend/agents/tools/openalex_wrapper.py

from pyopenalex import Works, Authors, Institutions, search
from typing import List, Optional
import asyncio

class OpenAlexTool:
    """
    pyopenalex 封装
    提供外部文献检索能力
    """

    def __init__(self):
        self.base_url = "https://api.openalex.org"

    async def search_works(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 10
    ) -> List[dict]:
        """
        检索 OpenAlex 文献
        """
        try:
            # 构建过滤器
            filter_dict = {
                "is_oa": True,  # 只看开放获取
                "has_abstract": True,
            }

            if filters:
                if filters.get("year_range"):
                    filter_dict["from_publication_date"] = f"{filters['year_range'][0]}-01-01"
                    filter_dict["to_publication_date"] = f"{filters['year_range'][1]}-12-31"

                if filters.get("method"):
                    filter_dict["default_stretching"] = filters["method"]

            # 搜索
            works = Works().search(query, filter=filter_dict, per_page=top_k)

            results = []
            for work in works:
                chunk = {
                    "chunk_id": f"openalex_{work.id}",
                    "source_type": "openalex",
                    "openalex_id": work.id,
                    "title": work.title,
                    "authors": [a.display_name for a in work.authorships] if work.authorships else [],
                    "year": work.publication_year,
                    "abstract": work abstract or "",
                    "text": self._extract_key_content(work),
                    "page_ref": None,
                    "relevance_score": 0.8,  # 默认评分
                    "url": work.doi or f"https://openalex.org/{work.id}"
                }
                results.append(chunk)

            return results

        except Exception as e:
            return []

    async def find_similar(
        self,
        title: str,
        top_k: int = 5
    ) -> List[dict]:
        """
        查找与给定论文相似的文献
        """
        try:
            # 使用 OpenAlex 的相似文献 API
            works = Works().search(title, per_page=top_k + 1)

            results = []
            for work in works:
                if work.title == title:
                    continue  # 跳过原文献

                chunk = {
                    "chunk_id": f"openalex_{work.id}",
                    "source_type": "openalex",
                    "title": work.title,
                    "authors": [a.display_name for a in work.authorships] if work.authorships else [],
                    "year": work.publication_year,
                    "text": work.abstract or "",
                    "relevance_score": 0.7
                }
                results.append(chunk)

                if len(results) >= top_k:
                    break

            return results

        except Exception as e:
            return []

    def _extract_key_content(self, work) -> str:
        """从 work 对象提取关键内容"""
        parts = []

        if work.title:
            parts.append(f"Title: {work.title}")

        if work.abstract:
            # 取前 500 字
            parts.append(f"Abstract: {work.abstract[:500]}...")

        if work.mesh_terms:
            terms = ", ".join([m.preferred_label for m in work.mesh_terms[:5]])
            parts.append(f"Keywords: {terms}")

        return "\n".join(parts)
```

### 5.3 Metadata Store

```python
# backend/agents/tools/metadata_store.py

import sqlite3
import json
import os
from typing import List, Optional
from datetime import datetime

class MetadataStore:
    """
    SQLite 元数据存储
    存储文献的结构化元数据，支持高效过滤
    """

    def __init__(self, db_path: str = "./data/metadata.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """确保数据库和表存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                abstract TEXT,
                file_path TEXT,
                openalex_id TEXT,
                indexed_at TEXT,
                region TEXT,
                method TEXT,
                data_type TEXT,
                dependent_vars TEXT,
                independent_vars TEXT,
                keywords TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_paper(self, paper_id: str, metadata: dict):
        """添加文献元数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO papers
            (paper_id, title, authors, year, abstract, file_path, openalex_id,
             indexed_at, region, method, data_type, dependent_vars, independent_vars, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_id,
            metadata.get("title"),
            json.dumps(metadata.get("authors", [])),
            metadata.get("year"),
            metadata.get("abstract"),
            metadata.get("file_path"),
            metadata.get("openalex_id"),
            datetime.utcnow().isoformat(),
            metadata.get("region"),
            metadata.get("method"),
            metadata.get("data_type"),
            json.dumps(metadata.get("dependent_vars", [])),
            json.dumps(metadata.get("independent_vars", [])),
            json.dumps(metadata.get("keywords", []))
        ))

        conn.commit()
        conn.close()

    def search_papers(
        self,
        method: str | None = None,
        region: str | None = None,
        year_range: tuple | None = None,
        keyword: str | None = None,
        limit: int = 20
    ) -> List[dict]:
        """
        根据条件搜索文献
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM papers WHERE 1=1"
        params = []

        if method:
            query += " AND method LIKE ?"
            params.append(f"%{method}%")

        if region:
            query += " AND region LIKE ?"
            params.append(f"%{region}%")

        if year_range:
            query += " AND year >= ? AND year <= ?"
            params.extend(year_range)

        if keyword:
            query += " AND (keywords LIKE ? OR title LIKE ? OR abstract LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "paper_id": row[0],
                "title": row[1],
                "authors": json.loads(row[2]) if row[2] else [],
                "year": row[3],
                "abstract": row[4],
                "file_path": row[5],
                "openalex_id": row[6],
                "indexed_at": row[7],
                "region": row[8],
                "method": row[9],
                "data_type": row[10],
                "dependent_vars": json.loads(row[11]) if row[11] else [],
                "independent_vars": json.loads(row[12]) if row[12] else [],
                "keywords": json.loads(row[13]) if row[13] else []
            })

        return results
```

### 5.4 Literature Node 主逻辑

```python
# backend/agents/orchestrator/subgraphs/literature_node.py

async def literature_node(state: MainState) -> MainState:
    """
    Literature Node 主逻辑

    流程：
    1. 本地检索（paper-qa）
    2. 外部检索（pyopenalex）
    3. 合并去重
    4. 方法决策（LLM）
    5. 质量评估
    """
    from .literature_state import LiteratureState
    from .paperqa_wrapper import PaperQATool
    from .openalex_wrapper import OpenAlexTool
    from .metadata_store import MetadataStore
    from langchain_openai import ChatOpenAI

    task_id = state["task_id"]
    query = extract_literature_query(state)  # 从 MainState 提取查询
    filters = extract_filters(state)  # 提取过滤条件

    literature_state = LiteratureState(
        task_id=task_id,
        query=query,
        filters=filters,
        local_chunks=[],
        openalex_chunks=[],
        merged_chunks=[],
        method_decision=None,
        references=[],
        quality_score=0.0,
        quality_warning=None,
        status="local_search"
    )

    # Step 1: 本地检索
    paperqa = PaperQATool()
    literature_state["local_chunks"] = await paperqa.search(
        query=query,
        top_k=10,
        filters=filters
    )

    if not literature_state["local_chunks"]:
        literature_state["local_search_error"] = "未找到相关本地文献"

    # Step 2: 外部检索（补充）
    literature_state["status"] = "openalex_search"
    openalex = OpenAlexTool()

    openalex_chunks = await openalex.search_works(
        query=query,
        filters=filters,
        top_k=10
    )
    literature_state["openalex_chunks"] = openalex_chunks

    if not openalex_chunks:
        literature_state["openalex_search_error"] = "未找到相关外部文献"

    # Step 3: 合并去重
    literature_state["status"] = "merging"
    literature_state["merged_chunks"] = merge_and_deduplicate(
        literature_state["local_chunks"],
        literature_state["openalex_chunks"]
    )

    # Step 4: 方法决策（LLM）
    literature_state["status"] = "method_decision"
    llm = ChatOpenAI(model="gpt-4")

    method_prompt = f"""
    基于以下检索到的文献片段，分析适合的研究方法。

    用户查询：{query}
    过滤条件：{filters}

    文献片段：
    {format_chunks_for_llm(literature_state['merged_chunks'][:10])}

    任务：
    1. 推荐适合该研究问题的方法（可选多个）
    2. 说明不推荐的方法（如有）
    3. 给出推荐理由

    返回JSON格式：
    {{
        "recommended_methods": ["方法1", "方法2"],
        "rejected_methods": ["不推荐的方法"],
        "reasoning": "推荐理由",
        "evidence_source_ids": ["chunk_id列表"]
    }}
    """

    method_response = await llm.ainvoke(method_prompt)
    literature_state["method_decision"] = json.loads(method_response.content)

    # Step 5: 质量评估
    literature_state["status"] = "quality_evaluate"
    quality_result = await evaluate_literature_quality(
        chunks=literature_state["merged_chunks"],
        method_decision=literature_state["method_decision"],
        query=query
    )
    literature_state["quality_score"] = quality_result["score"]
    literature_state["quality_warning"] = quality_result["warning"]

    # Step 6: 构建参考文献
    literature_state["references"] = build_references(
        literature_state["merged_chunks"]
    )

    # 更新 MainState
    return {
        **state,
        "literature_result": {
            "task_id": task_id,
            "query": query,
            "local_chunks": literature_state["local_chunks"],
            "openalex_chunks": literature_state["openalex_chunks"],
            "all_chunks": literature_state["merged_chunks"],
            "method_decision": literature_state["method_decision"],
            "references": literature_state["references"],
            "total_local_hits": len(literature_state["local_chunks"]),
            "total_openalex_hits": len(literature_state["openalex_chunks"]),
            "retrieval_time_ms": 0,  # 简化
            "quality_score": literature_state["quality_score"],
            "quality_warning": literature_state["quality_warning"],
            "created_at": datetime.utcnow().isoformat()
        },
        "current_node": "literature",
        "status": "done"
    }


def merge_and_deduplicate(local_chunks: List[dict], openalex_chunks: List[dict]) -> List[dict]:
    """合并本地和外部检索结果，去除重复"""
    merged = []
    seen_ids = set()

    # 优先添加本地文献（相关性通常更高）
    for chunk in local_chunks:
        if chunk["chunk_id"] not in seen_ids:
            chunk["is_local"] = True
            merged.append(chunk)
            seen_ids.add(chunk["chunk_id"])

    # 添加外部文献
    for chunk in openalex_chunks:
        if chunk["chunk_id"] not in seen_ids:
            chunk["is_local"] = False
            merged.append(chunk)
            seen_ids.add(chunk["chunk_id"])

    # 按相关性排序
    merged.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return merged


async def evaluate_literature_quality(
    chunks: List[dict],
    method_decision: dict,
    query: str
) -> dict:
    """评估文献检索质量"""
    # 简化评估逻辑
    score = 0.5

    # 根据结果数量调整
    if len(chunks) >= 5:
        score += 0.2
    elif len(chunks) >= 3:
        score += 0.1

    # 根据方法决策调整
    if method_decision and method_decision.get("recommended_methods"):
        score += 0.2

    # 根据查询相关性调整
    for chunk in chunks[:3]:
        if query.lower() in chunk.get("text", "").lower():
            score += 0.1
            break

    score = min(1.0, score)

    warning = None
    if score < 0.5:
        warning = "检索结果较少，可能需要调整查询词或扩展检索范围"

    return {"score": score, "warning": warning}
```

---

## 六、与其他节点的集成

### 6.1 Novelty Node 调用 Literature

```python
# Novelty Node 中
async def novelty_node(state: MainState) -> MainState:
    """
    Novelty Node 调用 Literature 获取文献证据
    """
    # 检查是否已有 literature_result
    if not state.get("literature_result"):
        # 调用 Literature Node
        literature_state = await literature_node(state)
        state["literature_result"] = literature_state["literature_result"]

    # 基于 literature_result 进行选题查重
    literature_result = state["literature_result"]

    # 对比已有论文和新选题
    novelty_check = await check_novelty(
        existing_papers=state.get("existing_papers", []),
        new_topic=state.get("user_query"),
        literature_chunks=literature_result["all_chunks"],
        method_decision=literature_result["method_decision"]
    )

    # ...
```

### 6.2 Text-to-Code Bridge 调用 Literature

```python
# Text-to-Code Bridge 中
async def retrieve_evidence_node(state: TextToCodeState) -> TextToCodeState:
    """
    Text-to-Code Bridge 从 MainState 读取 literature_result
    """
    # 从 task_id 获取 MainState
    main_state = get_main_state(state["task_id"])

    if main_state.get("literature_result"):
        literature_result = main_state["literature_result"]

        # 构建 evidence_package
        evidence_chunks = [
            {
                "chunk_id": c["chunk_id"],
                "source_file": c.get("source_file") or c.get("title"),
                "page_ref": c.get("page_ref"),
                "text": c["text"],
                "relevance_score": c.get("relevance_score", 0.5)
            }
            for c in literature_result["all_chunks"]
        ]

        state["evidence_package"] = {
            "task_id": state["task_id"],
            "evidence_chunks": evidence_chunks,
            "quality_score": literature_result.get("quality_score", 0.5),
            "quality_warning": literature_result.get("quality_warning"),
            "missing_aspects": []
        }
    else:
        # fallback: 调用 paper-qa 直接检索
        # ...
```

---

## 七、文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/agents/models/literature.py` | LiteratureResult 数据模型 |
| `backend/agents/orchestrator/subgraphs/literature_state.py` | 子图状态定义 |
| `backend/agents/orchestrator/subgraphs/literature_node.py` | Literature Node 主逻辑 |
| `backend/agents/tools/paperqa_wrapper.py` | paper-qa 封装 |
| `backend/agents/tools/openalex_wrapper.py` | pyopenalex 封装 |
| `backend/agents/tools/metadata_store.py` | SQLite 元数据存储 |
| `backend/core/literature_store.py` | 文献存储管理 |

---

## 八、与 Text-to-Code Bridge 的关系

```
Literature Node                      Text-to-Code Bridge
      │                                      │
      │  输出 literature_result               │
      │  包含:                               │
      │    - all_chunks (evidence)            │
      │    - method_decision                 │
      │    - quality_score                   │
      ▼                                      │
      │                                      │
      ◀──────────────────────────────────────┘
      │                                      │
      │  TextToCodeState.evidence_package    │
      │  直接复用 literature_result          │
      │  无需重新检索                        │
```

---

## 九、错误处理

| 错误场景 | 处理策略 |
|----------|----------|
| 本地检索超时 | 跳过本地，继续外部检索 |
| 外部检索失败 | 使用本地结果，给出警告 |
| 两个都失败 | 中断返回错误，要求用户检查文献库 |
| 检索结果太少 | 扩展检索范围，降低相关性阈值 |
| LLM 方法决策失败 | 使用默认方法列表，给出警告 |

---

## 十、实施顺序

建议 Phase 1 中的实施顺序：

1. **Literature Node 基础**（2-3小时）
   - paper-qa 封装
   - pyopenalex 封装
   - Metadata Store SQLite
   - Literature Node 子图

2. **集成 Novelty Node**（1-2小时）
   - Novelty 调用 Literature
   - 数据流打通

3. **集成 Text-to-Code Bridge**（1-2小时）
   - Bridge 复用 literature_result
   - 避免重复检索

---

## 十一、下一步

### 11.1 待讨论

- Research_Brief Schema 完整字段设计
- Analysis Node + Writing Node 实现
- Brief Builder 汇总逻辑

### 11.2 实施顺序建议

1. **Literature Node**（已完成设计）
2. **Research_Brief Schema**（下一步讨论）
3. **Analysis Node**（调用 Bridge + 处理数据）
4. **Brief Builder**（汇总所有节点结果）
5. **Writing Node**（生成草稿）
