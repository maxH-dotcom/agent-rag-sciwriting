"use client";

import { useState } from "react";

import { InterruptManager } from "./interrupt-manager";
import { TaskList } from "./task-list";
import { API_BASE_URL } from "../lib/config";

export function TaskConsole() {
  const [createdTaskId, setCreatedTaskId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [query, setQuery] = useState("我想分析农业产值对碳排放的影响，同时控制农药使用量");
  const [dataFile, setDataFile] = useState("");
  const [paperFile, setPaperFile] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  async function createTask() {
    setError(null);
    setIsCreating(true);
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_type: "analysis",
          user_query: query,
          data_files: dataFile ? [dataFile] : [],
          paper_files: paperFile ? [paperFile] : [],
        }),
      });

      if (!response.ok) {
        throw new Error(`创建任务失败: ${response.status}`);
      }

      const data = await response.json();
      setCreatedTaskId(data.task_id);
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "创建任务失败");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section style={{ display: "grid", gap: 20 }}>
      <div style={{ background: "#fff", padding: 20, borderRadius: 18 }}>
        <label style={{ display: "grid", gap: 8 }}>
          <span>研究问题</span>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            style={{ width: "100%", borderRadius: 12, border: "1px solid #d1d5db", padding: 12 }}
          />
        </label>
        <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
          <label style={{ display: "grid", gap: 8 }}>
            <span>数据文件路径（可选）</span>
            <input
              value={dataFile}
              onChange={(event) => setDataFile(event.target.value)}
              placeholder="/absolute/path/to/data.csv"
              style={{ width: "100%", borderRadius: 12, border: "1px solid #d1d5db", padding: 12 }}
            />
          </label>
          <label style={{ display: "grid", gap: 8 }}>
            <span>参考论文路径（可选）</span>
            <input
              value={paperFile}
              onChange={(event) => setPaperFile(event.target.value)}
              placeholder="/absolute/path/to/paper.pdf"
              style={{ width: "100%", borderRadius: 12, border: "1px solid #d1d5db", padding: 12 }}
            />
          </label>
        </div>
        <button
          onClick={createTask}
          disabled={isCreating}
          style={{ marginTop: 16, background: "#2563eb", color: "#fff", border: 0, borderRadius: 999, padding: "12px 18px", cursor: "pointer", opacity: isCreating ? 0.7 : 1 }}
        >
          {isCreating ? "创建中..." : "创建任务"}
        </button>
        {error ? <p style={{ color: "#b91c1c", marginTop: 12 }}>{error}</p> : null}
      </div>

      <InterruptManager taskId={createdTaskId} />

      <section style={{ display: "grid", gap: 12 }}>
        <h2 style={{ marginBottom: 0 }}>历史任务</h2>
        <TaskList refreshKey={refreshKey} />
      </section>
    </section>
  );
}
