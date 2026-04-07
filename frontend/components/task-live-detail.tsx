"use client";

import { useEffect, useState } from "react";
import { fetchTask, type TaskPayload } from "../lib/api";
import { TaskDetail } from "./task-detail";
import { TaskProgress } from "./task-progress";
import styles from "../src/app/workspace/[taskId]/page.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const TERMINAL_STATUSES = new Set(["done", "failed", "error", "aborted"]);

type ConnectionState = "idle" | "connecting" | "live" | "fallback";

interface TaskLiveDetailProps {
  taskId: string;
  initialTask: TaskPayload | null;
  initialError: string | null;
}

export function TaskLiveDetail({ taskId, initialTask, initialError }: TaskLiveDetailProps) {
  const [task, setTask] = useState<TaskPayload | null>(initialTask);
  const [error, setError] = useState<string | null>(initialError);
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");

  useEffect(() => {
    let cancelled = false;
    let eventSource: EventSource | null = null;
    let interval: ReturnType<typeof setInterval> | null = null;

    const stopPolling = () => {
      if (interval) {
        clearInterval(interval);
        interval = null;
      }
    };

    const refreshTask = async () => {
      try {
        const nextTask = await fetchTask(taskId);
        if (cancelled) return;
        setTask(nextTask);
        setError(null);
        if (TERMINAL_STATUSES.has(nextTask.status)) {
          stopPolling();
        }
      } catch (requestError) {
        if (cancelled) return;
        setError(requestError instanceof Error ? requestError.message : "任务加载失败");
      }
    };

    const startPolling = () => {
      stopPolling();
      setConnectionState("fallback");
      interval = setInterval(() => {
        void refreshTask();
      }, 3000);
    };

    const connectStream = () => {
      if (typeof window === "undefined" || typeof EventSource === "undefined") {
        startPolling();
        return;
      }

      setConnectionState("connecting");
      eventSource = new EventSource(`${API_BASE_URL}/tasks/${taskId}/stream`);

      eventSource.addEventListener("task", (event) => {
        try {
          const nextTask = JSON.parse(event.data) as TaskPayload;
          if (cancelled) return;
          setTask(nextTask);
          setError(null);
          setConnectionState(TERMINAL_STATUSES.has(nextTask.status) ? "idle" : "live");

          if (TERMINAL_STATUSES.has(nextTask.status) && eventSource) {
            eventSource.close();
            eventSource = null;
          }
        } catch {
          // Ignore malformed events.
        }
      });

      eventSource.onopen = () => {
        if (cancelled) return;
        stopPolling();
        setConnectionState("live");
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        if (cancelled) return;
        startPolling();
      };
    };

    if (!initialTask) {
      void refreshTask();
    }
    connectStream();

    return () => {
      cancelled = true;
      stopPolling();
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [taskId, initialTask]);

  return (
    <>
      {error && (
        <div className={styles.errorBanner} role="alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </div>
      )}

      {task && (
        <>
          <div className={styles.card} style={{ padding: "var(--space-xl)" }}>
            <div className={styles.liveMeta}>
              <TaskProgress currentNode={task.current_node} status={task.status} />
              <div className={styles.liveBadgeRow}>
                <span className={`${styles.liveBadge} ${styles[`liveBadge_${connectionState}`] ?? ""}`}>
                  {connectionState === "live" && "SSE 实时连接"}
                  {connectionState === "connecting" && "正在建立连接"}
                  {connectionState === "fallback" && "轮询刷新中"}
                  {connectionState === "idle" && "状态已稳定"}
                </span>
              </div>
            </div>
          </div>

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
              <div className={styles.dlRow}>
                <dt>连接状态</dt>
                <dd>
                  {connectionState === "live" && "后端推送中，页面无需手动刷新。"}
                  {connectionState === "connecting" && "正在建立 SSE 连接。"}
                  {connectionState === "fallback" && "实时连接不可用，已自动切换为轮询。"}
                  {connectionState === "idle" && "任务已完成或当前没有新的状态变化。"}
                </dd>
              </div>
            </dl>
          </div>

          <TaskDetail task={task} />
        </>
      )}
    </>
  );
}
