"use client";

import { useEffect, useMemo, useState } from "react";
import sharedStyles from "./shared.module.css";
import styles from "./literature-review.module.css";

interface LiteratureReference {
  reference_id: string;
  title: string;
  citation?: string;
  source_type?: string;
  url?: string | null;
}

interface LiteratureInterruptData {
  message?: string;
  literature_result?: {
    references?: LiteratureReference[];
    quality_score?: number;
    quality_warning?: string | null;
    source_stats?: Record<string, number>;
    selected_reference_ids?: string[];
  };
}

interface LiteratureReviewProps {
  interruptData: Record<string, unknown>;
  loading?: boolean;
  onApprove: () => Promise<void>;
  onSubmitModified: (payload: Record<string, unknown>) => Promise<void>;
  onReject: () => Promise<void>;
}

function asReferences(value: unknown): LiteratureReference[] {
  return Array.isArray(value)
    ? value.filter((item): item is LiteratureReference => !!item && typeof item === "object" && "reference_id" in item)
    : [];
}

export function LiteratureReview({
  interruptData,
  loading = false,
  onApprove,
  onSubmitModified,
  onReject,
}: LiteratureReviewProps) {
  const data = interruptData as LiteratureInterruptData;
  const literature = data.literature_result ?? {};
  const references = asReferences(literature.references);
  const initialSelected = useMemo(
    () => (Array.isArray(literature.selected_reference_ids) && literature.selected_reference_ids.length
      ? literature.selected_reference_ids
      : references.map((ref) => ref.reference_id)),
    [literature.selected_reference_ids, references],
  );
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelected);

  useEffect(() => {
    setSelectedIds(initialSelected);
  }, [initialSelected]);

  const selectedReferences = useMemo(
    () => references.filter((ref) => selectedIds.includes(ref.reference_id)),
    [references, selectedIds],
  );

  const isChanged = useMemo(
    () => JSON.stringify([...selectedIds].sort()) !== JSON.stringify([...initialSelected].sort()),
    [initialSelected, selectedIds],
  );

  function toggleReference(referenceId: string) {
    setSelectedIds((current) =>
      current.includes(referenceId)
        ? current.filter((id) => id !== referenceId)
        : [...current, referenceId],
    );
  }

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>文献审核</h3>
          <p className={styles.description}>
            {data.message ?? "保留真正相关的候选文献，后续创新判断和代码方案会优先使用这些证据。"}
          </p>
        </div>
        <span className={styles.badge}>已选 {selectedIds.length} / {references.length}</span>
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>检索质量</p>
          <p className={styles.summaryValue}>
            {typeof literature.quality_score === "number" ? literature.quality_score.toFixed(2) : "暂无"}
          </p>
        </div>
        <div className={styles.summaryCard}>
          <p className={styles.summaryLabel}>来源统计</p>
          <p className={styles.summaryValue}>
            {literature.source_stats
              ? Object.entries(literature.source_stats).map(([key, value]) => `${key}: ${value}`).join(" / ")
              : "暂无"}
          </p>
        </div>
      </div>

      {literature.quality_warning ? (
        <div className={styles.warningCard}>{literature.quality_warning}</div>
      ) : null}

      <div className={styles.list}>
        {references.map((reference) => {
          const checked = selectedIds.includes(reference.reference_id);
          return (
            <label key={reference.reference_id} className={`${styles.item} ${checked ? styles.itemSelected : ""}`}>
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleReference(reference.reference_id)}
                disabled={loading}
              />
              <div className={styles.itemBody}>
                <div className={styles.itemHeader}>
                  <p className={styles.itemTitle}>{reference.title}</p>
                  {reference.source_type ? <span className={styles.itemBadge}>{reference.source_type}</span> : null}
                </div>
                {reference.citation ? <p className={styles.itemCitation}>{reference.citation}</p> : null}
                {reference.url ? (
                  <a href={reference.url} target="_blank" rel="noreferrer" className={styles.itemLink}>
                    查看来源
                  </a>
                ) : null}
              </div>
            </label>
          );
        })}
      </div>

      <div className={styles.actions}>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onReject} disabled={loading}>
          终止任务
        </button>
        <button type="button" className={sharedStyles.btnSecondary} onClick={onApprove} disabled={loading}>
          保持当前结果继续
        </button>
        <button
          type="button"
          className={sharedStyles.btnPrimary}
          onClick={() => onSubmitModified({
            references: selectedReferences,
            selected_reference_ids: selectedIds,
          })}
          disabled={loading || !isChanged}
        >
          保存筛选并继续
        </button>
      </div>
    </section>
  );
}
