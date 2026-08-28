import { API_BASE } from "./api";
import type { ModelProvider } from "../types/model";

export const providerService = {
  list: async (): Promise<ModelProvider[]> => {
    const res = await fetch(`${API_BASE}/keys/`);
    if (!res.ok) throw new Error("Failed to fetch providers");
    return res.json();
  },

  save: async (
    providerId: string,
    payload: { value?: string; enabled?: boolean },
  ) => {
    const res = await fetch(`${API_BASE}/keys/${providerId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to save provider config");
    return res.json();
  },

  testConnection: async (providerId: string) => {
    const res = await fetch(`${API_BASE}/keys/${providerId}/test`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to test connection");
    return res.json();
  },

  reload: async () => {
    const res = await fetch(`${API_BASE}/keys/reload`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to reload config");
    return res.json();
  },
};
