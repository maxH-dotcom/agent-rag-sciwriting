"use client";

import { useEffect, useMemo, useState } from "react";
import sharedStyles from "./shared.module.css";
import styles from "./brief-review.module.css";

interface BriefInterruptData {
  research_goal?: string;
  status?: string;
  method_decision?: {
    recommended_models?: string[];
  };
  audit_trail?: Array<{ node?: string; action?: string }>;
}

interface BriefReviewProps {
  interruptData: Record<string, unknown>;
  loading?: boolean;
  onApprove: () => Promise<void>;
  onSubmitModified: (payload: Record<string, unknown>) => Promise<void>;
  onReject: () => Promise<void>;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function BriefReview({
  interruptData,
  loading = false,
  onApprove,
  onSubmitModified,
  onReject,
}: BriefReviewProps) {
  const data = interruptData as BriefInterruptData;
  const [researchGoal, setResearchGoal] = useState(data.research_goal ?? "");
  const [status, setStatus] = useState(data.status ?? "draft");
  const [modelsText, setModelsText] = useState(asStringArray(data.method_decision?.recommended_models).join(", "));

  useEffect(() => {
    setResearchGoal(data.research_goal ?? "");
    setStatus(data.status ?? "draft");
    setModelsText(asStringArray(data.method_decision?.recommended_models).join(", "));
  }, [data.method_decision?.recommended_models, data.research_goal, data.status]);

  const payload = useMemo(() => ({
    research_goal: researchGoal.trim(),
    status: status.trim(),
    method_decision: {
      ...(data.method_decision ?? {}),
      recommended_models: modelsText.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    },
  }), [data.method_decision, modelsText, researchGoal, status]);

  const isChanged = useMemo(() => JSON.stringify(payload) !== JSON.stringify({
    research_goal: data.research_goal ?? "",
    status: data.status ?? "draft",
    method_decision: {
      ...(data.method_decision ?? {}),
      recommended_models: asStringArray(data.method_decision?.recommended_models),
    },
  }), [data.method_decision, data.research_goal, data.status, payload]);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Research Brief 审核</h3>
          <p className={styles.description}>
            在进入写作草稿前，确认研究目标、简报状态和方法决策是否准确。
          </p>
        </div>
        <span className={styles.badge}>{status || "draft"}</span>
      </div>

      <div className={styles.field}>
        <label htmlFor="brief-goal" className={sharedStyles.label}>研究目标</label>
        <textarea
          id="brief-goal"
          className={sharedStyles.textarea}
          rows={4}
          value={researchGoal}
          onChange={(event) => setResearchGoal(event.target.value)}
        />
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label htmlFor="brief-status" className={sharedStyles.label}>简报状态</label>
          <input
            id="brief-status"
            className={sharedStyles.input}
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            placeholder="draft"
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="brief-models" className={sharedStyles.label}>候选模型</label>
          <input
            id="brief-models"
            className={sharedStyles.input}
            value={modelsText}
            onChange={(event) => setModelsText(event.target.value)}
            placeholder="多个模型用逗号分隔"
          />
        </div>
      </div>

      {!!data.audit_trail?.length && (
        <div className={styles.auditCard}>
          <p className={styles.auditTitle}>审计轨迹</p>
          <ul className={styles.auditList}>
            {data.audit_trail.map((item, index) => (
              <li key={index}>
                {(item.node || "unknown")} · {(item.action || "unknown")}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className={styles.actions}>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onReject} disabled={loading}>
          终止任务
        </button>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onApprove} disabled={loading}>
          保持当前简报继续
        </button>
        <button type="button" className={sharedStyles.btnPrimary} onClick={() => onSubmitModified(payload)} disabled={loading || !isChanged}>
          保存修改并继续
        </button>
      </div>
    </section>
  );
}
