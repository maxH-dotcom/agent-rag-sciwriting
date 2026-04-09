# 智能科研工作助手 - 项目状态

> 最后更新：2026-04-08（前端科研工作流闭环与真实数据回归已完成，进入测试与摘要增强收口）

---

## 已完成项目

### 1. 后端核心框架
- FastAPI + 6 Node 编排链路（data_mapping → literature → novelty → analysis → brief → writing）
- `/tasks`、`/tasks/{id}`、`/continue`、`/abort`、`/history`、`/checkpoints` 全套 API
- TaskStore 持久化层（文件后端 + Redis 后端可切换）
- 21/21 测试通过

### 2. 数据映射节点（data_mapping）
- 读取真实 CSV 文件列名和前3行预览
- 明确错误处理：文件不存在/非CSV/未提供文件各有对应提示
- fallback 列名支持无文件场景

### 3. 文献检索适配层
检索优先级：Zotero > local_files > paper-qa > OpenAlex > fallback

**已接入：**
- **Zotero API**：从用户个人库搜索文献，返回标题/作者/年份/摘要/URL，`~/.research_assistant/zotero_config.json` 自动读取 Key
- **OpenAlex API**：真实 HTTP 检索，返回相关文献标题
- **Fallback 规则库**：内置碳排放/面板数据/双重差分等方法知识

**待接入：**
- paper-qa：本地 PDF 语义检索（需安装 + 有 PDF 文件）
- OpenAlex 字段扩展：abstract、methods、concepts 等

### 4. 中断点系统
5 个人工审核中断点：
1. `data_mapping_required` — 确认因变量/自变量/控制变量映射
2. `literature_review_required` — 审核文献检索结果
3. `novelty_result_ready` — 确认创新性和迁移方向
4. `code_plan_ready` — 确认分析代码方案
5. `brief_ready_for_review` — 确认 Research Brief

### 5. Redis 基础设施
- Redis 服务已安装并启动（`brew services start redis`）
- `TaskRepository` + `CheckpointRepository` 支持 Redis 后端（`TASK_REPOSITORY_BACKEND=redis`）
- `LangGraphResearchRuntime` + `MemorySaver` 可用（`ORCHESTRATION_BACKEND=langgraph`）
- ⚠️ `langgraph-checkpoint-redis` 依赖 RedisJSON 模块，当前环境未加载

### 6. E2E 测试
- `test_e2e_interrupt_flow.py`：覆盖 create→中断→modified→approved→done 完整链路
- `test_api_unittest.py`：API 层测试
- `test_orchestrator.py`：编排器中断序列测试
- `test_unittest_smoke.py`：持久化和集成测试

### ~~7. 前端暂停~~ → ✅ 已重构（见 §12）

### 8. OpenAlex 文献质量提升（A）
- `_reconstruct_abstract()`：从 `abstract_inverted_index` 重建完整摘要
- `_extract_openalex_metadata()`：基于摘要+标题+concepts 提取方法/领域/地区/数据结构
- API 参数优化：`has_abstract:true` 过滤 + `relevance_score:desc` 排序，返回 5 条
- 覆盖：10 领域、18 方法、4 数据结构类型、11 地区，中英文关键词双覆盖
- `source` 字段格式化为 `OpenAlex: 作者名 (年份)`，`text` 包含摘要+期刊+年份+关键概念

**待完善：**
- OpenAlex 英文搜索相关性有限（搜索引擎本身限制），方法类关键词命中率低于领域/地区
- 部分论文摘要中不提及具体方法名称时 `method_name` 仍为"待解析"，可考虑结合 LLM 辅助提取
- `concepts` 字段可进一步用于自动映射 `method_name`（OpenAlex concepts 有层级结构，level 0-5）
- 英文查询结果与查询意图偏差较大时，可尝试拼接 `filter=concepts.id:C...` 做概念级过滤

### 9. 真实文件上传机制（D）
- `POST /upload` multipart 端点，支持多文件同时上传
- 自动判断文件类型（`kind=auto`）：CSV/XLSX→data，PDF/TXT/MD→paper
- 支持显式指定 `kind=data` 或 `kind=paper`，带后缀校验
- 文件保存至 `UPLOAD_DIR`（默认 `.runtime/uploads/`，可通过环境变量覆盖）
- UUID 前缀防止文件名冲突，50 MB 大小限制
- 返回服务端绝对路径，可直接传入 `POST /tasks` 的 `data_files`/`paper_files`
- 7 个新测试覆盖：auto/explicit kind、多文件、后缀校验、kind 不匹配、upload→task 完整链路
- 28/28 测试全部通过

### 13. 实时任务状态流 + Excel 数据支持（2026-04-08）
**状态：✅ 已完成**

