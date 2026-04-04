"use client";

import { useEffect, useState } from "react";

import { fetchTask, type TaskPayload } from "../lib/api";

export function InterruptManager({ taskId }: { taskId: string | null }) {
  const [task, setTask] = useState<TaskPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadTask(targetTaskId: string) {
    const payload = await fetchTask(targetTaskId);
    setTask(payload);
  }

  async function updateTask(action: "continue" | "abort") {
    if (!taskId || !task) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body:
          action === "continue"
            ? JSON.stringify({ decision: "approved", payload: { source: "frontend" } })
            : JSON.stringify({ reason: "frontend_abort" }),
      });
      if (!response.ok) {
        throw new Error(`${action} 失败: ${response.status}`);
      }
      const payload = await response.json();
      setTask(payload);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "任务更新失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    if (!taskId) return;
    loadTask(taskId).catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : "任务加载失败");
    });
  }, [taskId]);

  if (!taskId) {
    return <div style={{ color: "#6b7280" }}>还没有任务。先创建一个。</div>;
  }

  if (!task) {
    return <div>正在加载任务状态...</div>;
  }

  return (
    <div style={{ background: "#fff", padding: 20, borderRadius: 18 }}>
      <h2 style={{ marginTop: 0 }}>当前状态</h2>
      <p>任务类型: {task.task_type}</p>
      <p>研究问题: {task.user_query}</p>
      <p>节点: {task.current_node}</p>
      <p>状态: {task.status}</p>
      <p>中断原因: {task.interrupt_reason || "无"}</p>
      <p>下一步: {task.next_action || "无"}</p>
      {task.data_files?.length ? <p>数据文件: {task.data_files.join(", ")}</p> : null}
      {task.paper_files?.length ? <p>论文文件: {task.paper_files.join(", ")}</p> : null}
      {task.status === "interrupted" ? (
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          <button
            onClick={() => updateTask("continue")}
            disabled={isSubmitting}
            style={{ background: "#111827", color: "#fff", border: 0, borderRadius: 999, padding: "10px 16px", cursor: "pointer" }}
          >
            {isSubmitting ? "处理中..." : "继续任务"}
          </button>
          <button
            onClick={() => updateTask("abort")}
            disabled={isSubmitting}
            style={{ background: "#fff", color: "#b91c1c", border: "1px solid #fecaca", borderRadius: 999, padding: "10px 16px", cursor: "pointer" }}
          >
            终止任务
          </button>
        </div>
      ) : null}
      {error ? <p style={{ color: "#b91c1c" }}>{error}</p> : null}
      <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", borderRadius: 12, padding: 12 }}>
        {JSON.stringify(task.interrupt_data, null, 2)}
      </pre>
      {task.result ? (
        <details style={{ marginTop: 16 }}>
          <summary style={{ cursor: "pointer" }}>查看完整结果</summary>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", borderRadius: 12, padding: 12, marginTop: 12 }}>
            {JSON.stringify(task.result, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
