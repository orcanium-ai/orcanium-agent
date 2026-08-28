import { API_BASE } from "./api";

//Helpers
const rootBase = () => API_BASE.replace("/api/v1", "");

/**
 * Safe fetch wrapper — returns the parsed JSON on success, or null
 * if the backend is unreachable or returns a non-OK status.
 */
async function tryFetch<T>(
  input: RequestInfo,
  init?: RequestInit,
): Promise<T | null> {
  try {
    const res = await fetch(input, init);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

//Types (only what the backend actually returns)

export interface RootStatus {
  status: string;
  system: string;
  docs_url: string;
}

// Shape returned by GET /api/v1/system/stats
export interface SystemStats {
  host: {
    hostname: string;
    os: string;
    arch: string;
    python: string;
  };
  cpu: {
    cores: number;
    load_avg: { "1m": number; "5m": number; "15m": number };
    usage_pct: number;
  };
  memory: {
    total_bytes: number;
    available_bytes: number;
    used_bytes: number;
    usage_pct: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    usage_pct: number;
  };
  uptime: string;
}

//Shape returned by GET /api/v1/gateways/
export interface GatewayChannel {
  id: string;
  platform: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

// Shape returned by GET /api/v1/keys/
export interface ProviderEntry {
  provider_id: string;
  provider_name: string;
  type: string;
  env_var: string;
  configured: boolean;
  masked_value: string;
  enabled: boolean;
  status: string;
  last_checked: string | null;
}

// Shape returned by GET /api/v1/config/
export interface AppConfig {
  version?: string;
  settings?: Record<string, unknown>;
  model_providers?: Record<string, Record<string, string>>;
  [key: string]: unknown;
}

//Service
export const systemService = {
  /** GET /api/v1/system/stats — real host, CPU, memory, disk, uptime */
  getSystemStats: (): Promise<SystemStats | null> =>
    tryFetch<SystemStats>(`${API_BASE}/system/stats`),

  /** GET / – backend root status */
  getStatus: (): Promise<RootStatus | null> =>
    tryFetch<RootStatus>(`${rootBase()}/`),

  /** GET /api/v1/gateways/ – list gateway channels */
  getGateways: (): Promise<GatewayChannel[] | null> =>
    tryFetch<GatewayChannel[]>(`${API_BASE}/gateways/`),

  /** POST /api/v1/gateways/{id}/toggle – enable/disable a gateway */
  toggleGateway: (channelId: string, enabled: boolean) =>
    tryFetch<{ status: string }>(
      `${API_BASE}/gateways/${channelId}/toggle?enabled=${enabled}`,
      { method: "POST" },
    ),

  /** GET /api/v1/keys/ – list provider keys */
  getProviders: (): Promise<ProviderEntry[] | null> =>
    tryFetch<ProviderEntry[]>(`${API_BASE}/keys/`),

  /** POST /api/v1/keys/{provider_id} – save a provider key */
  saveProviderKey: (providerId: string, value: string) =>
    tryFetch<{ status: string }>(`${API_BASE}/keys/${providerId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    }),

  /** GET /api/v1/config/ – full app config */
  getConfig: (): Promise<AppConfig | null> =>
    tryFetch<AppConfig>(`${API_BASE}/config/`),

  /** POST /api/v1/config/reload – reload runtime config */
  reloadConfig: () =>
    tryFetch<{ status: string }>(`${API_BASE}/config/reload`, {
      method: "POST",
    }),

  /** GET /api/v1/logs/ – system logs */
  getLogs: (lines = 45) =>
    tryFetch<{ logs: string }>(`${API_BASE}/logs/?lines=${lines}`),
};
