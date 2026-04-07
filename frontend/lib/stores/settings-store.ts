import { create } from "zustand";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface SettingsPayload {
  settings: Record<string, unknown>;
  available_models: string[];
  sandbox_config: {
    timeout_seconds: number;
    max_output_size: number;
    allowed_imports: string[];
  };
}

export interface ApiKeyStatus {
  openai: "connected" | "disconnected" | "error";
  groq: "connected" | "disconnected" | "error";
  anthropic: "connected" | "disconnected" | "error";
  zotero: "connected" | "disconnected" | "error";
}

interface SettingsState {
  settings: SettingsPayload | null;
  apiKeyStatus: ApiKeyStatus;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  message: { type: "success" | "error"; text: string } | null;

  // Form state
  preferredModel: string;
  sandboxTimeout: number;
  autoConvertYear: boolean;
  significanceLevel: string;
  maxLiteratureCount: number;
  dataEncoding: string;
  allowedPackages: string;

  // Actions
  fetchSettings(): Promise<void>;
  updateSettings(updates: Record<string, unknown>): Promise<void>;
  verifyApiKey(provider: keyof ApiKeyStatus, key: string): Promise<void>;
  setField<K extends keyof SettingsState>(key: K, value: SettingsState[K]): void;
  clearMessage(): void;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  apiKeyStatus: {
    openai: "disconnected",
    groq: "disconnected",
    anthropic: "disconnected",
    zotero: "disconnected",
  },
  isLoading: false,
  isSaving: false,
  error: null,
  message: null,

  // Form fields
  preferredModel: "auto",
  sandboxTimeout: 60,
  autoConvertYear: true,
  significanceLevel: "0.05",
  maxLiteratureCount: 20,
  dataEncoding: "UTF-8",
  allowedPackages: "pandas, numpy, scipy, statsmodels, sklearn, matplotlib",

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/settings`);
      if (!response.ok) throw new Error(`配置加载失败: ${response.status}`);
      const data: SettingsPayload = await response.json();
      set({
        settings: data,
        preferredModel: (data.settings.preferred_model as string) || "auto",
        sandboxTimeout: (data.settings.sandbox_timeout as number) || 60,
        autoConvertYear: data.settings.auto_convert_year_column !== false,
        significanceLevel: (data.settings.significance_level as string) || "0.05",
        maxLiteratureCount: (data.settings.max_literature_count as number) || 20,
        dataEncoding: (data.settings.data_encoding as string) || "UTF-8",
        allowedPackages: (data.settings.allowed_packages as string[])?.join(", ") || "pandas, numpy",
        isLoading: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "配置加载失败",
        isLoading: false,
      });
    }
  },

  updateSettings: async (updates: Record<string, unknown>) => {
    set({ isSaving: true, error: null, message: null });
    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      });
      if (!response.ok) throw new Error(`配置更新失败: ${response.status}`);
      const data: SettingsPayload = await response.json();
      set({
        settings: data,
        isSaving: false,
        message: { type: "success", text: "设置已保存" },
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "配置更新失败",
        isSaving: false,
        message: { type: "error", text: String(err) },
      });
    }
  },

  verifyApiKey: async (provider: keyof ApiKeyStatus, key: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/settings/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: key }),
      });
      const data = await response.json();
      set((state) => ({
        apiKeyStatus: {
          ...state.apiKeyStatus,
          [provider]: data.valid ? "connected" : "error",
        },
      }));
    } catch {
      set((state) => ({
        apiKeyStatus: {
          ...state.apiKeyStatus,
          [provider]: "error",
        },
      }));
    }
  },

  setField: (key, value) => set({ [key]: value } as Partial<SettingsState>),

  clearMessage: () => set({ message: null }),
}));
