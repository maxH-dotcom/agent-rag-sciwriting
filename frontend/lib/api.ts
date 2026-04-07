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

export type SettingsPayload = {
  settings: Record<string, unknown>;
  available_models: string[];
  sandbox_config: {
    timeout_seconds: number;
    max_output_size: number;
    allowed_imports: string[];
  };
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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

export async function fetchSettings(): Promise<SettingsPayload> {
  const response = await fetch(`${API_BASE_URL}/settings`);
  if (!response.ok) {
    throw new Error(`配置加载失败: ${response.status}`);
  }
  return response.json();
}

export async function updateSettings(updates: Record<string, unknown>): Promise<SettingsPayload> {
  const response = await fetch(`${API_BASE_URL}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ updates }),
  });
  if (!response.ok) {
    throw new Error(`配置更新失败: ${response.status}`);
  }
  return response.json();
}
