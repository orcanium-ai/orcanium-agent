import { API_BASE } from "./api";
import { GatewayChannel } from "../types/gateway";

export const gatewayService = {
  list: async (): Promise<GatewayChannel[]> => {
    const res = await fetch(`${API_BASE}/gateways/`);
    if (!res.ok) throw new Error("Failed to fetch gateways");
    return res.json();
  },

  toggle: async (id: string, enabled: boolean) => {
    const res = await fetch(
      `${API_BASE}/gateways/${encodeURIComponent(id)}/toggle?enabled=${enabled}`,
      {
      method: "POST",
      },
    );
    if (!res.ok) throw new Error("Failed to toggle gateway");
    return res.json();
  },
};
