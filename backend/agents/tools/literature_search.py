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


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """从 OpenAlex abstract_inverted_index 重建摘要文本。"""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def _extract_openalex_metadata(item: dict[str, Any], abstract: str) -> tuple[str, str, str, str]:
    """从 OpenAlex 条目中提取 method_name, source_region, source_domain, data_structure。"""
    title = (item.get("title") or "").lower()
    text_lower = (title + " " + abstract).lower()

    # 从 concepts 提取领域
    concepts = item.get("concepts") or []
    concept_names = [c.get("display_name", "").lower() for c in concepts]
    concept_str = " ".join(concept_names)

    # --- source_domain ---
    source_domain = "待解析"
    domain_rules = [
        (["carbon", "emission", "greenhouse", "climate change", "co2", "碳排放", "碳减排", "温室气体", "低碳"], "碳排放/气候变化"),
        (["agricult", "farm", "crop", "soil", "irrigation", "livestock", "农业", "种植业", "畜牧", "耕地"], "农业经济学"),
        (["transport", "rail", "high-speed", "logistics", "traffic", "交通", "铁路", "物流", "高铁"], "交通/物流"),
        (["urban", "city", "spatial", "land use", "housing", "城市", "城镇化", "土地利用", "空间"], "城市/土地利用"),
        (["energy", "electricity", "renewable", "solar", "wind power", "能源", "电力", "可再生", "光伏"], "能源经济学"),
        (["trade", "export", "import", "tariff", "globalization", "贸易", "出口", "进口", "关税"], "国际贸易"),
        (["health", "mortality", "disease", "medical", "hospital", "健康", "医疗", "疾病", "死亡率"], "健康经济学"),
        (["education", "school", "student", "university", "learning", "教育", "学校", "高校", "人力资本"], "教育经济学"),
        (["finance", "banking", "stock", "monetary", "credit", "金融", "银行", "股票", "信贷"], "金融经济学"),
        (["environment", "pollution", "ecology", "biodiversity", "环境", "污染", "生态", "环保"], "环境经济学"),
    ]
    search_text = text_lower + " " + concept_str
    for keywords, domain in domain_rules:
        if any(k in search_text for k in keywords):
            source_domain = domain
            break

    # --- method_name ---
    method_name = "待解析"
    method_rules = [
        (["difference-in-difference", "difference in difference", "did ", "双重差分", "倍差法"], "双重差分"),
        (["fixed effect", "固定效应", "panel regression", "面板回归"], "固定效应模型"),
        (["instrumental variable", "iv ", "2sls", "two-stage", "工具变量"], "工具变量法"),
        (["regression discontinuity", "rdd", "断点回归"], "断点回归"),
        (["propensity score", "psm", "倾向得分匹配"], "倾向得分匹配"),
        (["synthetic control", "合成控制"], "合成控制法"),
        (["stirpat", "stochastic impacts"], "STIRPAT模型"),
        (["spatial econometric", "spatial lag", "空间计量", "spatial durbin", "空间杜宾", "空间自回归"], "空间计量模型"),
        (["gmm", "generalized method of moments", "dynamic panel", "动态面板", "广义矩估计"], "GMM动态面板"),
        (["meta-analysis", "meta analysis", "荟萃分析"], "Meta分析"),
        (["machine learning", "random forest", "neural network", "deep learning", "机器学习", "随机森林", "神经网络", "深度学习"], "机器学习"),
        (["granger causality", "var ", "vector autoregression", "格兰杰因果", "向量自回归"], "VAR/格兰杰因果"),
        (["lmdi", "因素分解", "decomposition analysis", "kaya identity"], "LMDI分解分析"),
        (["dea", "data envelopment", "数据包络", "效率分析", "sbm model", "sbm模型"], "DEA效率分析"),
        (["tobit", "受限因变量", "censored regression"], "Tobit模型"),
        (["threshold effect", "门槛效应", "threshold regression", "门槛回归"], "门槛回归模型"),
        (["mediation", "中介效应", "mediating effect"], "中介效应分析"),
        (["ekc", "kuznets", "库兹涅茨", "倒u型"], "EKC假说检验"),
    ]
    for keywords, method in method_rules:
        if any(k in search_text for k in keywords):
            method_name = method
            break

    # --- data_structure ---
    data_structure = "待解析"
    if any(k in search_text for k in ["panel data", "panel model", "面板数据", "longitudinal", "省域面板", "省份面板", "省级面板", "市级面板"]):
        data_structure = "面板数据"
    elif any(k in search_text for k in ["cross-section", "cross section", "截面数据", "横截面"]):
        data_structure = "截面数据"
    elif any(k in search_text for k in ["time series", "时间序列", "time-series"]):
        data_structure = "时间序列"
    elif any(k in search_text for k in ["survey data", "micro data", "微观数据", "调查数据", "家庭调查", "企业调查"]):
        data_structure = "微观调查数据"

    # --- source_region ---
    source_region = "待解析"
    region_rules = [
        (["china", "chinese", "中国", "省域", "省份", "我国"], "中国"),
        (["india", "indian"], "印度"),
        (["united states", "u.s.", "american"], "美国"),
        (["europe", "european", "eu "], "欧洲"),
        (["africa", "african", "sub-saharan"], "非洲"),
        (["japan", "japanese", "日本"], "日本"),
        (["korea", "korean", "韩国"], "韩国"),
        (["brazil", "brazilian"], "巴西"),
        (["southeast asia", "asean", "东南亚", "东盟"], "东南亚"),
        (["global", "worldwide", "international", "cross-country", "跨国", "全球"], "全球/跨国"),
        (["developing countr", "low-income", "emerging", "发展中国家"], "发展中国家"),
    ]
    for keywords, region in region_rules:
        if any(k in search_text for k in keywords):
            source_region = region
            break

    return method_name, source_region, source_domain, data_structure


