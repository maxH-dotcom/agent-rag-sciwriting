#!/usr/bin/env python3
"""
paper-qa lightweight wrapper — uses sentence-transformers + Groq directly.
Bypasses paper-qa's LiteLLM/LiteLLMModel to avoid structured-content API errors.
"""

import sys
import json
import os
import asyncio
import hashlib
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: str, chunk_size: int = 1000) -> list[dict]:
    """Extract text chunks from PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        from paperqa_pypdf import PdfReader

    chunks = []
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        # Split into overlapping chunks
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            chunk_id = hashlib.md5(f"{pdf_path}:{i}".encode()).hexdigest()[:12]
            chunks.append({
                "chunk_id": f"chunk_{chunk_id}",
                "text": chunk_text,
                "source": pdf_path,
                "page_start": i // chunk_size + 1,
            })
    except Exception as e:
        print(f"WARNING: Failed to extract PDF {pdf_path}: {e}", file=sys.stderr)

    return chunks


# ---------------------------------------------------------------------------
# Embedding via sentence-transformers (in-process, no LiteLLM)
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer
    _EMBEDDER: Optional[SentenceTransformer] = None

    def _get_embedder() -> SentenceTransformer:
        global _EMBEDDER
        if _EMBEDDER is None:
            _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        return _EMBEDDER

    def embed_chunks(chunks: list[dict]) -> list[dict]:
        """Add embedding vectors to chunks."""
        texts = [c["text"] for c in chunks]
        embedder = _get_embedder()
        vectors = embedder.encode(texts, show_progress_bar=False)
        for chunk, vec in zip(chunks, vectors):
            chunk["embedding"] = vec.tolist()
        return chunks

    def cosine_sim(a: list, b: list) -> float:
        """Dot product of normalized vectors."""
        import numpy as np
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def search_chunks(chunks: list[dict], query: str, top_k: int = 5) -> list[dict]:
        """Semantic search with cosine similarity."""
        embedder = _get_embedder()
        query_vec = embedder.encode([query])[0]
        for chunk in chunks:
            chunk["score"] = cosine_sim(chunk["embedding"], query_vec.tolist())
        chunks.sort(key=lambda x: x["score"], reverse=True)
        return chunks[:top_k]

    EMBEDDINGS_OK = True

except ImportError:
    EMBEDDINGS_OK = False
    print("WARNING: sentence-transformers not available, using text matching", file=sys.stderr)

    def search_chunks(chunks: list[dict], query: str, top_k: int = 5) -> list[dict]:
        """Fallback text matching."""
        q_lower = query.lower()
        for chunk in chunks:
            # Simple word overlap score
            words = set(chunk["text"].lower().split())
            query_words = set(q_lower.split())
            chunk["score"] = len(words & query_words) / max(len(query_words), 1)
        chunks.sort(key=lambda x: x["score"], reverse=True)
        return chunks[:top_k]


# ---------------------------------------------------------------------------
# Groq LLM — direct API call (not via LiteLLM to avoid structured-content issues)
# ---------------------------------------------------------------------------

async def _groq_complete(
    prompt: str,
    model: str = "groq/llama-3.1-8b-instant",
    api_key: Optional[str] = None,
    max_tokens: int = 512,
) -> str:
    """Call Groq API directly via httpx."""
    import httpx

    if api_key is None:
        api_key = os.environ.get("GROQ_API_KEY", "")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model.removeprefix("groq/"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Main search function
# ---------------------------------------------------------------------------

async def search_papers(query: str, paper_files: list[str]) -> dict:
    """Add PDFs, embed, search, and generate answer via Groq."""

    if not EMBEDDINGS_OK:
        return {"chunks": [], "answer": "", "error": "sentence-transformers not available"}

    # 1. Extract text from all PDFs
    all_chunks: list[dict] = []
    for pdf_path in paper_files:
        path = Path(pdf_path)
        if path.exists() and path.suffix.lower() == ".pdf":
            chunks = extract_pdf_text(str(path))
            all_chunks.extend(chunks)

    if not all_chunks:
        return {"chunks": [], "answer": "", "error": f"No readable PDFs found in {paper_files}"}

    # 2. Embed all chunks
    all_chunks = embed_chunks(all_chunks)

    # 3. Semantic search
    top_chunks = search_chunks(all_chunks, query, top_k=5)

    # 4. Build context from top chunks
    context_parts = []
    for i, c in enumerate(top_chunks, 1):
        context_parts.append(f"[文献{i}]\n{c['text'][:500]}")

    context = "\n\n---\n\n".join(context_parts)

    # 5. Generate answer via Groq
    answer = await _groq_complete(
        prompt=(
            f"Based on the following literature excerpts, answer the research question.\n"
            f"Research question: {query}\n\n"
            f"Literature excerpts:\n{context}\n\n"
            f"Provide a concise answer with citations in brackets [文献#]."
        ),
        max_tokens=800,
    )

    # 6. Build result chunks (without embeddings, for JSON serialization)
    result_chunks = []
    for c in top_chunks:
        result_chunks.append({
            "chunk_id": c["chunk_id"],
            "text": c["text"][:800],
            "source": c["source"],
            "score": round(c["score"], 4),
        })

    return {
        "chunks": result_chunks,
        "answer": answer,
        "error": None,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"chunks": [], "answer": "", "error": f"Invalid input: {e}"}), file=sys.stderr)
        sys.exit(1)

    query = data.get("query", "")
    paper_files = data.get("paper_files", [])

    if not query:
        print(json.dumps({"chunks": [], "answer": "", "error": "No query provided"}), file=sys.stderr)
        sys.exit(1)

    if not paper_files:
        print(json.dumps({"chunks": [], "answer": "", "error": "No paper files provided"}), file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(search_papers(query, paper_files))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
