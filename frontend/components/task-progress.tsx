"use client";

import styles from "./task-progress.module.css";

const NODES = [
  { id: "user_query",       label: "问题解析" },
  { id: "data_mapping",     label: "数据映射" },
  { id: "literature_review", label: "文献综述" },
  { id: "innovation_judgment", label: "创新判断" },
  { id: "code_generation",   label: "代码生成" },
  { id: "brief_output",     label: "简报输出" },
];

interface TaskProgressProps {
  currentNode: string;
  status: string;
}

function getStepStatus(
  nodeId: string,
  currentNode: string,
  status: string
): "pending" | "running" | "done" | "error" | "interrupted" {
  const currentIndex = NODES.findIndex((n) => n.id === currentNode);
  const stepIndex = NODES.findIndex((n) => n.id === nodeId);

  if (status === "failed" || status === "aborted") {
    if (stepIndex === currentIndex) return "error";
    if (stepIndex < currentIndex) return "error";
    return "pending";
  }

  if (stepIndex < currentIndex) return "done";
  if (stepIndex === currentIndex) {
    if (status === "interrupted") return "interrupted";
    if (status === "running" || status === "pending") return "running";
    if (status === "done") return "done";
    return "running";
  }
  return "pending";
}

export function TaskProgress({ currentNode, status }: TaskProgressProps) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.label}>执行进度</span>
      </div>
      <div className={styles.stepper} role="list" aria-label="任务执行进度">
        {NODES.map((node, index) => {
          const stepStatus = getStepStatus(node.id, currentNode, status);
          const isLast = index === NODES.length - 1;

          return (
            <div key={node.id} style={{ display: "contents" }}>
              <div
                className={`${styles.step} ${styles[`step--${stepStatus}`]}`}
                role="listitem"
                aria-label={`${node.label}: ${stepStatus}`}
              >
                <div className={styles.stepDot}>
                  {stepStatus === "done" ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  ) : stepStatus === "error" ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  ) : stepStatus === "interrupted" ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
                    </svg>
                  ) : (
                    <span aria-hidden="true">{index + 1}</span>
                  )}
                </div>
                <span className={styles.stepLabel}>{node.label}</span>
              </div>
              {!isLast && (
                <div
                  className={`${styles.stepConnector} ${stepStatus === "done" ? styles.stepConnectorDone : ""}`}
                  aria-hidden="true"
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