def _openalex_chunks(user_query: str) -> tuple[list[LiteratureChunk], str | None]:
    if os.environ.get("RESEARCH_ASSISTANT_DISABLE_REMOTE_SEARCH", "0") == "1":
        return [], "远程检索已通过环境变量关闭。"

    url = (
        f"https://api.openalex.org/works?search={quote_plus(user_query)}"
        f"&filter=has_abstract:true"
        f"&per-page=5&sort=relevance_score:desc"
    )
    try:
        with urlopen(url, timeout=8) as response:  # pragma: no cover - network dependent
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network dependent
        return [], f"OpenAlex 检索失败: {exc}"

    results = payload.get("results", [])
    chunks: list[LiteratureChunk] = []
    for index, item in enumerate(results, start=1):
        title = item.get("title") or f"openalex_{index}"
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))

        # 作者信息
        authorships = item.get("authorships") or []
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in authorships[:3]
            if a.get("author", {}).get("display_name")
        ]
        author_str = "; ".join(authors) if authors else "未知作者"

        # 发表年份和期刊
        year = item.get("publication_year") or ""
        venue = ""
        primary_loc = item.get("primary_location") or {}
        source_info = primary_loc.get("source") or {}
        venue = source_info.get("display_name") or ""

        # 元数据提取
        method_name, source_region, source_domain, data_structure = _extract_openalex_metadata(item, abstract)

        # 构建富文本
        text_parts = [title]
        if abstract:
            text_parts.append(f"\n\n摘要: {abstract[:400]}")
        if venue:
            text_parts.append(f"\n\n期刊: {venue}")
        if year:
            text_parts.append(f"\n\n年份: {year}")

        # concepts 标签
        concepts = item.get("concepts") or []
        top_concepts = [c.get("display_name", "") for c in concepts[:5] if c.get("display_name")]
        if top_concepts:
            text_parts.append(f"\n\n关键概念: {', '.join(top_concepts)}")

        source_label = f"OpenAlex: {author_str}" + (f" ({year})" if year else "")

        chunks.append(
            LiteratureChunk(
                chunk_id=f"openalex_{index:03d}",
                title=title,
                source=source_label,
                source_type="openalex",
                text="".join(text_parts)[:800],
                method_name=method_name,
                source_region=source_region,
                source_domain=source_domain,
                data_structure=data_structure,
                relevance_score=max(0.45, 0.88 - index * 0.06),
                url=item.get("id"),
            )
        )
    return chunks, None


