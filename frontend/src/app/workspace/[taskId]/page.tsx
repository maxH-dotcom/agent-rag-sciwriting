import Link from "next/link";
import { fetchTask } from "../../../../lib/api";
import { TaskLiveDetail } from "../../../../components/task-live-detail";
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

      <TaskLiveDetail taskId={params.taskId} initialTask={task} initialError={error} />
    </main>
  );
}