- 后端新增 `GET /tasks/{id}/stream` SSE 端点，支持任务详情页和工作台实时订阅状态变化
- 前端 `InterruptManager` 改为优先使用 SSE，连接失败自动回退到 3 秒轮询
- 任务详情页新增实时连接状态展示：建立连接 / SSE 推送 / 轮询回退 / 状态已稳定
- `data_mapping_node.py` 补齐 `.xlsx` / `.xls` 读取，避免上传支持 Excel 但分析节点只认 CSV 的断层
- 修复 `text_to_code_bridge.py` 中 Panel FE / OLS 模板的内层 f-string 转义问题，E2E 流程恢复可跑通
- `requirements.txt` 补齐 `pandas` 与 `openpyxl`，README 新增依赖安装步骤
- `.gitignore` 补充 `.venv-paperqa/` 和 `scw agent mvp/venv/`，避免环境目录污染版本库
- 新增测试覆盖：SSE 流、Excel 文件创建任务

### 14. 真实数据验收脚本与问题集回归（2026-04-08）
**状态：✅ 8 题真实数据验收问题集首轮全部通过**

- 新增 [scripts/real_data_acceptance.py](/Volumes/hmq/智能科研工作助手/scripts/real_data_acceptance.py)，用于基于 FastAPI `TestClient` 跑真实数据验收
- 当前脚本已覆盖：
  - CSV 直接建任务
  - Excel 上传后建任务
  - 中断后全链路 continue 到 `writing`
  - 写作草稿结果产出校验
- 2026-04-08 首轮执行结果：8/8 通过，0 个 bad case
  - `Q1` CSV 变量映射推荐
  - `Q2` CSV 描述性统计与主要特征总结
  - `Q3` CSV 基础回归分析
  - `Q4` CSV 面板固定效应尝试与解释
  - `Q5` Excel 关键变量关系比较
  - `Q6` CSV 论文结果分析草稿
  - `Q7` Excel 字段识别与变量角色建议
  - `Q8` Excel OLS / DID / Panel FE 方法选择解释
- 当前环境使用 `scw agent mvp/venv/bin/python` 跑通；主环境仍缺 `fastapi/pytest`
- `bad case/` 目录保留自动落盘逻辑，一旦真实数据失败会自动生成记录文件

### 10. Text-to-Code Bridge（C）
- **证据提取**：从 `literature_result` 中提取 `EvidencePackage`，自动检测缺失面（因变量/自变量/文献/方法）
- **代码生成**：基于数据映射 + 文献证据 + 模型推荐，生成完整可执行的 Python 分析脚本
  - 支持 4 种方法模板：OLS 回归、Panel FE 固定效应、DID 双重差分、STIRPAT 模型
  - 代码包含数据读取、变量准备、清洗、描述统计、回归、结构化输出 6 步完整流程
  - 每个关键步骤绑定证据来源 (`EvidenceBinding`)
- **安全检查**：AST 语法检查 + 正则危险操作拦截 + import 白名单
  - 禁止 `os.system`/`subprocess`/`eval`/`exec`/`__import__`
  - 白名单：pandas, numpy, scipy, statsmodels, sklearn, matplotlib 等分析库
- **Subprocess 沙箱执行**：临时目录隔离 + 数据文件符号链接 + 超时保护 + 最小化环境变量
- **analysis_node 集成**：中断数据包含代码脚本、执行结果、bridge 状态、适应性解释
- 25 个新测试覆盖：安全检查(10)、沙箱执行(4)、证据提取(2)、代码生成(5)、Bridge 集成(2)、模型序列化(2)

**待完善：**
- 代码生成目前为规则模板，后续可接入 LLM 生成更灵活的代码
- 沙箱执行依赖系统 Python + 已安装的分析库（pandas/statsmodels/linearmodels）
- 执行失败时的自动重试和代码修正机制（Phase2 安全与稳定性）

**新增文件：**
| 文件 | 作用 |
|------|------|
| `backend/agents/models/code_generation.py` | 数据模型（EvidencePackage, GeneratedCode, ExecutionResult 等） |
| `backend/core/sandbox.py` | 代码安全检查 + subprocess 沙箱执行 |
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | Bridge 完整流程（证据→生成→检查→执行） |
| `tests/test_text_to_code_bridge.py` | 25 个测试用例 |

### 11. Benchmark 测试套件搭建（2026-04-06 ~ 2026-04-07）
**状态：✅ 全部 63 个测试通过**