def _zotero_chunks(user_query: str) -> tuple[list[LiteratureChunk], str | None]:
    """从用户 Zotero 个人库搜索文献。"""
    from backend.core.config import ZOTERO_API_KEY

    if not ZOTERO_API_KEY:
        return [], "ZOTERO_API_KEY 未配置，跳过 Zotero 检索。"

    import re

    try:
        # 先获取用户信息（API Key 验证 + userID）
        from urllib.request import Request

        req = Request(
            "https://api.zotero.org/keys/" + ZOTERO_API_KEY,
            headers={"Zotero-API-Key": ZOTERO_API_KEY},
        )
        with urlopen(req, timeout=5) as resp:
            key_info = json.loads(resp.read().decode("utf-8"))
        user_id = key_info.get("userID")
        if not user_id:
            return [], "Zotero API Key 用户信息无效。"
    except Exception as exc:
        return [], f"Zotero API Key 验证失败: {exc}"

    try:
        # 搜索用户库
        encoded_q = quote_plus(user_query)
        url = f"https://api.zotero.org/users/{user_id}/items?q={encoded_q}&format=json&limit=8&itemType=journalArticle"
        req = Request(url, headers={"Zotero-API-Key": ZOTERO_API_KEY})
        with urlopen(req, timeout=8) as resp:
            items = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return [], f"Zotero 库检索失败: {exc}"

    chunks: list[LiteratureChunk] = []
    for index, item in enumerate(items[:8]):
        data = item.get("data", {})
        title = data.get("title", "无标题")
        creators = data.get("creators", [])
        author_str = "; ".join(
            f"{c.get('lastName', '')} {c.get('firstName', '')}".strip()
            for c in creators[:3]
            if c.get("lastName")
        ) or "未知作者"
        year = data.get("date", "")[:4] if data.get("date") else ""
        abstract = data.get("abstractNote", "")[:300]
        publication = data.get("publicationTitle", "") or data.get("bookTitle", "")

        # 提取领域关键词
        domain = "未知领域"
        text_lower = (title + " " + abstract).lower()
        if any(k in text_lower for k in ["carbon", "emission", "climate", "greenhouse"]):
            domain = "碳排放/气候变化"
        elif any(k in text_lower for k in ["agricult", "farm", "crop", "soil"]):
            domain = "农业经济学"
        elif any(k in text_lower for k in ["transport", "rail", "high-speed"]):
            domain = "交通/物流"
        elif any(k in text_lower for k in ["urban", "city", "spatial", "land"]):
            domain = "城市/土地利用"

        # 判断数据结构
        data_structure = "待解析"
        if abstract:
            if any(k in abstract.lower() for k in ["panel", "固定效应", "差分", "did"]):
                data_structure = "面板数据"
            elif any(k in abstract.lower() for k in ["cross-section", "截面", "横截面"]):
                data_structure = "截面数据"

        text_content = title
        if abstract:
            text_content += f"\n\n摘要: {abstract}"
        if publication:
            text_content += f"\n\n期刊: {publication}"
        if year:
            text_content += f"\n\n年份: {year}"

        chunks.append(
            LiteratureChunk(
                chunk_id=f"zotero_{index + 1:03d}",
                title=title,
                source=f"Zotero: {author_str}" + (f" ({year})" if year else ""),
                source_type="zotero",
                text=text_content,
                method_name="待解析",
                source_region="待解析",
                source_domain=domain,
                data_structure=data_structure,
                relevance_score=0.88 - index * 0.04,
                url=data.get("url") or f"https://www.zotero.org/{key_info.get('username', 'user')}/items/{data.get('key')}",
            )
        )

    if not chunks:
        return [], f"Zotero 库中未找到与「{user_query}」相关的文献。"

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
    zotero_chunks, zotero_warning = _zotero_chunks(user_query)
    paperqa_chunks, paperqa_warning = _paperqa_chunks(user_query, paper_files)
    openalex_chunks, openalex_warning = _openalex_chunks(user_query)

    if zotero_warning:
        warnings.append(zotero_warning)
    if paperqa_warning:
        warnings.append(paperqa_warning)
    if openalex_warning:
        warnings.append(openalex_warning)

    # Zotero 库优先（用户个人 curation），其次 local_files、paperqa、openalex、fallback
    merged_chunks = zotero_chunks + local_chunks + paperqa_chunks + openalex_chunks + fallback_chunks
    merged_chunks.sort(key=lambda chunk: chunk.relevance_score, reverse=True)

    chunk_dicts = [chunk.to_dict() for chunk in merged_chunks]
    top_chunks = chunk_dicts[:8]

    quality_score = 0.55
    if zotero_chunks:
        quality_score += 0.15
    if paperqa_chunks:
        quality_score += 0.15
    if openalex_chunks:
        quality_score += 0.1
    if local_chunks:
        quality_score += 0.05
    quality_score = min(0.99, quality_score)

    return {
        "query": user_query,
        "all_chunks": top_chunks,
        "method_metadata": _build_method_metadata(top_chunks),
        "references": _build_references(top_chunks),
        "quality_score": quality_score,
        "quality_warning": "；".join(warnings) if warnings else None,
        "source_stats": {
            "zotero": len(zotero_chunks),
            "local_file": len(local_chunks),
            "paperqa": len(paperqa_chunks),
            "openalex": len(openalex_chunks),
            "fallback": len(fallback_chunks),
        },
    }
