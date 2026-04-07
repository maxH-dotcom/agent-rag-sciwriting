"use client";

import { useEffect } from "react";
import { useTaskStore } from "../lib/stores/task-store";
import { TaskProgress } from "./task-progress";
import sharedStyles from "./shared.module.css";
import styles from "./interrupt-manager.module.css";

interface InterruptManagerProps {
  taskId: string | null;
  onTaskUpdate?: () => void;
}

export function InterruptManager({ taskId, onTaskUpdate }: InterruptManagerProps) {
  const {
    currentTask,
    fetchTask,
    continueTask,
    abortTask,
    isLoading,
    error,
    connectStream,
    disconnectStream,
    stopPolling,
    isPolling,
    streamStatus,
    streamError,
  } = useTaskStore();

  useEffect(() => {
    if (!taskId) return;
    fetchTask(taskId);
    connectStream(taskId);
    return () => {
      disconnectStream();
      stopPolling();
    };
  }, [taskId, fetchTask, connectStream, disconnectStream, stopPolling]);

  useEffect(() => {
    if (currentTask && ["done", "failed", "error", "aborted"].includes(currentTask.status)) {
      disconnectStream();
      stopPolling();
      onTaskUpdate?.();
    }
  }, [currentTask?.status, disconnectStream, stopPolling, onTaskUpdate]);

  async function handleContinue() {
    if (!taskId) return;
    await continueTask(taskId);
  }

  async function handleAbort() {
    if (!taskId) return;
    await abortTask(taskId);
    stopPolling();
  }

  if (!taskId) {
    return (
      <p className={sharedStyles.mutedText}>还没有任务。先创建一个。</p>
    );
  }

  if (!currentTask) {
    return (
      <div className={sharedStyles.card}>
        <div className={sharedStyles.mutedText}>
          <span className={sharedStyles.spinner} aria-hidden="true" />
          正在加载任务状态...
        </div>
      </div>
    );
  }

  const isInterrupted = currentTask.status === "interrupted";
  const isRunning = currentTask.status === "running" || currentTask.status === "pending";

  return (
    <div className={sharedStyles.card}>
      {/* ── Progress Stepper ─────────────────────── */}
      <TaskProgress currentNode={currentTask.current_node} status={currentTask.status} />

      {/* ── Summary ─────────────────────────────── */}
      <h2 className={sharedStyles.sectionHeading} style={{ marginTop: "var(--space-xl)" }}>
        当前状态
      </h2>
      <dl className={styles.dl}>
        <div className={styles.dlRow}>
          <dt>任务类型</dt>
          <dd>{currentTask.task_type}</dd>
        </div>
        <div className={styles.dlRow}>
          <dt>研究问题</dt>
          <dd>{currentTask.user_query}</dd>
        </div>
        <div className={styles.dlRow}>
          <dt>节点</dt>
          <dd>{currentTask.current_node}</dd>
        </div>
        <div className={styles.dlRow}>
          <dt>状态</dt>
          <dd>
                  <span className={`${sharedStyles.status} ${sharedStyles[`status_${currentTask.status}`] ?? ""}`}>
                    {streamStatus === "live"
                      ? `${currentTask.status} (SSE 实时更新)`
                      : isRunning && isPolling
                        ? `${currentTask.status} (轮询刷新)`
                        : currentTask.status}
                  </span>
                </dd>
              </div>
        <div className={styles.dlRow}>
          <dt>中断原因</dt>
          <dd>{currentTask.interrupt_reason || "无"}</dd>
        </div>
        <div className={styles.dlRow}>
          <dt>下一步</dt>
          <dd>{currentTask.next_action || "无"}</dd>
        </div>
        {currentTask.data_files?.length ? (
          <div className={styles.dlRow}>
            <dt>数据文件</dt>
            <dd className={styles.filePaths}>{currentTask.data_files.join(", ")}</dd>
          </div>
        ) : null}
        {currentTask.paper_files?.length ? (
          <div className={styles.dlRow}>
            <dt>论文文件</dt>
            <dd className={styles.filePaths}>{currentTask.paper_files.join(", ")}</dd>
          </div>
        ) : null}
      </dl>

      {/* ── Action buttons ───────────────────────── */}
      {isInterrupted && (
        <div className={styles.actions}>
          <button
            onClick={handleContinue}
            disabled={isLoading}
            className={sharedStyles.btnPrimary}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <span className={sharedStyles.spinner} aria-hidden="true" />
                处理中...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                继续任务
              </>
            )}
          </button>
          <button
            onClick={handleAbort}
            disabled={isLoading}
            className={sharedStyles.btnSecondary}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <span className={sharedStyles.spinner} aria-hidden="true" />
                处理中...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                </svg>
                终止任务
              </>
            )}
          </button>
        </div>
      )}

      {/* ── Running indicator ────────────────────── */}
      {isRunning && (
        <div className={sharedStyles.mutedText} style={{ marginTop: "var(--space-md)" }}>
          <span className={sharedStyles.spinner} aria-hidden="true" />
          {streamStatus === "connecting"
            ? "正在建立实时连接..."
            : streamStatus === "live"
              ? "任务执行中，状态会实时推送到页面。"
              : "任务执行中，页面会自动刷新状态。"}
        </div>
      )}

      {/* ── Error ───────────────────────────────── */}
      {(error || streamError) && (
        <div className={sharedStyles.errorText} role="alert">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error || streamError}
        </div>
      )}

      {/* ── Interrupt data ───────────────────────── */}
      {currentTask.interrupt_data && (
        <>
          <h3 className={styles.subheading}>中断数据</h3>
          <pre className={sharedStyles.codeBlock}>
            {JSON.stringify(currentTask.interrupt_data, null, 2)}
          </pre>
        </>
      )}

      {/* ── Result ──────────────────────────────── */}
      {currentTask.result && (
        <details className={styles.details}>
          <summary className={styles.detailsSummary}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
            查看完整结果
          </summary>
          <pre className={sharedStyles.codeBlock}>
            {JSON.stringify(currentTask.result, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
