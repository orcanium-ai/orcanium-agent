import { API_BASE } from "./api";
import { Message } from "../types/agent";

export interface SessionInfo {
  id: string;
  agent_name: string;
  title?: string;
  source?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  message_count?: number;
  model?: string;
  preview?: string;
}

export const sessionService = {
  list: async (agentName?: string): Promise<SessionInfo[]> => {
    const params = agentName
      ? `?agent_name=${encodeURIComponent(agentName)}`
      : "";
    const res = await fetch(`${API_BASE}/sessions/${params}`);
    if (!res.ok) throw new Error("Failed to fetch sessions");
    return res.json();
  },

  getMessages: async (sessionId: string): Promise<Message[]> => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error("Failed to fetch messages");
    return res.json();
  },

  delete: async (sessionId: string) => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete session");
    return res.json();
  },

  create: async (
    agentName: string,
    title?: string,
  ): Promise<{ status: string; session: SessionInfo }> => {
    const params = new URLSearchParams({ agent_name: agentName });
    if (title) params.set("title", title);
    const res = await fetch(`${API_BASE}/sessions/create?${params}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to create session");
    return res.json();
  },

  sendMessage: async (
    sessionId: string,
    agentName: string,
    message: string,
  ) => {
    const url = `${API_BASE}/sessions/${sessionId}/chat?agent_name=${encodeURIComponent(agentName)}&session_id=${encodeURIComponent(sessionId)}&message=${encodeURIComponent(message)}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  },
};
