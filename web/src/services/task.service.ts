import { API_BASE } from "./api";
import { ScheduledTask } from "../types/task";

export const taskService = {
  list: async (): Promise<ScheduledTask[]> => {
    const res = await fetch(`${API_BASE}/tasks/`);
    if (!res.ok) throw new Error("Failed to fetch tasks");
    return res.json();
  },

  create: async (data: {
    agent_name: string;
    cron_expr: string;
    job_type: string;
    payload?: Record<string, any>;
  }) => {
    const params = new URLSearchParams({
      agent_name: data.agent_name,
      cron_expr: data.cron_expr,
      job_type: data.job_type,
    });
    if (data.payload) params.set("payload", JSON.stringify(data.payload));
    const res = await fetch(`${API_BASE}/tasks/create?${params}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to create task");
    return res.json();
  },

  toggle: async (taskId: string, status: "active" | "paused") => {
    const res = await fetch(
      `${API_BASE}/tasks/${taskId}/toggle?status=${status}`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error("Failed to toggle task");
    return res.json();
  },

  delete: async (id: string) => {
    const res = await fetch(`${API_BASE}/tasks/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete task");
    return res.json();
  },
};
