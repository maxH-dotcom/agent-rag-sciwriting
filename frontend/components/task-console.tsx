"use client";

import { useState, useEffect } from "react";
import { FileUploader, type UploadedFile } from "./file-uploader";
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
  const [dataFiles, setDataFiles] = useState<UploadedFile[]>([]);
  const [paperFiles, setPaperFiles] = useState<UploadedFile[]>([]);
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
        data_files: dataFiles.map((file) => file.path),
        paper_files: paperFiles.map((file) => file.path),
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
              <label className={sharedStyles.label}>
                数据文件（可选）
              </label>
              <FileUploader
                kind="data"
                onChange={setDataFiles}
                label="上传数据文件"
                helperText="支持 .csv、.xlsx、.xls，上传后会自动写入任务请求"
              />
            </div>

            <div className={styles.field}>
              <label className={sharedStyles.label}>
                参考材料（可选）
              </label>
              <FileUploader
                kind="paper"
                onChange={setPaperFiles}
                label="上传论文或笔记"
                helperText="支持 .pdf、.txt、.md，可同时上传多份材料"
              />
            </div>
          </div>

          {(dataFiles.length > 0 || paperFiles.length > 0) && (
            <div className={styles.uploadSummary}>
              <p className={styles.uploadSummaryTitle}>本次任务将使用以下已上传文件</p>
              <div className={styles.uploadSummaryStats}>
                <span>数据文件 {dataFiles.length} 个</span>
                <span>参考材料 {paperFiles.length} 个</span>
              </div>
            </div>
          )}

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