**文件结构：**
- `benchmark/retrieval/cases.json` — 15 个检索测试用例
- `benchmark/text_to_code/cases.json` — 18 个代码生成测试用例
- `benchmark/citation/cases.json` — 15 个引用溯源测试用例（全部与实际 chunk 文本对齐）
- `benchmark/e2e/cases.json` — 12 个端到端流程测试用例
- `benchmark/fixtures/retrieval/chunks.json` — 20 个真实文本 chunks
- `benchmark/fixtures/text_to_code/*.csv` — 15 个 CSV 测试数据文件
- `benchmark/mock_client.py` — MockAgentClient（中文 bigram 分词）
- `benchmark/evaluator.py` — BenchmarkEvaluator（修复了 keyword recall 和 stdout JSON 解析）
- `benchmark/run_evaluation.py` — CLI 评测报告生成器
- `tests/test_benchmark_*.py` — 4 个测试文件

**测试覆盖：**
| 类别 | 测试方法数 | 说明 |
|------|-----------|------|
| retrieval | 12 | 关键词匹配/语义检索/Recall@5/Precision@K/噪声查询/空结果 |
| text_to_code | 22 | 基础计算/回归/面板数据/可视化/安全拦截/沙箱执行 |
| citation | 15 | 精确溯源/漂移检测/矛盾检测/过度泛化/溯源链 |
| e2e | 14 | 流程中断/用户拒绝/多节点审批/路由准确性/节点顺序 |

**关键修复：**
- Mock 中文分词：空格 split → 字符 bigram（解决中文检索永远为 0 的问题）
- Keyword recall 计算：从搜索 chunk ID 改为搜索实际文本内容
- `output_data` 为空时：回退解析 stdout 中的 JSON 结构化输出
- Citation cases：全部 15 个 expected_source 与实际 chunk 文本重新对齐
- Optional 依赖测试：statsmodels/sklearn/scipy 未安装时条件通过而非 crash

**中优先级待修复：**
- ✅ `forbidden_operations` 参数在 evaluator._security_check 中被忽略（2026-04-07 修复）
- ✅ 14 个 case 有定义但无对应测试方法（2026-04-07 补全）
- ✅ 无 CI 配置文件（2026-04-07 添加 `.github/workflows/benchmark.yml`）

**本次新增修复：**
- `evaluator._security_check()`：支持 case 级 `forbidden` 动态模式，基础白名单独立生效
- `test_benchmark_text_to_code.py`：补全 code_008/015/016/017/018 五个测试
- `test_benchmark_retrieval.py`：补全 ret_003/006/010/011/012/013/014 七个测试
- 所有沙箱执行测试改为条件通过（pandas 未安装时不 crash）
- `.github/workflows/benchmark.yml`：macOS + Python 3.9矩阵，4类别并行测试
- `benchmark/reporting/report_generator.py`：`ReportGenerator` 类（Markdown + HTML 报告，整合人工评分）
- `benchmark/run_evaluation.py`：重写使用 `ReportGenerator`，输出 JSON/MD/HTML 三种格式

### 12. 前端重构 v2.0（2026-04-07）
**状态：⚠️ 视觉框架、SSE 实时通讯与科研工作流主路径已基本打通；真实数据验收与自动化测试仍待补齐**

**设计系统：**
- Navy 深色主题全面替换浅色 Teal 主题（`#0F172A` 背景 + `#38BDF8` 强调）
- 双字体策略：Crimson Pro（文献/简报）+ Atkinson Hyperlegible（界面/数据）
- 所有 CSS Module 对齐新设计系统

**Zustand 状态管理：**
- `lib/stores/task-store.ts` — 任务全局状态，含 3 秒轮询逻辑
- `lib/stores/settings-store.ts` — API Key + 科研偏好状态
- `lib/stores/model-store.ts` — 变量映射状态

**核心组件（新建）：**
| 组件 | 功能 |
|------|------|
| `FileUploader` | 拖拽上传 + 进度条 + 文件列表 |
| `TaskProgress` | 横向 Stepper，五种节点状态视觉 |
| `TaskDetail` | 按 result 类型分发渲染（Table/Cards/Code/Markdown） |
| `InterruptManager` | 集成 TaskProgress + 轮询状态更新 |

**2026-04-08 已完成推进：**
- `FileUploader` 已真正接入 [task-console.tsx](/Volumes/hmq/智能科研工作助手/frontend/components/task-console.tsx)，支持数据文件与论文文件上传
- `/upload` 前后端协议已对齐，上传结果会自动回填到创建任务请求，无需手填绝对路径
- 结果页与中断页已从“原始 JSON 优先”调整为“结构化科研结果优先”
- `InterruptManager` 已支持 5 个关键中断点中的 5 个结构化审核分支：
  - `data_mapping_required`
  - `literature_review_required`
  - `novelty_result_ready`
  - `code_plan_ready`
  - `brief_ready_for_review`
- `task-detail.tsx` 的中断数据标签页已按节点类型结构化渲染，而不是统一 dump JSON

