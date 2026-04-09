"use client";

import { useEffect, useMemo, useState } from "react";
import sharedStyles from "./shared.module.css";
import styles from "./data-mapping-review.module.css";

interface MappingPayload {
  dependent_var?: string | null;
  independent_vars?: string[];
  control_vars?: string[];
  entity_column?: string | null;
  time_column?: string | null;
  method_preference?: string | null;
  columns?: string[];
  preview?: Array<Record<string, unknown>>;
}

interface DataMappingInterruptData {
  message?: string;
  recommended_mapping?: MappingPayload;
}

interface DataMappingReviewProps {
  interruptData: Record<string, unknown>;
  loading?: boolean;
  onApprove: () => Promise<void>;
  onSubmitModified: (payload: Record<string, unknown>) => Promise<void>;
  onReject: () => Promise<void>;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function parseCommaList(value: string): string[] {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function DataMappingReview({
  interruptData,
  loading = false,
  onApprove,
  onSubmitModified,
  onReject,
}: DataMappingReviewProps) {
  const data = interruptData as DataMappingInterruptData;
  const mapping = data.recommended_mapping ?? {};
  const columns = asStringArray(mapping.columns);
  const preview = Array.isArray(mapping.preview) ? mapping.preview : [];

  const [dependentVar, setDependentVar] = useState(mapping.dependent_var ?? "");
  const [independentVarsText, setIndependentVarsText] = useState(asStringArray(mapping.independent_vars).join(", "));
  const [controlVarsText, setControlVarsText] = useState(asStringArray(mapping.control_vars).join(", "));
  const [entityColumn, setEntityColumn] = useState(mapping.entity_column ?? "");
  const [timeColumn, setTimeColumn] = useState(mapping.time_column ?? "");
  const [methodPreference, setMethodPreference] = useState(mapping.method_preference ?? "");

  useEffect(() => {
    setDependentVar(mapping.dependent_var ?? "");
    setIndependentVarsText(asStringArray(mapping.independent_vars).join(", "));
    setControlVarsText(asStringArray(mapping.control_vars).join(", "));
    setEntityColumn(mapping.entity_column ?? "");
    setTimeColumn(mapping.time_column ?? "");
    setMethodPreference(mapping.method_preference ?? "");
  }, [
    mapping.control_vars,
    mapping.dependent_var,
    mapping.entity_column,
    mapping.independent_vars,
    mapping.method_preference,
    mapping.time_column,
  ]);

  const normalizedPayload = useMemo(() => ({
    dependent_var: dependentVar.trim() || null,
    independent_vars: parseCommaList(independentVarsText),
    control_vars: parseCommaList(controlVarsText),
    entity_column: entityColumn.trim() || null,
    time_column: timeColumn.trim() || null,
    method_preference: methodPreference.trim() || null,
  }), [controlVarsText, dependentVar, entityColumn, independentVarsText, methodPreference, timeColumn]);

  const isChanged = useMemo(() => JSON.stringify(normalizedPayload) !== JSON.stringify({
    dependent_var: mapping.dependent_var ?? null,
    independent_vars: asStringArray(mapping.independent_vars),
    control_vars: asStringArray(mapping.control_vars),
    entity_column: mapping.entity_column ?? null,
    time_column: mapping.time_column ?? null,
    method_preference: mapping.method_preference ?? null,
  }), [mapping.control_vars, mapping.dependent_var, mapping.entity_column, mapping.independent_vars, mapping.method_preference, mapping.time_column, normalizedPayload]);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>变量映射审核</h3>
          <p className={styles.description}>
            {data.message ?? "请确认因变量、自变量和控制变量，后续分析会直接使用这里的结果。"}
          </p>
        </div>
        <span className={styles.badge}>{columns.length} 个字段可选</span>
      </div>

      {columns.length > 0 && (
        <div className={styles.columnsCard}>
          <p className={styles.columnsLabel}>数据字段</p>
          <div className={styles.columnsList}>
            {columns.map((column) => (
              <button
                key={column}
                type="button"
                className={styles.columnChip}
                onClick={() => {
                  if (!dependentVar) {
                    setDependentVar(column);
                  }
                }}
              >
                {column}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className={styles.formGrid}>
        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="dependent-var">
            因变量
          </label>
          <input
            id="dependent-var"
            className={sharedStyles.input}
            value={dependentVar}
            onChange={(event) => setDependentVar(event.target.value)}
            placeholder="例如：碳排放总量"
          />
        </div>

        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="method-preference">
            方法偏好
          </label>
          <input
            id="method-preference"
            className={sharedStyles.input}
            value={methodPreference}
            onChange={(event) => setMethodPreference(event.target.value)}
            placeholder="例如：panel_fe / ols"
          />
        </div>

        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="independent-vars">
            自变量
          </label>
          <textarea
            id="independent-vars"
            className={sharedStyles.textarea}
            value={independentVarsText}
            onChange={(event) => setIndependentVarsText(event.target.value)}
            rows={3}
            placeholder="多个变量用逗号分隔"
          />
        </div>

        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="control-vars">
            控制变量
          </label>
          <textarea
            id="control-vars"
            className={sharedStyles.textarea}
            value={controlVarsText}
            onChange={(event) => setControlVarsText(event.target.value)}
            rows={3}
            placeholder="多个变量用逗号分隔"
          />
        </div>

        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="entity-column">
            地区列
          </label>
          <input
            id="entity-column"
            className={sharedStyles.input}
            value={entityColumn}
            onChange={(event) => setEntityColumn(event.target.value)}
            placeholder="例如：地区"
          />
        </div>

        <div className={styles.field}>
          <label className={sharedStyles.label} htmlFor="time-column">
            时间列
          </label>
          <input
            id="time-column"
            className={sharedStyles.input}
            value={timeColumn}
            onChange={(event) => setTimeColumn(event.target.value)}
            placeholder="例如：年份"
          />
        </div>
      </div>

      {preview.length > 0 && (
        <div className={styles.previewCard}>
          <p className={styles.columnsLabel}>数据预览</p>
          <div className={styles.previewScroller}>
            <table className={styles.previewTable}>
              <thead>
                <tr>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {columns.map((column) => (
                      <td key={`${rowIndex}-${column}`}>{String(row[column] ?? "-")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className={styles.actions}>
        <button
          type="button"
          className={sharedStyles.btnSecondary}
          onClick={onReject}
          disabled={loading}
        >
          终止任务
        </button>
        <button
          type="button"
          className={sharedStyles.btnSecondary}
          onClick={onApprove}
          disabled={loading}
        >
          直接采用推荐映射
        </button>
        <button
          type="button"
          className={sharedStyles.btnPrimary}
          onClick={() => onSubmitModified(normalizedPayload)}
          disabled={loading || !isChanged}
        >
          提交修改并继续
        </button>
      </div>
    </section>
  );
}
