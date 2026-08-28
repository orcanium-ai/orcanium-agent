import { API_BASE } from "./api";

export interface Skill {
  id: string;
  title: string;
  description: string;
  workflow: string;
  examples: string;
  state: "ACTIVE" | "DORMANT";
  created_at?: string;
  updated_at?: string;
  last_used?: string;
  use_count: number;
  importance: number;
  executable: boolean;
}

export interface SkillListResponse {
  agent: string;
  skills: Skill[];
}

export interface HubSearchResult {
  query: string;
  results: any[];
  total: number;
}

export const skillService = {
  /** List all skills for an agent. */
  list: async (agent: string): Promise<SkillListResponse> => {
    const res = await fetch(`${API_BASE}/skills/?agent=${encodeURIComponent(agent)}`);
    if (!res.ok) throw new Error("Failed to fetch skills");
    return res.json();
  },

  /** Create a new skill. */
  create: async (agent: string, data: { title: string; description?: string; workflow?: string; examples?: string; executable?: boolean }) => {
    const params = new URLSearchParams({ agent, title: data.title });
    if (data.description) params.set("description", data.description);
    if (data.workflow) params.set("workflow", data.workflow);
    if (data.examples) params.set("examples", data.examples);
    if (data.executable) params.set("executable", "true");
    const res = await fetch(`${API_BASE}/skills/?${params}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create skill");
    return res.json();
  },

  /** Update a skill. */
  update: async (agent: string, skillId: string, data: Partial<Skill>) => {
    const params = new URLSearchParams({ agent });
    if (data.title) params.set("title", data.title);
    if (data.description) params.set("description", data.description);
    if (data.state) params.set("state", data.state);
    const res = await fetch(`${API_BASE}/skills/${encodeURIComponent(skillId)}?${params}`, { method: "PUT" });
    if (!res.ok) throw new Error("Failed to update skill");
    return res.json();
  },

  /** Delete a skill. */
  remove: async (agent: string, skillId: string) => {
    const res = await fetch(`${API_BASE}/skills/${encodeURIComponent(skillId)}?agent=${encodeURIComponent(agent)}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete skill");
    return res.json();
  },

  /** Toggle skill enabled/disabled. */
  toggle: async (agent: string, skillId: string, enabled: boolean) => {
    const res = await fetch(`${API_BASE}/skills/toggle?agent=${encodeURIComponent(agent)}&skill_id=${encodeURIComponent(skillId)}&enabled=${enabled}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to toggle skill");
    return res.json();
  },

  /** Search skill registries. */
  searchHub: async (query: string, limit = 20): Promise<HubSearchResult> => {
    const res = await fetch(`${API_BASE}/skills/hub/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    if (!res.ok) throw new Error("Failed to search hub");
    return res.json();
  },

  /** Install a skill from the hub. */
  installFromHub: async (identifier: string, agent: string) => {
    const res = await fetch(`${API_BASE}/skills/hub/install?identifier=${encodeURIComponent(identifier)}&agent=${encodeURIComponent(agent)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to install skill");
    return res.json();
  },
};
