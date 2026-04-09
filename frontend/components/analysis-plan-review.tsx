"use client";

import { useEffect, useMemo, useState } from "react";
import sharedStyles from "./shared.module.css";
import styles from "./analysis-plan-review.module.css";

interface AnalysisInterruptData {
  message?: string;
  bridge_status?: string;
  recommended_models?: string[];
  execution_plan?: string[];
  adaptation_explanation?: string;
  execution_result?: Record<string, unknown> | null;
  result_summary?: {
    summary_text?: string;
    method?: string;
    n_obs?: number;
    r_squared?: number;
    r_squared_within?: number;
    did_interaction_coef?: number | null;
    coefficients?: Record<string, { coef?: number; pvalue?: number }>;
  } | null;
  code_script?: string;
}

interface AnalysisPlanReviewProps {
  interruptData: Record<string, unknown>;
  loading?: boolean;
  onApprove: () => Promise<void>;
  onSubmitModified: (payload: Record<string, unknown>) => Promise<void>;
  onReject: () => Promise<void>;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function formatBridgeStatus(status?: string): string {
  if (!status) return "待确认";
  if (status === "success") return "代码已执行成功";
  if (status === "execution_failed") return "代码执行失败";
  if (status === "check_failed") return "安全检查未通过";
  return status;
}

export function AnalysisPlanReview({
  interruptData,
  loading = false,
  onApprove,
  onSubmitModified,
  onReject,
}: AnalysisPlanReviewProps) {
  const data = interruptData as AnalysisInterruptData;
  const [modelsText, setModelsText] = useState(asStringArray(data.recommended_models).join(", "));
  const [planText, setPlanText] = useState(asStringArray(data.execution_plan).join("\n"));
  const [adaptationExplanation, setAdaptationExplanation] = useState(data.adaptation_explanation ?? "");
  const coefficientRows = data.result_summary?.coefficients
    ? Object.entries(data.result_summary.coefficients).filter(([name]) => name !== "const").slice(0, 6)
    : [];

  useEffect(() => {
    setModelsText(asStringArray(data.recommended_models).join(", "));
    setPlanText(asStringArray(data.execution_plan).join("\n"));
    setAdaptationExplanation(data.adaptation_explanation ?? "");
  }, [data.adaptation_explanation, data.execution_plan, data.recommended_models]);

  const modifiedPayload = useMemo(() => ({
    recommended_models: modelsText.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    execution_plan: planText.split("\n").map((item) => item.trim()).filter(Boolean),
    adaptation_explanation: adaptationExplanation.trim(),
  }), [adaptationExplanation, modelsText, planText]);

  const isChanged = useMemo(() => JSON.stringify(modifiedPayload) !== JSON.stringify({
    recommended_models: asStringArray(data.recommended_models),
    execution_plan: asStringArray(data.execution_plan),
    adaptation_explanation: data.adaptation_explanation ?? "",
  }), [data.adaptation_explanation, data.execution_plan, data.recommended_models, modifiedPayload]);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>代码方案审核</h3>
          <p className={styles.description}>
            {data.message ?? "请确认分析方法、执行步骤和代码方案，再继续生成研究简报。"}
          </p>
        </div>
        <span className={styles.badge}>{formatBridgeStatus(data.bridge_status)}</span>
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>推荐模型</p>
          <p className={styles.summaryValue}>{asStringArray(data.recommended_models).join(" / ") || "暂无"}</p>
        </div>
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>执行状态</p>
          <p className={styles.summaryValue}>{formatBridgeStatus(data.bridge_status)}</p>
        </div>
      </div>

      {data.result_summary?.summary_text && (
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>结果摘要</p>
          <p className={styles.summaryValue}>{data.result_summary.summary_text}</p>
        </div>
      )}

      {(typeof data.result_summary?.n_obs === "number"
        || typeof data.result_summary?.r_squared === "number"
        || typeof data.result_summary?.r_squared_within === "number"
        || typeof data.result_summary?.did_interaction_coef === "number") && (
        <div className={styles.summaryGrid}>
          {typeof data.result_summary?.n_obs === "number" && (
            <div className={styles.summaryCard}>
              <p className={styles.summaryLabel}>样本量</p>
              <p className={styles.summaryValue}>{data.result_summary.n_obs}</p>
            </div>
          )}
          {typeof data.result_summary?.r_squared === "number" && (
            <div className={styles.summaryCard}>
              <p className={styles.summaryLabel}>R²</p>
              <p className={styles.summaryValue}>{data.result_summary.r_squared.toFixed(4)}</p>
            </div>
          )}
          {typeof data.result_summary?.r_squared_within === "number" && (
            <div className={styles.summaryCard}>
              <p className={styles.summaryLabel}>组内 R²</p>
              <p className={styles.summaryValue}>{data.result_summary.r_squared_within.toFixed(4)}</p>
            </div>
          )}
          {typeof data.result_summary?.did_interaction_coef === "number" && (
            <div className={styles.summaryCard}>
              <p className={styles.summaryLabel}>DID 交互项系数</p>
              <p className={styles.summaryValue}>{data.result_summary.did_interaction_coef.toFixed(4)}</p>
            </div>
          )}
        </div>
      )}

      {!!coefficientRows.length && (
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>核心系数</p>
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

      <div className={styles.field}>
        <label htmlFor="recommended-models" className={sharedStyles.label}>推荐模型</label>
        <input
          id="recommended-models"
          className={sharedStyles.input}
          value={modelsText}
          onChange={(event) => setModelsText(event.target.value)}
          placeholder="多个模型用逗号分隔"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="adaptation-explanation" className={sharedStyles.label}>方案说明</label>
        <textarea
          id="adaptation-explanation"
          className={sharedStyles.textarea}
          rows={4}
          value={adaptationExplanation}
          onChange={(event) => setAdaptationExplanation(event.target.value)}
          placeholder="补充说明为什么采用这套模型和代码方案"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="execution-plan" className={sharedStyles.label}>执行步骤</label>
        <textarea
          id="execution-plan"
          className={sharedStyles.textarea}
          rows={6}
          value={planText}
          onChange={(event) => setPlanText(event.target.value)}
          placeholder="每行一个步骤"
        />
      </div>

      {data.execution_result && (
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>执行回执</p>
          <pre className={styles.resultBlock}>{JSON.stringify(data.execution_result, null, 2)}</pre>
        </div>
      )}

      {data.code_script && (
        <details className={styles.details}>
          <summary className={styles.detailsSummary}>查看生成代码</summary>
          <pre className={styles.codeBlock}>{data.code_script}</pre>
        </details>
      )}

      <div className={styles.actions}>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onReject} disabled={loading}>终止任务</button>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onApprove} disabled={loading}>直接采用当前方案</button>
        <button type="button" className={sharedStyles.btnPrimary} onClick={() => onSubmitModified(modifiedPayload)} disabled={loading || !isChanged}>保存调整并继续</button>
      </div>
    </section>
  );
}
