"use client";

import { useState } from "react";
import type { TaskPayload } from "../lib/api";
import styles from "./task-detail.module.css";

interface DataMappingResult {
  type: "data_mapping";
  dependent_var?: string | null;
  independent_vars?: string[];
  control_vars?: string[];
  entity_column?: string | null;
  time_column?: string | null;
  method_preference?: string | null;
  columns?: string[];
  preview?: Array<Record<string, unknown>>;
}

interface LiteratureReviewResult {
  type: "literature_review";
  papers: {
    title: string;
    authors?: string[];
    year?: number;
    journal?: string;
    citations?: number;
    abstract?: string;
    doi?: string;
  }[];
}

interface CodeGenerationResult {
  type: "code_generation";
  recommended_models?: string[];
  execution_plan?: string[];
  adaptation_explanation?: string;
  bridge_status?: string;
  execution_result?: Record<string, unknown> | null;
  result_summary?: Record<string, unknown> | null;
  code_script?: string;
}

interface StructuredAnalysisResult {
  method?: string;
  n_obs?: number;
  r_squared?: number;
  adj_r_squared?: number;
  r_squared_within?: number;
  did_interaction_coef?: number | null;
  coefficients?: Record<string, { coef?: number; pvalue?: number }>;
}

interface ResearchBriefResult {
  type: "research_brief";
  title?: string;
  research_goal?: string;
  method_decision?: Record<string, unknown>;
}

interface WritingResult {
  type: "writing";
  abstract?: string;
  methods?: string;
  results?: string;
  outline?: string[];
}

type ParsedResult =
  | DataMappingResult
  | LiteratureReviewResult
  | CodeGenerationResult
  | ResearchBriefResult
  | WritingResult
  | { type: "unknown"; data: unknown };

function parseResult(result: Record<string, unknown> | null): ParsedResult {
  if (!result) return { type: "unknown", data: null };

  if (result.final_output && typeof result.final_output === "object") {
    const finalOutput = result.final_output as Record<string, unknown>;
    if (finalOutput.draft && typeof finalOutput.draft === "object") {
      return { type: "writing", ...(finalOutput.draft as Record<string, unknown>) } as WritingResult;
    }
  }

  if (result.analysis_result && typeof result.analysis_result === "object") {
    return { type: "code_generation", ...(result.analysis_result as Record<string, unknown>) } as CodeGenerationResult;
  }

  if (result.literature_result && typeof result.literature_result === "object") {
    const literature = result.literature_result as Record<string, unknown>;
    return {
      type: "literature_review",
      papers: Array.isArray(literature.references) ? literature.references as LiteratureReviewResult["papers"] : [],
    };
  }

  if (result.data_mapping_result && typeof result.data_mapping_result === "object") {
    return { type: "data_mapping", ...(result.data_mapping_result as Record<string, unknown>) } as DataMappingResult;
  }

  if (result.brief_result && typeof result.brief_result === "object") {
    return { type: "research_brief", ...(result.brief_result as Record<string, unknown>) } as ResearchBriefResult;
  }

  return { type: "unknown", data: result };
}