**当前剩余缺口（2026-04-08 晚间补记）：**
- 前端虽然已有结构化结果页，但某些分析场景的“统计结论摘要”仍可继续增强，尤其是更复杂模型或多系数解释
- 前端交互自动化测试尚未补齐；当前验证主要依赖 `npm run build`
- 主环境缺少 `pytest` 模块，但已可通过 `scw agent mvp/venv/bin/python` 运行真实数据验收脚本
- `InterruptManager` 与 `TaskDetail` 的结构化展示仍有共享渲染层可抽取，后续可进一步减少重复维护成本

**设置页增强：**
- API Key 管理：密码掩码 + 显示/隐藏 + 连接状态（已保存不回显密钥）
- 科研偏好：分析方法/显著性水平/文献数量/数据编码/年份转换
- 模型连接测试按钮

**待后续迭代：**
- Monaco Editor IDE（代码编辑器）
- Variable Mapper（双栏变量映射视图）
- 更强的结果摘要层（结论/表格/统计摘要/图表说明）
- 中断审核组件与任务详情页共享一套结构化渲染逻辑，消除重复展示

**新建文件：**
| 文件 | 作用 |
|------|------|
| `lib/stores/task-store.ts` | 任务 Zustand Store |
| `lib/stores/settings-store.ts` | 设置 Zustand Store |
| `lib/stores/model-store.ts` | 变量映射 Zustand Store |
| `components/file-uploader.tsx` + `.module.css` | 文件上传组件 |
| `components/task-progress.tsx` + `.module.css` | 任务进度 Stepper |
| `components/task-detail.tsx` + `.module.css` | 任务详情结构化渲染 |
| `src/app/settings/page.tsx` | 重构后的设置页 |
| `frontend/src/app/globals.css` | Navy 深色主题全局 CSS |

---

## 待完成项目（按优先级）

### 高优先级

#### I. 前端科研工作流闭环（新增，2026-04-08）
**目标：** 让用户可以不手填绝对路径、不阅读原始代码/JSON，也能完成一次从上传到结果消费的科研流程。

**当前状态：** ⚠️ 主路径基本完成，待真实数据验收与自动化测试收口

**必须完成：**
1. 工作台接入真实文件上传组件，支持数据文件与论文文件上传
2. 上传成功后自动回填服务端路径到任务创建请求，无需人工复制路径
3. 任务详情页优先展示研究结果，而不是优先展示代码和原始 JSON
4. 中断节点提供可操作的人类可读界面，而不是仅展示 `interrupt_data` 原文

**验收标准：**
- 在 [task-console.tsx](/Volumes/hmq/智能科研工作助手/frontend/components/task-console.tsx) 中可直接上传 `.csv/.xlsx/.xls/.pdf/.txt/.md`
- 上传成功后，用户能在界面看到文件名、类型、服务端路径和当前选中状态
- 创建任务时无需手动输入绝对路径，Network 请求中的 `data_files` / `paper_files` 自动带入上传结果
- 任一上传失败时，界面给出用户可读错误信息，不出现空白、崩溃或仅有控制台报错
- 任一上传成功后刷新任务详情页，不会丢失该任务的文件信息展示

**当前完成度（2026-04-08）：**
- [x] 工作台真实接入上传组件
- [x] 上传后自动回填服务端路径
- [x] 任务详情页默认优先展示结构化结果
- [x] 中断节点已有结构化交互界面
- [x] 真实数据验收脚本已落地
- [x] 完整 8 题验收集首轮已跑通
- [x] bad case 自动落盘机制已就位（当前 0 条失败）

#### J. 结果优先展示层（新增，2026-04-08）
**目标：** 从“给开发者看执行过程”升级为“给研究者看研究结论”。

**当前状态：** ⚠️ 已完成第一版结构化展示，仍需更强的分析摘要提炼

**必须完成：**
1. 数据映射结果以变量卡片/映射表呈现，并标出因变量、自变量、控制变量候选
2. 文献结果以文献卡片呈现，能读标题、作者、年份、摘要、出处
3. 分析结果优先展示模型名称、核心系数、显著性、样本量、R²、结论摘要
4. 代码仅作为可展开附属信息，不再占据默认主视图
5. 未识别结果类型时才退回原始 JSON

**验收标准：**
- `code_generation` 结果默认首屏不直接展示大段代码
- 若后端返回结构化执行结果，页面能展示“结论摘要 + 关键统计量 + 输出说明”
- 若后端仅返回代码和 stdout，也必须将 stdout 中的关键结果提炼为可读摘要，而不是整块原样抛出
- `interrupt_data` 默认以结构化视图展示；只有点击“查看原始数据”时才显示 JSON
- 任意结果页在移动端与桌面端都能完整阅读，不出现横向溢出导致主要内容不可读

