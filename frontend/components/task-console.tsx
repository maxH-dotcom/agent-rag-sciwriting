"use client";

import { useState, useEffect } from "react";
import { InterruptManager } from "./interrupt-manager";
import { TaskList } from "./task-list";
import { useTaskStore } from "../lib/stores/task-store";
import sharedStyles from "./shared.module.css";
import styles from "./task-console.module.css";

function _getErrorHint(errorMsg: string): string {
  const msg = errorMsg.toLowerCase();
  if (msg.includes("absolute") || msg.includes("绝对路径")) {
    return "数据文件路径必须是绝对路径，不能是相对路径或文件名";
  }
  if (msg.includes("not exist") || msg.includes("不存在")) {
    return "请确认文件存在，路径中没有拼写错误";
  }
  if (msg.includes("csv") || msg.includes("xlsx")) {
    return "数据文件格式应为 .csv、.xlsx 或 .xls";
  }
  if (msg.includes("pdf") || msg.includes("txt") || msg.includes("md")) {
    return "数据文件格式应为 .pdf、.txt 或 .md";
  }
  if (msg.includes("format") || msg.includes("类型") || msg.includes("不支持")) {
    return "请检查文件格式是否在支持列表中";
  }
  return "请检查文件路径是否正确，或尝试不填文件路径直接创建";
}

export function TaskConsole() {
  const { createTask, isLoading, error, clearError, fetchTasks } = useTaskStore();
  const [createdTaskId, setCreatedTaskId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [query, setQuery] = useState("我想分析农业产值对碳排放的影响，同时控制农药使用量");
  const [dataFile, setDataFile] = useState("");
  const [paperFile, setPaperFile] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  async function handleCreateTask() {
    if (!query.trim()) return;
    setLocalError(null);
    try {
      const taskId = await createTask({
        task_type: "analysis",
        user_query: query,
        data_files: dataFile ? [dataFile] : [],
        paper_files: paperFile ? [paperFile] : [],
      });
      setCreatedTaskId(taskId);
      setRefreshKey((v) => v + 1);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "创建任务失败");
    }
  }

  const displayError = localError || error;

  return (
    <section className={styles.sections}>
      {/* ── Create task form ─────────────────────── */}
      <div className={sharedStyles.card}>
        <h2 className={sharedStyles.sectionHeading}>创建新任务</h2>

        <div className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="query" className={sharedStyles.label}>
              研究问题
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              rows={4}
              className={sharedStyles.textarea}
              placeholder="描述你的研究问题..."
            />
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="dataFile" className={sharedStyles.label}>
                数据文件路径（可选）
              </label>
              <input
                id="dataFile"
                type="text"
                value={dataFile}
                onChange={(event) => setDataFile(event.target.value)}
                placeholder="/absolute/path/to/data.csv"
                className={sharedStyles.input}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="paperFile" className={sharedStyles.label}>
                参考论文路径（可选）
              </label>
              <input
                id="paperFile"
                type="text"
                value={paperFile}
                onChange={(event) => setPaperFile(event.target.value)}
                placeholder="/absolute/path/to/paper.pdf"
                className={sharedStyles.input}
              />
            </div>
          </div>

          <button
            onClick={handleCreateTask}
            disabled={isLoading || !query.trim()}
            className={sharedStyles.btnPrimary}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <span className={sharedStyles.spinner} aria-hidden="true" />
                创建中...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                创建任务
              </>
            )}
          </button>

          {displayError && (
            <div className={styles.errorCard} role="alert">
              <div className={styles.errorHeader}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                创建失败
              </div>
              <p className={styles.errorMessage}>{displayError}</p>
              <div className={styles.errorHint}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span>{_getErrorHint(displayError)}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Interrupt manager ─────────────────────── */}
      {createdTaskId && (
        <InterruptManager taskId={createdTaskId} onTaskUpdate={() => setRefreshKey((v) => v + 1)} />
      )}

      {/* ── Task history ─────────────────────────── */}
      <section>
        <h2 className={sharedStyles.sectionHeading}>历史任务</h2>
        <TaskList refreshKey={refreshKey} />
      </section>
    </section>
  );
}
