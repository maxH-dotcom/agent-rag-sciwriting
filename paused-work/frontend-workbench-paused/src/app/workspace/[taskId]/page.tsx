import Link from "next/link";

import { fetchTask } from "../../../lib/api";

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
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, marginBottom: 8 }}>任务详情</h1>
          <p style={{ color: "#4b5563", margin: 0 }}>任务 ID: {params.taskId}</p>
        </div>
        <Link href="/workspace" style={{ textDecoration: "none", color: "#2563eb" }}>
          返回工作台
        </Link>
      </div>

      {error ? <p style={{ color: "#b91c1c" }}>{error}</p> : null}

      {task ? (
        <section style={{ display: "grid", gap: 16, marginTop: 24 }}>
          <div style={{ background: "#fff", padding: 20, borderRadius: 16 }}>
            <h2 style={{ marginTop: 0 }}>任务摘要</h2>
            <p>研究问题: {task.user_query}</p>
            <p>状态: {task.status}</p>
            <p>当前节点: {task.current_node}</p>
            <p>中断原因: {task.interrupt_reason || "无"}</p>
          </div>

          <div style={{ background: "#fff", padding: 20, borderRadius: 16 }}>
            <h2 style={{ marginTop: 0 }}>当前中断数据</h2>
            <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", borderRadius: 12, padding: 12 }}>
              {JSON.stringify(task.interrupt_data, null, 2)}
            </pre>
          </div>

          <div style={{ background: "#fff", padding: 20, borderRadius: 16 }}>
            <h2 style={{ marginTop: 0 }}>完整结果</h2>
            <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", borderRadius: 12, padding: 12 }}>
              {JSON.stringify(task.result, null, 2)}
            </pre>
          </div>
        </section>
      ) : null}
    </main>
  );
}

