import { API_BASE } from "./api";
import { Agent } from "../types/agent";

export const agentService = {
  list: async (): Promise<Agent[]> => {
    const res = await fetch(`${API_BASE}/agents/`);
    if (!res.ok) throw new Error("Failed to fetch agents");
    return res.json();
  },

  create: async (data: {
    name: string;
    soul?: string;
    skills?: string;
    memory?: string;
    model_provider?: string;
    model_name?: string;
  }) => {
    const params = new URLSearchParams({ name: data.name });
    if (data.soul) params.set("soul", data.soul);
    if (data.skills) params.set("skills", data.skills);
    if (data.memory) params.set("memory", data.memory);
    if (data.model_provider) params.set("model_provider", data.model_provider);
    if (data.model_name) params.set("model_name", data.model_name);
    const res = await fetch(`${API_BASE}/agents/create?${params}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to create agent");
    return res.json();
  },

  delete: async (name: string) => {
    const res = await fetch(`${API_BASE}/agents/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete agent");
    return res.json();
  },

  updateStatus: async (name: string, action: string) => {
    const res = await fetch(`${API_BASE}/agents/${name}/${action}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Failed to ${action} agent`);
    return res.json();
  },

  getFiles: async (name: string) => {
    const res = await fetch(`${API_BASE}/agents/${name}/files`);
    if (!res.ok) throw new Error("Failed to fetch agent files");
    return res.json();
  },

  saveFiles: async (name: string, files: any) => {
    const res = await fetch(`${API_BASE}/agents/${name}/files`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(files),
    });
    if (!res.ok) throw new Error("Failed to save agent files");
    return res.json();
  },
};