**当前完成度（2026-04-08）：**
- [x] 数据映射结果以变量卡片 + 预览表展示
- [x] 文献结果以文献卡片展示
- [x] 分析结果优先展示模型、执行步骤、方案摘要、关键统计量与核心系数，代码折叠
- [x] 中断数据默认走结构化视图
- [x] 任务详情页中断标签页已按节点结构化渲染
- [x] 后端已显式返回 `result_summary`，前端不再主要依赖从 `stdout` 提取
- [ ] 更复杂模型场景下的中文结论摘要仍可继续增强

#### K. 中断审核与变量映射可用化（新增，2026-04-08）
**目标：** 让用户能在每个中断点真正“审核并继续”，而不是只能看状态。

**当前状态：** ✅ 主路径 5 个关键审核节点均已有结构化前端交互

**必须完成：**
1. `data_mapping_required` 提供双栏或表单式变量映射编辑
2. `literature_review_required` 支持勾选/保留/拒绝候选文献
3. `code_plan_ready` 支持查看计划摘要，并对方案做确认或修改
4. 各中断点继续后，页面状态能实时刷新并继续推进任务

**验收标准：**
- 至少 `data_mapping_required` 和 `code_plan_ready` 两个中断点具有真实可操作 UI
- 用户修改后的内容会被实际传给后端继续接口，而非只改前端显示
- 点击继续后不出现死循环、全页白屏、无限 loading 或必须手动刷新才能看到下一状态
- 中断态和完成态切换由 SSE 或轮询稳定驱动，连续操作 5 次以上不报错

**当前完成度（2026-04-08）：**
- [x] `data_mapping_required` 变量映射编辑
- [x] `literature_review_required` 文献勾选筛选
- [x] `novelty_result_ready` 创新性与迁移方向编辑
- [x] `code_plan_ready` 代码方案审核与调整
- [x] `brief_ready_for_review` Research Brief 审核
- [x] `continueTask` 已支持 `approved / modified / rejected` 与 payload 回传
- [x] `InterruptManager` 底部重复原始中断 JSON 已移除
- [ ] 前端交互自动化测试尚未补齐

#### ~~A. OpenAlex 文献质量提升~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §8，待完善点已记录**

#### B. paper-qa 接入 ✅ 已完成（2026-04-06）
**文件：**
- `backend/agents/tools/paperqa_wrapper.py` — 轻量级子进程 wrapper（重建）
- `backend/agents/tools/literature_search.py` — `_paperqa_chunks()` 子进程调用

**实现方案：**
- paper-qa 2026.3.18 安装在 `.venv-paperqa` 隔离环境中，避免与主环境 pydantic>=2 冲突
- `paperqa_wrapper.py` 轻量架构：PyPDF 提取文本 → sentence-transformers embedding → Groq API 直调生成答案
- 绕过了 paper-qa → LiteLLM → LiteLLMModel 的 structured-content API 兼容问题

**依赖（.venv-paperqa）：**
```
paper-qa pillow sentence-transformers groq
```

**使用方式：**
1. 主环境设置 `GROQ_API_KEY` 环境变量
2. API 调用时传入 PDF 路径列表（如 `/Volumes/hmq/文献/papers/`）
3. 子进程调用 wrapper，完成 PDF 解析 + embedding + 语义检索 + 答案生成

#### ~~C. Text-to-Code Bridge~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §10**

#### ~~D. 真实文件上传机制~~ ✅ 已完成（2026-04-06）
**详见已完成项目 §9**

### 中优先级

#### ~~E. scw agent mvp 逻辑迁移~~ ✅ 已完成（2026-04-07）
**目录：** `scw agent mvp/`
**合并内容：**
- `backend/agents/tools/question_parser.py`：VAR_ALIASES（16变量×多别名）、normalize_var_name()、多 Provider LLM（Anthropic/Groq/OpenAI）、规则 fallback
- `backend/agents/tools/model_recommender.py`：MODEL_RULES（7模型+文献出处）、infer_data_structure()、has_policy_shock/spatial_effect 参数

#### ~~F. Phase2 安全与稳定性~~ ✅ 已完成（2026-04-07）
**新增文件：**
- `backend/core/error_handling.py`：ErrorSeverity/ErrorInfo、ERROR_CLASSIFICATION（23种错误）、classify_error()、@with_retry（async/sync 通用，指数退避）
- `backend/core/logging/structured_logger.py`：JSONFormatter、StructuredLogger（ContextVar 协程安全）、set_context/with_context
- `backend/core/logging/events.py`：20+ 事件常量（节点/工具/任务/用户交互/性能）

#### ~~G. Phase3 评测体系~~ ✅ 已完成（2026-04-07）
**文件：** `Phase3-评测体系-设计文档.md`
**内容：** Benchmark 测试集、评估指标
**详见已完成项目 §11

### H. 后端优化：自定义模型与全链路编辑（规划中）
**文件：** `思路统筹/后端优化.md`

**核心目标：** 从单一"数据处理流"升级为高自由度"科研工作台"

