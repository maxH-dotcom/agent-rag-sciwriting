import Link from "next/link";
import { fetchTask } from "../../../../lib/api";
import { TaskDetail } from "../../../../components/task-detail";
import { TaskProgress } from "../../../../components/task-progress";
import styles from "./page.module.css";

type TaskDetailPageProps = {
  params: { taskId: string };
};

export default async function TaskDetailPage({ params }: TaskDetailPageProps) {
  let task = null;
  let error: string | null = null;

  try {
    task = await fetchTask(params.taskId);
  } catch (requestError) {
    error = requestError instanceof Error ? requestError.message : "任务加载失败";
  }

  return (
    <main className={styles.main}>
      {/* ── Header ──────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h1 className={styles.title}>任务详情</h1>
          <p className={styles.taskId}>任务 ID: {params.taskId}</p>
        </div>
        <Link href="/workspace" className={styles.backLink}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          返回工作台
        </Link>
      </div>

      {/* ── Error ───────────────────────────── */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </div>
      )}

      {/* ── Task ─────────────────────────────── */}
      {task && (
        <>
          {/* Progress stepper */}
          <div className={styles.card} style={{ padding: "var(--space-xl)" }}>
            <TaskProgress currentNode={task.current_node} status={task.status} />
          </div>

          {/* Summary card */}
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>任务摘要</h2>
            <dl className={styles.dl}>
              <div className={styles.dlRow}>
                <dt>研究问题</dt>
                <dd>{task.user_query}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>状态</dt>
                <dd>
                  <span className={`${styles.status} ${styles[`status_${task.status}`] ?? ""}`}>
                    {task.status}
                  </span>
                </dd>
              </div>
              <div className={styles.dlRow}>
                <dt>当前节点</dt>
                <dd>{task.current_node}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>中断原因</dt>
                <dd>{task.interrupt_reason || "无"}</dd>
              </div>
              <div className={styles.dlRow}>
                <dt>下一步</dt>
                <dd>{task.next_action || "无"}</dd>
              </div>
            </dl>
          </div>

          {/* Structured result / interrupt data */}
          <TaskDetail task={task} />
        </>
      )}
    </main>
  );
}
