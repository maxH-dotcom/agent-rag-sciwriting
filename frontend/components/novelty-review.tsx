"use client";

import { useEffect, useMemo, useState } from "react";
import sharedStyles from "./shared.module.css";
import styles from "./novelty-review.module.css";

interface TransferAssessment {
  method_name?: string;
  transfer_feasibility?: string;
  transfer_feasibility_reason?: string;
  required_adaptations?: string[];
}

interface NoveltyInterruptData {
  transfer_assessments?: TransferAssessment[];
  recommended_direction?: {
    summary?: string;
    why?: string;
  };
  differentiation_points?: string[];
}

interface NoveltyReviewProps {
  interruptData: Record<string, unknown>;
  loading?: boolean;
  onApprove: () => Promise<void>;
  onSubmitModified: (payload: Record<string, unknown>) => Promise<void>;
  onReject: () => Promise<void>;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function NoveltyReview({
  interruptData,
  loading = false,
  onApprove,
  onSubmitModified,
  onReject,
}: NoveltyReviewProps) {
  const data = interruptData as NoveltyInterruptData;
  const firstAssessment = (Array.isArray(data.transfer_assessments) ? data.transfer_assessments[0] : undefined) ?? {};

  const [summary, setSummary] = useState(data.recommended_direction?.summary ?? "");
  const [why, setWhy] = useState(data.recommended_direction?.why ?? "");
  const [methodName, setMethodName] = useState(firstAssessment.method_name ?? "");
  const [feasibility, setFeasibility] = useState(firstAssessment.transfer_feasibility ?? "");
  const [adaptationsText, setAdaptationsText] = useState(
    asStringArray(firstAssessment.required_adaptations).join("\n"),
  );
  const [differentiationText, setDifferentiationText] = useState(
    asStringArray(data.differentiation_points).join("\n"),
  );

  useEffect(() => {
    setSummary(data.recommended_direction?.summary ?? "");
    setWhy(data.recommended_direction?.why ?? "");
    setMethodName(firstAssessment.method_name ?? "");
    setFeasibility(firstAssessment.transfer_feasibility ?? "");
    setAdaptationsText(asStringArray(firstAssessment.required_adaptations).join("\n"));
    setDifferentiationText(asStringArray(data.differentiation_points).join("\n"));
  }, [
    data.differentiation_points,
    data.recommended_direction?.summary,
    data.recommended_direction?.why,
    firstAssessment.method_name,
    firstAssessment.required_adaptations,
    firstAssessment.transfer_feasibility,
  ]);

  const modifiedPayload = useMemo(() => ({
    transfer_assessments: [
      {
        ...firstAssessment,
        method_name: methodName.trim(),
        transfer_feasibility: feasibility.trim(),
        required_adaptations: adaptationsText.split("\n").map((item) => item.trim()).filter(Boolean),
      },
    ],
    recommended_direction: {
      summary: summary.trim(),
      why: why.trim(),
    },
    differentiation_points: differentiationText.split("\n").map((item) => item.trim()).filter(Boolean),
  }), [adaptationsText, differentiationText, feasibility, firstAssessment, methodName, summary, why]);

  const isChanged = useMemo(() => JSON.stringify(modifiedPayload) !== JSON.stringify({
    transfer_assessments: [
      {
        ...firstAssessment,
        method_name: firstAssessment.method_name ?? "",
        transfer_feasibility: firstAssessment.transfer_feasibility ?? "",
        required_adaptations: asStringArray(firstAssessment.required_adaptations),
      },
    ],
    recommended_direction: {
      summary: data.recommended_direction?.summary ?? "",
      why: data.recommended_direction?.why ?? "",
    },
    differentiation_points: asStringArray(data.differentiation_points),
  }), [data.differentiation_points, data.recommended_direction?.summary, data.recommended_direction?.why, firstAssessment, modifiedPayload]);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>创新性与迁移方向审核</h3>
          <p className={styles.description}>
            确认这条研究路线是否值得继续，以及为什么现在先走这条路。
          </p>
        </div>
        <span className={styles.badge}>{feasibility || "待确认"}</span>
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label htmlFor="method-name" className={sharedStyles.label}>推荐方法</label>
          <input
            id="method-name"
            className={sharedStyles.input}
            value={methodName}
            onChange={(event) => setMethodName(event.target.value)}
            placeholder="例如：固定效应模型"
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="feasibility" className={sharedStyles.label}>迁移可行性</label>
          <input
            id="feasibility"
            className={sharedStyles.input}
            value={feasibility}
            onChange={(event) => setFeasibility(event.target.value)}
            placeholder="例如：高 / 中 / 低"
          />
        </div>
      </div>

      <div className={styles.field}>
        <label htmlFor="summary" className={sharedStyles.label}>推荐方向摘要</label>
        <textarea
          id="summary"
          className={sharedStyles.textarea}
          rows={3}
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          placeholder="一句话说明接下来建议怎么推进"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="why" className={sharedStyles.label}>为什么这样推进</label>
        <textarea
          id="why"
          className={sharedStyles.textarea}
          rows={4}
          value={why}
          onChange={(event) => setWhy(event.target.value)}
          placeholder="解释为什么这条路线适合当前任务"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="adaptations" className={sharedStyles.label}>需要补的调整项</label>
        <textarea
          id="adaptations"
          className={sharedStyles.textarea}
          rows={4}
          value={adaptationsText}
          onChange={(event) => setAdaptationsText(event.target.value)}
          placeholder="每行一个调整项"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="differentiation" className={sharedStyles.label}>差异化要点</label>
        <textarea
          id="differentiation"
          className={sharedStyles.textarea}
          rows={4}
          value={differentiationText}
          onChange={(event) => setDifferentiationText(event.target.value)}
          placeholder="每行一个差异化点"
        />
      </div>

      <div className={styles.actions}>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onReject} disabled={loading}>
          终止任务
        </button>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onApprove} disabled={loading}>
          保持当前判断继续
        </button>
        <button
          type="button"
          className={sharedStyles.btnPrimary}
          onClick={() => onSubmitModified(modifiedPayload)}
          disabled={loading || !isChanged}
        >
          保存调整并继续
        </button>
      </div>
    </section>
  );
}
