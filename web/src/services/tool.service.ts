import { API_BASE } from "./api";

export interface ToolInfo {
  key: string;
  name: string;
  label: string;
  description: string;
  enabled: boolean;
  default_off: boolean;
}

export interface ToolListResponse {
  tools: ToolInfo[];
  platform: string;
}

export const toolService = {
  /** List all configurable tools with enabled/disabled status. */
  list: async (platform = "cli"): Promise<ToolListResponse> => {
    const res = await fetch(`${API_BASE}/tools/?platform=${platform}`);
    if (!res.ok) throw new Error("Failed to fetch tools");
    return res.json();
  },

  /** Enable one or more toolsets. */
  enable: async (tools: string[], platform = "cli") => {
    const res = await fetch(`${API_BASE}/tools/enable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, tools }),
    });
    if (!res.ok) throw new Error("Failed to enable tools");
    return res.json();
  },

  /** Disable one or more toolsets. */
  disable: async (tools: string[], platform = "cli") => {
    const res = await fetch(`${API_BASE}/tools/disable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, tools }),
    });
    if (!res.ok) throw new Error("Failed to disable tools");
    return res.json();
  },
};
