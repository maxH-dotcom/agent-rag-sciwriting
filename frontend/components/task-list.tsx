"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useTaskStore } from "../lib/stores/task-store";
import sharedStyles from "./shared.module.css";
import styles from "./task-list.module.css";

export function TaskList({ refreshKey = 0 }: { refreshKey?: number }) {
  const { tasks, fetchTasks, isLoading, error } = useTaskStore();

  useEffect(() => {
    fetchTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  if (isLoading && !tasks.length) {
    return (
      <div className={sharedStyles.mutedText}>
        <span className={sharedStyles.spinner} aria-hidden="true" />
        正在读取任务列表...
      </div>
    );
  }

  if (error && !tasks.length) {
    return (
      <div className={sharedStyles.errorText} role="alert">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        {error}
      </div>
    );
  }

  if (!tasks.length) {
    return (
      <p className={sharedStyles.mutedText}>还没有历史任务。先创建一个。</p>
    );
  }

  return (
    <div className={styles.list} role="list">
      {tasks.map((task) => (
        <Link
          key={task.task_id}
          href={`/workspace/${task.task_id}`}
          className={styles.item}
          role="listitem"
        >
          <div className={styles.itemHeader}>
            <span className={`${sharedStyles.status} ${sharedStyles[`status_${task.status}`] ?? ""}`}>
              {task.status}
            </span>
            <span className={styles.node}>{task.current_node}</span>
          </div>
          <p className={styles.query}>{task.user_query}</p>
          <p className={styles.taskId}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            {task.task_id}
          </p>
        </Link>
      ))}
    </div>
  );
}
