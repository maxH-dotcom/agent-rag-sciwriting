from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import urlopen


@dataclass
class LiteratureChunk:
    chunk_id: str
    title: str
    source: str
    source_type: str
    text: str
    method_name: str
    source_region: str
    source_domain: str
    data_structure: str
    relevance_score: float
    source_file: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "source": self.source,
            "source_type": self.source_type,
            "text": self.text,
            "method_name": self.method_name,
            "source_region": self.source_region,
            "source_domain": self.source_domain,
            "data_structure": self.data_structure,
            "relevance_score": self.relevance_score,
            "source_file": self.source_file,
            "url": self.url,
        }


def _fallback_chunks(user_query: str) -> list[LiteratureChunk]:
    knowledge_base = [
        LiteratureChunk(
            chunk_id="lit_001",
            title="Panel Methods for Environmental Productivity",
            source="Wooldridge-style panel econometrics",
            source_type="fallback",
            text="固定效应模型适合控制地区不随时间变化的不可观测异质性。",
            method_name="固定效应模型",
            source_region="通用",
            source_domain="环境经济学",
            data_structure="面板数据",
            relevance_score=0.92,
        ),
        LiteratureChunk(
            chunk_id="lit_002",
            title="STIRPAT for Carbon Emissions",
            source="农业碳排放研究综述",
            source_type="fallback",
            text="STIRPAT 常用于碳排放驱动因素分析，适合解释变量映射与跨地区迁移。",
            method_name="STIRPAT模型",
            source_region="中国地区研究",
            source_domain="农业碳排放",
            data_structure="面板数据",
            relevance_score=0.9,
        ),
        LiteratureChunk(
            chunk_id="lit_003",
            title="Difference in Differences for Policy Evaluation",
            source="准实验方法综述",
            source_type="fallback",
            text="双重差分适合评估政策冲击前后的因果效应，但需要较强识别假设。",
            method_name="双重差分",
            source_region="通用",
            source_domain="政策评估",
            data_structure="面板数据",
            relevance_score=0.84,
        ),
    ]

    if "碳排放" in user_query:
        return knowledge_base[:2]
    if "政策" in user_query:
        return [knowledge_base[2], knowledge_base[0]]
    return knowledge_base[:1]


def _local_file_chunks(paper_files: list[str]) -> list[LiteratureChunk]:
    chunks: list[LiteratureChunk] = []
    for index, paper_file in enumerate(paper_files, start=1):
        path = Path(paper_file)
        title = path.stem if path.stem else f"Local Paper {index}"
        chunks.append(
            LiteratureChunk(
                chunk_id=f"local_{index:03d}",
                title=title,
                source=paper_file,
                source_type="local_file",
                text=f"本地论文文件已登记: {title}。当前版本仅记录文件元数据，后续接入真实 paper-qa 解析。",
                method_name="待解析",
                source_region="待解析",
                source_domain="待解析",
                data_structure="待解析",
                relevance_score=0.6,
                source_file=paper_file,
            )
        )
    return chunks


def _paperqa_chunks(user_query: str, paper_files: list[str]) -> tuple[list[LiteratureChunk], str | None]:
    try:
        from paperqa import Docs
    except ModuleNotFoundError:
        return [], "paper-qa 未安装，跳过本地文献语义检索。"

    if not paper_files:
        return [], "没有提供本地论文文件，跳过 paper-qa 检索。"

    try:
        import asyncio

        async def _search() -> list[LiteratureChunk]:
            docs = Docs()
            for paper_file in paper_files:
                path = Path(paper_file)
                if path.exists():
                    await docs.add(path.name, dir=str(path.parent))
            result = await docs.aquery(user_query)
            answer = getattr(result, "answer", "") or ""
            references = getattr(result, "references", []) or []

            chunks: list[LiteratureChunk] = []
            for index, reference in enumerate(references[:5], start=1):
                if isinstance(reference, dict):
                    source_file = reference.get("path") or reference.get("filepath")
                else:
                    source_file = str(reference)
                chunks.append(
                    LiteratureChunk(
                        chunk_id=f"paperqa_{index:03d}",
                        title=Path(source_file).stem if source_file else f"paperqa_{index}",
                        source=source_file or "paper-qa",
                        source_type="paperqa",
                        text=answer[:500] if answer else "paper-qa 返回了引用，但没有答案摘要。",
                        method_name="待解析",
                        source_region="待解析",
                        source_domain="待解析",
                        data_structure="待解析",
                        relevance_score=max(0.5, 0.95 - index * 0.08),
                        source_file=source_file,
                    )
                )
            return chunks

        return asyncio.run(_search()), None
    except Exception as exc:  # pragma: no cover - depends on external package/runtime
        return [], f"paper-qa 检索失败: {exc}"


