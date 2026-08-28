import { API_BASE } from "./api";

export interface MemoryEntry {
  id: string;
  category: string;
  content: string;
  importance?: number;
  confidence?: number;
  access_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface MemoryListResponse {
  agent: string;
  entries: MemoryEntry[];
  total: number;
}

export interface MemoryHealthResponse {
  agent: string;
  health: { score: number; [key: string]: any };
}

export const memoryService = {
  /** List memory entries for an agent. */
  list: async (agent: string): Promise<MemoryListResponse> => {
    const res = await fetch(`${API_BASE}/memory/?agent=${encodeURIComponent(agent)}`);
    if (!res.ok) throw new Error("Failed to fetch memory");
    return res.json();
  },

  /** List user profile entries for an agent. */
  listUser: async (agent: string): Promise<MemoryListResponse> => {
    const res = await fetch(`${API_BASE}/memory/user?agent=${encodeURIComponent(agent)}`);
    if (!res.ok) throw new Error("Failed to fetch user profile");
    return res.json();
  },

  /** Add a memory entry. */
  add: async (agent: string, content: string, category = "CONTEXT") => {
    const params = new URLSearchParams({ agent, content, category });
    const res = await fetch(`${API_BASE}/memory/?${params}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to add memory");
    return res.json();
  },

  /** Delete a memory entry. */
  remove: async (agent: string, entryId: string) => {
    const res = await fetch(`${API_BASE}/memory/${encodeURIComponent(entryId)}?agent=${encodeURIComponent(agent)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete memory");
    return res.json();
  },

  /** Get memory health score. */
  health: async (agent: string): Promise<MemoryHealthResponse> => {
    const res = await fetch(`${API_BASE}/memory/health?agent=${encodeURIComponent(agent)}`);
    if (!res.ok) throw new Error("Failed to fetch memory health");
    return res.json();
  },
};
