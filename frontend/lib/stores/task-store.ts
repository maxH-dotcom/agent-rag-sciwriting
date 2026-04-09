import { create } from "zustand";
import type { TaskPayload } from "../api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

interface TaskState {
  tasks: TaskPayload[];
  currentTask: TaskPayload | null;
  isLoading: boolean;
  error: string | null;
  isPolling: boolean;
  pollingInterval: ReturnType<typeof setInterval> | null;
  streamStatus: "idle" | "connecting" | "live" | "fallback";
  streamError: string | null;
  eventSource: EventSource | null;

  // Actions
  fetchTasks(): Promise<void>;
  fetchTask(id: string): Promise<void>;
  createTask(payload: {
    task_type: string;
    user_query: string;
    data_files?: string[];
    paper_files?: string[];
  }): Promise<string>;
  continueTask(
    id: string,
    options?: {
      decision?: "approved" | "modified" | "rejected";
      payload?: Record<string, unknown>;
    },
  ): Promise<void>;
  abortTask(id: string): Promise<void>;
  connectStream(id: string): void;
  disconnectStream(): void;
  startPolling(id: string): void;
  stopPolling(): void;
  clearError(): void;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  currentTask: null,
  isLoading: false,
  error: null,
  isPolling: false,
  pollingInterval: null,
  streamStatus: "idle",
  streamError: null,
  eventSource: null,

  fetchTasks: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, { cache: "no-store" });
      if (!response.ok) throw new Error(`任务列表加载失败: ${response.status}`);
      const payload = await response.json();
      set({ tasks: payload.items || [], isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "任务列表加载失败",
        isLoading: false,
      });
    }
  },

  fetchTask: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${id}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`任务加载失败: ${response.status}`);
      const task: TaskPayload = await response.json();
      set({ currentTask: task, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "任务加载失败",
        isLoading: false,
      });
    }
  },

  createTask: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        let guidance = "";
        try {
          const cloned = await response.clone().json();
          if (cloned?.detail?.guidance) guidance = cloned.detail.guidance;
        } catch { /* ignore */ }
        throw new Error(guidance || `创建任务失败 (${response.status})`);
      }
      const data = await response.json();
      set((state) => ({
        tasks: [{ ...data, status: "pending" }, ...state.tasks],
        isLoading: false,
      }));
      return data.task_id;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "创建任务失败",
        isLoading: false,
      });
      throw err;
    }
  },

  continueTask: async (id, options) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${id}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: options?.decision ?? "approved",
          payload: options?.payload ?? { source: "frontend" },
        }),
      });
      if (!response.ok) throw new Error(`继续任务失败: ${response.status}`);
      const task: TaskPayload = await response.json();
      set({ currentTask: task, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "继续任务失败",
        isLoading: false,
      });
    }
  },

  abortTask: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${id}/abort`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "frontend_abort" }),
      });
      if (!response.ok) throw new Error(`终止任务失败: ${response.status}`);
      const task: TaskPayload = await response.json();
      set({ currentTask: task, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "终止任务失败",
        isLoading: false,
      });
    }
  },

  connectStream: (id: string) => {
    const { eventSource, disconnectStream, stopPolling, startPolling } = get();
    if (eventSource) disconnectStream();

    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      set({
        streamStatus: "fallback",
        streamError: "当前环境不支持实时连接，已切换为轮询。",
      });
      startPolling(id);
      return;
    }

    stopPolling();
    set({ streamStatus: "connecting", streamError: null });

    const source = new EventSource(`${API_BASE_URL}/tasks/${id}/stream`);

    source.addEventListener("task", (event) => {
      try {
        const task = JSON.parse(event.data) as TaskPayload;
        set({
          currentTask: task,
          streamStatus: ["done", "failed", "aborted", "error"].includes(task.status) ? "idle" : "live",
          streamError: null,
        });

        if (["done", "failed", "aborted", "error"].includes(task.status)) {
          source.close();
          set({ eventSource: null });
        }
      } catch {
        // Ignore malformed events and keep the connection alive.
      }
    });

    source.onopen = () => {
      stopPolling();
      set({ streamStatus: "live", streamError: null });
    };

    source.onerror = () => {
      source.close();
      set({
        eventSource: null,
        streamStatus: "fallback",
        streamError: "实时连接已断开，正在回退到轮询刷新。",
      });
      startPolling(id);
    };

    set({ eventSource: source });
  },

  disconnectStream: () => {
    const { eventSource } = get();
    if (eventSource) {
      eventSource.close();
    }
    set({ eventSource: null, streamStatus: "idle", streamError: null });
  },

  startPolling: (id: string) => {
    const { pollingInterval, stopPolling, eventSource } = get();
    if (pollingInterval) stopPolling();
    if (eventSource) {
      eventSource.close();
      set({ eventSource: null });
    }

    set({ isPolling: true, streamStatus: "fallback" });

    // Initial fetch
    get().fetchTask(id);

    const interval = setInterval(async () => {
      const { currentTask } = get();
      if (!currentTask) return;

      // Stop polling on terminal states
      if (["done", "failed", "aborted", "interrupted"].includes(currentTask.status)) {
        get().stopPolling();
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${id}`, { cache: "no-store" });
        if (!response.ok) return;
        const task: TaskPayload = await response.json();
        set({ currentTask: task });

        // Stop polling on terminal states
        if (["done", "failed", "aborted", "interrupted"].includes(task.status)) {
          get().stopPolling();
        }
      } catch { /* ignore polling errors */ }
    }, 3000);

    set({ pollingInterval: interval });
  },

  stopPolling: () => {
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    set({ pollingInterval: null, isPolling: false });
  },

  clearError: () => set({ error: null }),
}));