def _openalex_chunks(user_query: str) -> tuple[list[LiteratureChunk], str | None]:
    if os.environ.get("RESEARCH_ASSISTANT_DISABLE_REMOTE_SEARCH", "0") == "1":
        return [], "远程检索已通过环境变量关闭。"

    url = f"https://api.openalex.org/works?search={quote_plus(user_query)}&per-page=3"
    try:
        with urlopen(url, timeout=5) as response:  # pragma: no cover - network dependent
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network dependent
        return [], f"OpenAlex 检索失败: {exc}"

    results = payload.get("results", [])
    chunks: list[LiteratureChunk] = []
    for index, item in enumerate(results, start=1):
        chunks.append(
            LiteratureChunk(
                chunk_id=f"openalex_{index:03d}",
                title=item.get("title") or f"openalex_{index}",
                source=item.get("id") or "OpenAlex",
                source_type="openalex",
                text=(item.get("display_name") or item.get("title") or "")[:500],
                method_name="待解析",
                source_region="待解析",
                source_domain="待解析",
                data_structure="待解析",
                relevance_score=max(0.45, 0.88 - index * 0.08),
                url=item.get("id"),
            )
        )
    return chunks, None


def _build_references(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for chunk in chunks:
        references.append(
            {
                "reference_id": chunk["chunk_id"],
                "title": chunk["title"],
                "citation": f"{chunk['title']} ({chunk['source']})",
                "source_type": chunk["source_type"],
                "url": chunk.get("url"),
            }
        )
    return references


def _build_method_metadata(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "method_name": chunk["method_name"],
            "source_chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "source_region": chunk["source_region"],
            "source_domain": chunk["source_domain"],
            "data_structure": chunk["data_structure"],
            "relevance_score": chunk["relevance_score"],
        }
        for chunk in chunks
    ]


def retrieve_literature(user_query: str, paper_files: list[str] | None = None) -> dict[str, Any]:
    paper_files = paper_files or []
    warnings: list[str] = []

    fallback_chunks = _fallback_chunks(user_query)
    local_chunks = _local_file_chunks(paper_files)
    paperqa_chunks, paperqa_warning = _paperqa_chunks(user_query, paper_files)
    openalex_chunks, openalex_warning = _openalex_chunks(user_query)

    if paperqa_warning:
        warnings.append(paperqa_warning)
    if openalex_warning:
        warnings.append(openalex_warning)

    merged_chunks = local_chunks + paperqa_chunks + openalex_chunks + fallback_chunks
    merged_chunks.sort(key=lambda chunk: chunk.relevance_score, reverse=True)

    chunk_dicts = [chunk.to_dict() for chunk in merged_chunks]
    top_chunks = chunk_dicts[:8]

    quality_score = 0.55
    if paperqa_chunks:
        quality_score += 0.2
    if openalex_chunks:
        quality_score += 0.15
    if local_chunks:
        quality_score += 0.05
    quality_score = min(0.98, quality_score)

    return {
        "query": user_query,
        "all_chunks": top_chunks,
        "method_metadata": _build_method_metadata(top_chunks),
        "references": _build_references(top_chunks),
        "quality_score": quality_score,
        "quality_warning": "；".join(warnings) if warnings else None,
        "source_stats": {
            "local_file": len(local_chunks),
            "paperqa": len(paperqa_chunks),
            "openalex": len(openalex_chunks),
            "fallback": len(fallback_chunks),
        },
    }
