"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchTasks, type TaskPayload } from "../lib/api";

export function TaskList({ refreshKey = 0 }: { refreshKey?: number }) {
  const [tasks, setTasks] = useState<TaskPayload[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTasks()
      .then((items) => {
        setTasks(items);
        setError(null);
      })
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "任务列表加载失败");
      })
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return <div style={{ color: "#6b7280" }}>正在读取任务列表...</div>;
  }

  if (error) {
    return <div style={{ color: "#b91c1c" }}>{error}</div>;
  }

  if (!tasks.length) {
    return <div style={{ color: "#6b7280" }}>还没有历史任务。先创建一个。</div>;
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {tasks.map((task) => (
        <Link
          key={task.task_id}
          href={`/workspace/${task.task_id}`}
          style={{
            display: "grid",
            gap: 6,
            background: "#fff",
            padding: 16,
            borderRadius: 16,
            textDecoration: "none",
            color: "#111827",
            border: "1px solid #e5e7eb",
          }}
        >
          <strong>{task.user_query}</strong>
          <span>任务 ID: {task.task_id}</span>
          <span>节点: {task.current_node}</span>
          <span>状态: {task.status}</span>
        </Link>
      ))}
    </div>
  );
}