**三大核心能力：**

### L. 项目完成后的真实数据验收（新增，2026-04-08）
**目标：** 不以“测试脚本通过”为唯一完成标准，必须用真实数据问真实问题，验证系统稳定性与可用性。

**固定验收数据路径：**
- `/Volumes/hmq/智能科研工作助手/scw agent mvp/data/zhejiang_carbon.csv`
- `/Volumes/hmq/智能科研工作助手/scw agent mvp/data/浙江省各城市粮食，碳排放及农业经济发展情况.xlsx`

**验收原则：**
- 必须同时覆盖 CSV 与 Excel 两种数据输入
- 必须覆盖“直接建任务”“上传后建任务”“中断后继续”三类路径
- 必须覆盖描述统计、回归分析、变量关系解释、结果写作至少四类问题
- 验收以“是否稳定给出可读结果”为先，不以“是否输出了代码”作为成功标准
- 若出现报错，必须记录触发问题、出错节点、修复方式，并重新回归整个问题集
- 任一失败样例必须落盘到 `bad case/` 目录，不允许只在对话或临时笔记中记录

**建议验收问题集（至少全部跑完一次）：**
1. `请基于浙江碳排放数据，识别可能的因变量、自变量和控制变量，并给出推荐映射。`
2. `请对农业产值与碳排放之间的关系做描述性统计，并总结主要特征。`
3. `请以碳排放为因变量、农业产值为核心自变量、农药使用量为控制变量，生成并执行一个基础回归分析。`
4. `如果这是面板数据，请尝试固定效应模型，并解释核心系数方向与显著性。`
5. `请比较粮食产量、农业经济发展水平与碳排放之间的关系，给出哪一个变量更值得重点讨论。`
6. `请输出一段可以直接放入论文“结果分析”部分的中文草稿，概括关键发现。`
7. `请基于上传的 Excel 数据，自动识别字段含义，并说明哪些字段适合作为被解释变量、解释变量和控制变量。`
8. `请检查这份数据是否更适合做 OLS、DID 还是面板固定效应，并解释原因。`

**最终通过标准：**
- 上述问题集至少成功完成 6/8，且两份数据文件都至少各成功跑通 3 个问题
- 成功案例中，前端默认主视图展示的是“结果/结论/映射/文献/摘要”，不是大段代码
- 全流程测试过程中，不允许出现高频阻塞性报错（如页面白屏、无限更新、上传失败后无法恢复、详情页持续报错）
- 若有失败问题，必须在 `bad case/` 目录中新增对应记录文件，并在 `PROJECT_STATUS.md` 中追加失败概览与后续修复计划，不得直接标记项目完成

**当前进度（2026-04-08 晚间）：**
- 已完成完整 8 题真实数据回归，CSV 与 Excel 均已覆盖
- 当前累计：8/8 通过，0 个 bad case
- 当前仍建议继续扩展问题集，特别是更复杂的论文文件参与场景与 paper-qa 场景

**`bad case/` 记录要求：**
- 一个失败样例对应一个独立记录文件，文件名建议包含日期、数据文件、问题编号、失败节点
- 每条记录至少包含：输入数据文件、用户问题、复现步骤、预期结果、实际结果、报错信息、根因分析、解决方案、修复后回归结果
- 若问题暂未修复，必须明确当前阻塞点和下一步处理计划
1. **代码驱动的自定义模型** — Monaco Editor + Python/R AST 解析 + 动态表单生成
2. **全链路中断与修改干预** — Variable Mapper 可视化映射 + 代码沙箱二次编辑 + 断点续跑
3. **DAG 执行引擎** — 节点级状态持久化 + 从修改节点重新执行

**新增 API 草案：**
| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/models/parse` | POST | 静态解析自定义代码提取变量 |
| `/api/models/custom` | POST | 保存自定义模型资产 |
| `/api/tasks/{id}/nodes/{node}/update` | PUT | 修改指定节点的数据/参数 |
| `/api/tasks/{id}/resume` | POST | 从修改处继续执行 |

**实施风险：**
- 沙箱冷启动延迟 → 建议维护热备用沙箱池（Warm Pool）
- AST 解析容错率低 → 建议强制用户按模板格式书写（如 `def custom_model(data, params):`）

---

## 环境变量说明

```bash
# Redis（TaskRepository + CheckpointRepository 后端）
TASK_REPOSITORY_BACKEND=file        # "file" 或 "redis"
TASK_REPOSITORY_BACKEND=redis

# LangGraph 编排 + Checkpointer
ORCHESTRATION_BACKEND=custom        # "custom"（默认）或 "langgraph"
ORCHESTRATION_BACKEND=langgraph
LANGGRAPH_CHECKPOINT_BACKEND=memory # "memory"（默认）或 "redis"