function DataMappingView({ result }: { result: DataMappingResult }) {
  const metrics = [
    { label: "因变量", value: result.dependent_var || "未确认" },
    { label: "自变量", value: result.independent_vars?.join(", ") || "未确认" },
    { label: "控制变量", value: result.control_vars?.join(", ") || "无" },
    { label: "地区列", value: result.entity_column || "未确认" },
    { label: "时间列", value: result.time_column || "未确认" },
    { label: "方法偏好", value: result.method_preference || "无偏好" },
  ];

  return (
    <div className={styles.resultStack}>
      <div className={styles.metricGrid}>
        {metrics.map((item) => (
          <div key={item.label} className={styles.metricCard}>
            <p className={styles.metricLabel}>{item.label}</p>
            <p className={styles.metricValue}>{item.value}</p>
          </div>
        ))}
      </div>
      {!!result.columns?.length && (
        <div className={styles.previewScroller}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                {result.columns.map((column) => <th key={column}>{column}</th>)}
              </tr>
            </thead>
            <tbody>
              {(result.preview || []).map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {result.columns?.map((column) => (
                    <td key={`${rowIndex}-${column}`}>{String(row[column] ?? "-")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LiteratureReviewView({ papers }: { papers: LiteratureReviewResult["papers"] }) {
  if (!papers.length) return <div className={styles.empty}>暂无文献数据</div>;

  return (
    <div className={styles.litGrid}>
      {papers.map((paper, index) => (
        <div key={index} className={styles.litCard}>
          <h3 className={styles.litTitle}>{paper.title}</h3>
          <div className={styles.litMeta}>
            {paper.year && <span className={styles.litBadge}>{paper.year}</span>}
            {paper.journal && <span className={styles.litBadge}>{paper.journal}</span>}
            {paper.citations !== undefined && (
              <span className={styles["litBadge--highlight"]}>被引 {paper.citations}</span>
            )}
          </div>
          {paper.abstract && <p className={styles.litAbstract}>{paper.abstract}</p>}
          {paper.authors?.length ? <p className={styles.authorLine}>{paper.authors.join(", ")}</p> : null}
        </div>
      ))}
    </div>
  );
}

function extractStructuredAnalysis(executionResult: Record<string, unknown> | null | undefined): StructuredAnalysisResult | null {
  if (!executionResult) return null;

  const stdout = typeof executionResult.stdout === "string" ? executionResult.stdout : "";
  const match = stdout.match(/\{\s*"method"[\s\S]*\}\s*$/);
  if (match) {
    try {
      return JSON.parse(match[0]) as StructuredAnalysisResult;
    } catch {
      // fall through
    }
  }

  if ("method" in executionResult || "coefficients" in executionResult) {
    return executionResult as unknown as StructuredAnalysisResult;
  }

  return null;
}

function summarizeAnalysis(result: CodeGenerationResult, structured: StructuredAnalysisResult | null): string | null {
  if (result.result_summary && typeof result.result_summary.summary_text === "string") {
    return result.result_summary.summary_text;
  }
  if (!structured) return result.adaptation_explanation || null;

  const coefficients = structured.coefficients || {};
  const keyEntry = Object.entries(coefficients).find(([name]) => name !== "const");
  const [keyName, keyValue] = keyEntry || [];
  const coef = keyValue?.coef;
  const pvalue = keyValue?.pvalue;
  const direction = typeof coef === "number" ? (coef > 0 ? "正向" : coef < 0 ? "负向" : "接近于零") : null;
  const significance = typeof pvalue === "number"
    ? (pvalue < 0.01 ? "在 1% 水平显著" : pvalue < 0.05 ? "在 5% 水平显著" : pvalue < 0.1 ? "在 10% 水平边际显著" : "统计上不显著")
    : null;

  const summaryParts = [
    structured.method ? `当前模型为 ${structured.method}` : null,
    typeof structured.n_obs === "number" ? `样本量 ${structured.n_obs}` : null,
    typeof structured.r_squared === "number"
      ? `R²=${structured.r_squared.toFixed(4)}`
      : typeof structured.r_squared_within === "number"
        ? `组内 R²=${structured.r_squared_within.toFixed(4)}`
        : null,
  ].filter(Boolean);

  if (keyName && direction) {
    summaryParts.push(`${keyName} 对结果变量呈${direction}影响`);
  }
  if (significance) {
    summaryParts.push(significance);
  }

  return summaryParts.length > 0 ? `${summaryParts.join("，")}。` : (result.adaptation_explanation || null);
}

function CodeGenerationView({ result }: { result: CodeGenerationResult }) {
  const structured = (result.result_summary as StructuredAnalysisResult | null) ?? extractStructuredAnalysis(result.execution_result);
  const summary = summarizeAnalysis(result, structured);
  const coefficientRows = structured?.coefficients
    ? Object.entries(structured.coefficients).filter(([name]) => name !== "const").slice(0, 6)
    : [];

  return (
    <div className={styles.resultStack}>
      <div className={styles.metricGrid}>
        <div className={styles.metricCard}>
          <p className={styles.metricLabel}>桥接状态</p>
          <p className={styles.metricValue}>{result.bridge_status || "未知"}</p>
        </div>
        <div className={styles.metricCard}>
          <p className={styles.metricLabel}>推荐模型</p>
          <p className={styles.metricValue}>{result.recommended_models?.join(", ") || "暂无"}</p>
        </div>
      </div>
      {summary && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>结果摘要</p>
          <p className={styles.summaryText}>{summary}</p>
        </div>
      )}
      {structured && (
        <div className={styles.metricGrid}>
          {typeof structured.n_obs === "number" ? (
            <div className={styles.metricCard}>
              <p className={styles.metricLabel}>样本量</p>
              <p className={styles.metricValue}>{structured.n_obs}</p>
            </div>
          ) : null}
          {typeof structured.r_squared === "number" ? (
            <div className={styles.metricCard}>
              <p className={styles.metricLabel}>R²</p>
              <p className={styles.metricValue}>{structured.r_squared.toFixed(4)}</p>
            </div>
          ) : null}
          {typeof structured.r_squared_within === "number" ? (
            <div className={styles.metricCard}>
              <p className={styles.metricLabel}>组内 R²</p>
              <p className={styles.metricValue}>{structured.r_squared_within.toFixed(4)}</p>
            </div>
          ) : null}
          {typeof structured.did_interaction_coef === "number" ? (
            <div className={styles.metricCard}>
              <p className={styles.metricLabel}>DID 交互项系数</p>
              <p className={styles.metricValue}>{structured.did_interaction_coef.toFixed(4)}</p>
            </div>
          ) : null}
        </div>
      )}
      {!!coefficientRows.length && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>核心系数</p>
          <div className={styles.coefficientList}>
            {coefficientRows.map(([name, value]) => (
              <div key={name} className={styles.coefficientItem}>
                <span className={styles.coefficientName}>{name}</span>
                <span className={styles.coefficientMeta}>
                  coef={typeof value.coef === "number" ? value.coef.toFixed(4) : "-"}
                  {" · "}
                  p={typeof value.pvalue === "number" ? value.pvalue.toFixed(4) : "-"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {!!result.execution_plan?.length && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>执行步骤</p>
          <ol className={styles.list}>
            {result.execution_plan.map((item, index) => <li key={index}>{item}</li>)}
          </ol>
        </div>
      )}
      {result.execution_result && (
        <details className={styles.codeBlock}>
          <summary className={styles.codeToolbar}>
            <span className={styles.codeLang}>执行回执</span>
          </summary>
          <pre className={styles.codeContent}>{JSON.stringify(result.execution_result, null, 2)}</pre>
        </details>
      )}
      {result.code_script && (
        <details className={styles.codeBlock}>
          <summary className={styles.codeToolbar}>
            <span className={styles.codeLang}>python</span>
            <span className={styles.codeHint}>代码作为附属信息折叠展示</span>
          </summary>
          <pre className={styles.codeContent}>{result.code_script}</pre>
        </details>
      )}
    </div>
  );
}

function BriefView({ result }: { result: ResearchBriefResult }) {
  const models = Array.isArray(result.method_decision?.recommended_models)
    ? result.method_decision?.recommended_models as string[]
    : [];

  return (
    <div className={styles.resultStack}>
      <div className={styles.metricGrid}>
        <div className={styles.metricCard}>
          <p className={styles.metricLabel}>研究目标</p>
          <p className={styles.metricValue}>{result.research_goal || result.title || "未提供"}</p>
        </div>
        <div className={styles.metricCard}>
          <p className={styles.metricLabel}>候选模型</p>
          <p className={styles.metricValue}>{models.join(", ") || "未提供"}</p>
        </div>
      </div>
      <details className={styles.codeBlock}>
        <summary className={styles.codeToolbar}>
          <span className={styles.codeLang}>研究简报 JSON</span>
        </summary>
        <pre className={styles.codeContent}>{JSON.stringify(result, null, 2)}</pre>
      </details>
    </div>
  );
}

function WritingView({ result }: { result: WritingResult }) {
  return (
    <div className={styles.resultStack}>
      {result.abstract && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>摘要草稿</p>
          <p className={styles.summaryText}>{result.abstract}</p>
        </div>
      )}
      {result.methods && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>方法说明</p>
          <p className={styles.summaryText}>{result.methods}</p>
        </div>
      )}
      {result.results && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>结果摘要</p>
          <p className={styles.summaryText}>{result.results}</p>
        </div>
      )}
      {!!result.outline?.length && (
        <div className={styles.summaryCard}>
          <p className={styles.metricLabel}>论文提纲</p>
          <ol className={styles.list}>
            {result.outline.map((item, index) => <li key={index}>{item}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}

function UnknownView({ data }: { data: unknown }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <div className={styles.empty}>未知结果类型，使用原始 JSON 展示</div>
      <button className={styles.jsonToggle} onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
        {expanded ? "收起" : "展开"} 原始 JSON
      </button>
      {expanded && (
        <div className={styles.jsonContent}>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </>
  );
}

function InterruptDataView({ task }: { task: TaskPayload }) {
  const data = task.interrupt_data as Record<string, unknown>;

  if (!data) {
    return <div className={styles.empty}>当前没有中断数据</div>;
  }

  if (task.interrupt_reason === "data_mapping_required") {
    return <DataMappingView result={{ type: "data_mapping", ...((data.recommended_mapping as Record<string, unknown>) || {}) } as DataMappingResult} />;
  }

  if (task.interrupt_reason === "literature_review_required") {
    const literature = (data.literature_result as Record<string, unknown>) || {};
    return (
      <div className={styles.resultStack}>
        <LiteratureReviewView papers={Array.isArray(literature.references) ? literature.references as LiteratureReviewResult["papers"] : []} />
        {"quality_warning" in literature && literature.quality_warning ? (
          <div className={styles.summaryCard}>
            <p className={styles.metricLabel}>质量提醒</p>
            <p className={styles.summaryText}>{String(literature.quality_warning)}</p>
          </div>
        ) : null}
      </div>
    );
  }

  if (task.interrupt_reason === "novelty_result_ready") {
    const novelty = data;
    const transfer = Array.isArray(novelty.transfer_assessments) ? novelty.transfer_assessments[0] as Record<string, unknown> : null;
    return (
      <div className={styles.resultStack}>
        <div className={styles.metricGrid}>
          <div className={styles.metricCard}>
            <p className={styles.metricLabel}>推荐方法</p>
            <p className={styles.metricValue}>{String(transfer?.method_name || "未提供")}</p>
          </div>
          <div className={styles.metricCard}>
            <p className={styles.metricLabel}>迁移可行性</p>
            <p className={styles.metricValue}>{String(transfer?.transfer_feasibility || "未提供")}</p>
          </div>
        </div>
        {"recommended_direction" in novelty ? (
          <div className={styles.summaryCard}>
            <p className={styles.metricLabel}>推荐方向</p>
            <p className={styles.summaryText}>{String(((novelty.recommended_direction as Record<string, unknown>) || {}).summary || "未提供")}</p>
          </div>
        ) : null}
        {Array.isArray(novelty.differentiation_points) ? (
          <div className={styles.summaryCard}>
            <p className={styles.metricLabel}>差异化要点</p>
            <ol className={styles.list}>
              {(novelty.differentiation_points as string[]).map((item, index) => <li key={index}>{item}</li>)}
            </ol>
          </div>
        ) : null}
      </div>
    );
  }

  if (task.interrupt_reason === "code_plan_ready") {
    return <CodeGenerationView result={{ type: "code_generation", ...(data as Record<string, unknown>) } as CodeGenerationResult} />;
  }

  if (task.interrupt_reason === "brief_ready_for_review") {
    return <BriefView result={{ type: "research_brief", ...(data as Record<string, unknown>) } as ResearchBriefResult} />;
  }

  return (
    <div className={styles.jsonContent}>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

interface TaskDetailProps {
  task: TaskPayload;
}

export function TaskDetail({ task }: TaskDetailProps) {
  const [activeTab, setActiveTab] = useState("result");
  const parsed = parseResult(task.result ?? null);
  const availableTabs = [{ id: "result", label: "结果" }];

  if (task.interrupt_data) {
    availableTabs.push({ id: "interrupt", label: "中断数据" });
  }

  return (
    <div className={styles.container}>
      <div className={styles.tabBar} role="tablist">
        {availableTabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`${styles.tab} ${activeTab === tab.id ? styles["tab--active"] : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "result" && (
        <div className={styles.section} role="tabpanel">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              {parsed.type === "data_mapping" ? "数据映射结果"
                : parsed.type === "literature_review" ? "文献综述结果"
                : parsed.type === "code_generation" ? "分析方案"
                : parsed.type === "research_brief" ? "研究简报"
                : parsed.type === "writing" ? "写作草稿"
                : "任务结果"}
            </h2>
          </div>
          <div className={styles.sectionBody}>
            {parsed.type === "data_mapping" && <DataMappingView result={parsed} />}
            {parsed.type === "literature_review" && <LiteratureReviewView papers={parsed.papers} />}
            {parsed.type === "code_generation" && <CodeGenerationView result={parsed} />}
            {parsed.type === "research_brief" && <BriefView result={parsed} />}
            {parsed.type === "writing" && <WritingView result={parsed} />}
            {parsed.type === "unknown" && <UnknownView data={parsed.data} />}
          </div>
        </div>
      )}

      {activeTab === "interrupt" && task.interrupt_data && (
        <div className={styles.section} role="tabpanel">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>中断数据</h2>
          </div>
          <div className={styles.sectionBody}>
            <InterruptDataView task={task} />
          </div>
        </div>
      )}
    </div>
  );
}
