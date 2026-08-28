import { API_BASE } from "./api";

export interface AppConfig {
  version?: string;
  settings?: {
    theme?: string;
    telemetry?: boolean;
    auto_backup?: boolean;
  };
  model_providers?: Record<string, Record<string, string>>;
  [key: string]: unknown;
}

export const configService = {
  get: async (): Promise<AppConfig> => {
    const res = await fetch(`${API_BASE}/config/`);
    if (!res.ok) throw new Error("Failed to fetch config");
    return res.json();
  },

  update: async (payload: Record<string, unknown>) => {
    const res = await fetch(`${API_BASE}/config/update`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update config");
    return res.json();
  },

  reload: async () => {
    const res = await fetch(`${API_BASE}/config/reload`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to reload config");
    return res.json();
  },

  // Legacy methods used by useRuntimeStatus
  getRaw: async (): Promise<{ yaml: string; path: string }> => {
    const res = await fetch(`${API_BASE}/config/raw`);
    if (!res.ok) throw new Error("Failed to fetch raw config");
    return res.json();
  },

  saveRaw: async (yaml: string) => {
    const res = await fetch(`${API_BASE}/config/raw`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml }),
    });
    if (!res.ok) throw new Error("Failed to save raw config");
    return res.json();
  },

  getSystemLogs: async (lines = 45) => {
    const res = await fetch(`${API_BASE}/logs/?lines=${lines}`);
    if (!res.ok) throw new Error("Failed to fetch system logs");
    return res.json();
  },

  restartGateway: () => {
    return Promise.resolve({
      success: true,
      message: "Gateway restart signal triggered!",
    });
  },

  updateOrcanium: () => {
    return Promise.resolve({
      success: true,
      message: "Checking for Orcanium OS updates...",
    });
  },
};
