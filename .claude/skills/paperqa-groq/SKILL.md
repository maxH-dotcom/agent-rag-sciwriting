---
name: paperqa-groq
description: Test paper-qa + Groq configuration in .venv-paperqa
---

# Paper-qa + Groq Integration Test

## 验证状态

paper-qa + Groq 配置已验证成功（2026-04-06）。

## 关键发现

### 正确的配置方式

paper-qa 2026.3.18 + Groq 不能用 `LLM=groq/...` 环境变量，必须用 `model_list` litellm 格式：

```python
GROQ_CONFIG = dict(
    model_list=[dict(
        model_name="groq/llama-3.1-8b-instant",
        litellm_params=dict(
            model="groq/llama-3.1-8b-instant",
            api_base="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
            temperature=0.1,
        ),
    )]
)
```

同时需要配置：
- `embedding="st-all-MiniLM-L6-v2"`（sentence-transformers，本地 embedding）
- `summary_llm` 和 `llm` 都要单独配置 Groq
- `parsing.multimodal=MultimodalOptions.ON_WITHOUT_ENRICHMENT` 避免 media enrichment 走 gpt-4o

### paper-qa 架构问题

paper-qa 的 `summary_llm` 会传递 **structured content blocks**（含图片/表格元数据）给 LLM，
Groq 的 `/chat/completions` API 只接受纯字符串 content，导致 `messages[N].content must be a string` 错误。

### 解决方案

新建 `backend/agents/tools/paperqa_wrapper.py`，使用轻量级架构：
1. **PyPDF** 提取 PDF 文本
2. **sentence-transformers** 本地 embedding（all-MiniLM-L6-v2）
3. **Groq API 直调**（httpx，非 LiteLLM）生成答案

直接 HTTP 调用绕过了 paper-qa → LiteLLM → LiteLLMModel 的 structured-content 兼容问题。

### 依赖

```bash
# .venv-paperqa 中已安装
pip install paper-qa pillow sentence-transformers groq
```

## 测试命令

```bash
GROQ_API_KEY='gsk_...' ".venv-paperqa/bin/python" backend/agents/tools/paperqa_wrapper.py
# stdin: {"query": "...", "paper_files": ["/path/to/paper.pdf"]}
```

## 端到端测试

```bash
GROQ_API_KEY='gsk_...' ".venv-paperqa/bin/python" -c "
import os; os.environ['GROQ_API_KEY'] = 'gsk_...'
from backend.agents.tools.literature_search import retrieve_literature
result = retrieve_literature('碳排放 农业 影响', ['/Volumes/hmq/文献/papers/2210.00001.pdf'])
print(result['source_stats'])  # 应显示 paperqa: 5
"
```
