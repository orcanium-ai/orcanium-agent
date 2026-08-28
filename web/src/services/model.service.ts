import { API_BASE } from "./api";

export interface ProviderProfileModel {
  id: string;
  name: string;
}

export const modelService = {
  /** GET /api/v1/models/{providerId}/models — discover models for a provider */
  listByProvider: async (
    providerId: string,
  ): Promise<{ provider_id: string; provider_name: string; models: { id: string; name: string }[] } | null> => {
    try {
      const res = await fetch(`${API_BASE}/models/${providerId}/models`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },
};