# Redis 连接
REDIS_URL=redis://127.0.0.1:6379/0

# Zotero（自动从 ~/.research_assistant/zotero_config.json 读取，也可设 env var）
ZOTERO_API_KEY=你的APIKey
```

---

## 启动命令

```bash
cd /Volumes/hmq/智能科研工作助手
source .venv/bin/activate
uvicorn backend.main:app --reload

# 运行测试
pytest tests/ -v

# 上传文件
curl -X POST http://127.0.0.1:8000/upload \
  -F "files=@/path/to/data.csv" \
  -F "files=@/path/to/paper.pdf"

# 用返回的路径创建任务
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type":"analysis","user_query":"碳排放 农业 面板数据","data_files":["/abs/path/to/data.csv"],"paper_files":[]}'
```

---

## Zotero API Key 配置

```bash
# 路径
~/.research_assistant/zotero_config.json

# 内容
{
  "api_key": "sWBsPWaQWj9wP1s7BZFAsHN6",
  "note": "Zotero API Key for 智能科研工作助手"
}
```

---

## 文件索引

### 后端（backend/）

#### 入口
| 文件 | 作用 |
|------|------|
| `backend/main.py` | FastAPI 应用入口 |
| `backend/core/config.py` | 所有环境变量配置 |

#### API 层
| 文件 | 作用 |
|------|------|
| `backend/api/routes.py` | API 路由（/tasks, /upload, /settings 等） |
| `backend/api/schemas.py` | Pydantic 请求/响应模型 |

#### Agent 工具层
| 文件 | 作用 |
|------|------|
| `backend/agents/tools/question_parser.py` | 问题解析（VAR_ALIASES、多 Provider LLM） |
| `backend/agents/tools/model_recommender.py` | 模型推荐（MODEL_RULES、infer_data_structure） |
| `backend/agents/tools/literature_search.py` | 文献检索（Zotero/OpenAlex/paper-qa/fallback） |
| `backend/agents/tools/paperqa_wrapper.py` | paper-qa 轻量 wrapper（子进程调用） |

#### Agent 数据模型
| 文件 | 作用 |
|------|------|
| `backend/agents/models/state.py` | AgentState 图状态定义 |
| `backend/agents/models/research_brief.py` | Research Brief 数据模型 |
| `backend/agents/models/code_generation.py` | 代码生成数据模型（EvidencePackage, GeneratedCode, ExecutionResult） |

#### 编排层
| 文件 | 作用 |
|------|------|
| `backend/agents/orchestrator/main_graph.py` | 主图编排 |
| `backend/agents/orchestrator/langgraph_runtime.py` | LangGraph 运行时 |
| `backend/agents/runtime.py` | AgentRuntime 基类 |

#### Node 子图（6 个）
| 文件 | 作用 |
|------|------|
| `backend/agents/orchestrator/subgraphs/data_mapping_node.py` | 数据映射节点 |
| `backend/agents/orchestrator/subgraphs/literature_node.py` | 文献综述节点 |
| `backend/agents/orchestrator/subgraphs/novelty_node.py` | 创新判断节点 |
| `backend/agents/orchestrator/subgraphs/analysis_node.py` | 分析节点 |
| `backend/agents/orchestrator/subgraphs/brief_builder_node.py` | 简报构建节点 |
| `backend/agents/orchestrator/subgraphs/writing_node.py` | 写作节点 |
| `backend/agents/orchestrator/subgraphs/text_to_code_bridge.py` | Text-to-Code Bridge 节点 |

#### 核心（core/）
| 文件 | 作用 |
|------|------|
| `backend/core/task_store.py` | TaskStore 编排逻辑 |
| `backend/core/task_repository.py` | 任务持久化（file/redis 后端） |
| `backend/core/task_history.py` | 任务历史记录 |
| `backend/core/task_mutations.py` | 任务修改逻辑 |
| `backend/core/checkpoint_repository.py` | Checkpoint 持久化 |
| `backend/core/sandbox.py` | 代码安全检查 + subprocess 沙箱执行 |
| `backend/core/error_handling.py` | 错误分类 + 重试装饰器 |
| `backend/core/file_validation.py` | 文件类型校验 |
| `backend/core/redis_checkpointer.py` | Redis String Checkpointer |
| `backend/core/logging/structured_logger.py` | 结构化日志（ContextVar 协程安全） |
| `backend/core/logging/events.py` | 20+ 事件常量 |

### 前端（frontend/）

#### 页面（src/app/）
| 文件 | 作用 |
|------|------|
| `frontend/src/app/page.tsx` | 首页 Landing Page |
| `frontend/src/app/layout.tsx` | 根布局 |
| `frontend/src/app/workspace/page.tsx` | 工作台（任务创建+历史） |
| `frontend/src/app/workspace/[taskId]/page.tsx` | 任务详情页 |
| `frontend/src/app/settings/page.tsx` | 设置页（API Key + 科研偏好） |

#### 组件（components/）
| 文件 | 作用 |
|------|------|
| `frontend/components/task-console.tsx` | 任务创建表单 |
| `frontend/components/task-list.tsx` | 历史任务列表 |
| `frontend/components/interrupt-manager.tsx` | 中断管理 + 继续/终止 |
| `frontend/components/task-progress.tsx` | 任务进度 Stepper（新建） |
| `frontend/components/task-detail.tsx` | 任务详情结构化渲染（新建） |
| `frontend/components/file-uploader.tsx` | 拖拽文件上传组件（新建） |
| `frontend/components/shared.module.css` | 共享样式（Navy 深色主题） |

#### 状态管理（lib/stores/）
| 文件 | 作用 |
|------|------|
| `frontend/lib/stores/task-store.ts` | 任务全局状态 + 轮询 |
| `frontend/lib/stores/settings-store.ts` | 设置 + API Key 状态 |
| `frontend/lib/stores/model-store.ts` | 变量映射状态 |
| `frontend/lib/api.ts` | API 客户端（fetchTasks/fetchTask 等） |

### 测试（tests/）
| 文件 | 作用 |
|------|------|
| `tests/test_e2e_interrupt_flow.py` | 端到端中断流测试 |
| `tests/test_api_unittest.py` | API 层测试 |
| `tests/test_orchestrator.py` | 编排器中断序列测试 |
| `tests/test_unittest_smoke.py` | 持久化和集成测试 |
| `tests/test_literature_search_unittest.py` | 文献检索测试 |
| `tests/test_runtime_unittest.py` | 运行时测试 |
| `tests/test_text_to_code_bridge.py` | Text-to-Code Bridge 测试 |
| `tests/test_benchmark_*.py` | Benchmark 评测测试（4 个） |

### Benchmark（benchmark/）
| 文件 | 作用 |
|------|------|
| `benchmark/evaluator.py` | 评测引擎 |
| `benchmark/run_evaluation.py` | CLI 评测报告生成器 |
| `benchmark/mock_client.py` | MockAgentClient（中文 bigram 分词） |
| `benchmark/retrieval/cases.json` | 15 个检索测试用例 |
| `benchmark/text_to_code/cases.json` | 18 个代码生成测试用例 |
| `benchmark/citation/cases.json` | 15 个引用溯源测试用例 |
| `benchmark/e2e/cases.json` | 12 个端到端测试用例 |
| `benchmark/fixtures/retrieval/chunks.json` | 20 个真实文本 chunks |
| `benchmark/reporting/report_generator.py` | Markdown + HTML 报告生成 |

### 设计文档（思路统筹/）
| 文件 | 作用 |
|------|------|
| `思路统筹/Phase0-最小可运行骨架-实施计划.md` | 项目启动计划 |
| `思路统筹/Phase1-集成与中断-设计文档.md` | 中断点系统设计 |
| `思路统筹/Phase1-Analysis-Node-设计文档.md` | Analysis Node 设计 |
| `思路统筹/Phase1-Literature-Node-设计文档.md` | Literature Node 设计 |
| `思路统筹/Phase1-Novelty-Node-设计文档.md` | Novelty Node 设计 |
| `思路统筹/Phase1-Research-Brief-Schema-设计文档.md` | Research Brief Schema |
| `思路统筹/Phase1-Text-to-Code-Bridge-设计文档.md` | Text-to-Code Bridge 设计 |
| `思路统筹/Phase1-Writing-Node-设计文档.md` | Writing Node 设计 |
| `思路统筹/Phase2-安全与稳定性-设计文档.md` | 安全与稳定性设计 |
| `思路统筹/Phase3-评测体系-设计文档.md` | 评测体系设计 |
| `思路统筹/后端优化.md` | 自定义模型 + 全链路编辑架构 |
| `思路统筹/架构图-综合版.md` | 系统架构图（Mermaid） |
| `思路统筹/时序图-综合版.md` | 时序图（Mermaid） |
| `思路统筹/科研多Agent系统MVP实施计划.md` | MVP 实施总计划 |
| `思路统筹/设计文档索引.md` | 文档索引 |

### 其他
| 文件 | 作用 |
|------|------|
| `CLAUDE.md` | 项目级 Claude Code 指令 |
| `PROJECT_STATUS.md` | 本项目状态文档 |
| `README.md` | 项目说明 |
| `requirements.txt` | Python 依赖 |
| `TODOS.md` | 待办事项 |
| `改进建议_2026-04-07.md` | 改进建议记录 |
| `paused-work/frontend-workbench-paused/` | 暂停的前端工作副本 |
| `scw agent mvp/` | SCW Agent MVP 工作目录 |
