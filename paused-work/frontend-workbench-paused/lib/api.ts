import { API_BASE_URL } from "./config";

export type TaskPayload = {
  task_id: string;
  task_type: string;
  user_query: string;
  data_files?: string[];
  paper_files?: string[];
  status: string;
  current_node: string;
  next_action?: string | null;
  interrupt_reason?: string | null;
  interrupt_data?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
};

export async function fetchTask(taskId: string): Promise<TaskPayload> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`任务加载失败: ${response.status}`);
  }
  return response.json();
}

export async function fetchTasks(): Promise<TaskPayload[]> {
  const response = await fetch(`${API_BASE_URL}/tasks`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`任务列表加载失败: ${response.status}`);
  }
  const payload = await response.json();
  return payload.items || [];
}

