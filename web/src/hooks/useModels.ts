import { useQuery } from "@tanstack/react-query";
import { modelService } from "../services/model.service";
import { useProviders } from "./useProviders";

/**
 * Fetches available models for a given provider.
 * Falls back to the provider's default model list if the API call fails.
 */
export const useModels = (providerId: string) => {
  const { providers } = useProviders();

  const provider = providers.find((p) => p.provider_id === providerId);

  const query = useQuery({
    queryKey: ["models", providerId],
    queryFn: async () => {
      const result = await modelService.listByProvider(providerId);
      if (result && result.models && result.models.length > 0) {
        return result.models.map((m) => m.name);
      }
      return [];
    },
    retry: 1,
    staleTime: 60_000, // 1 minute cache
    enabled: !!providerId,
  });

  return {
    models: query.data || [],
    isLoading: query.isLoading,
    providerName: provider?.provider_name || providerId,
  };
};

/**
 * Fallback default models keyed by provider_id.
 * Used when the model discovery endpoint is unreachable.
 */
const FALLBACK_DEFAULT_MODELS: Record<string, string> = {
  openai: "gpt-4o",
  anthropic: "claude-3-opus-20240229",
  gemini: "gemini-1.5-flash",
  google: "gemini-1.5-flash",
  openrouter: "meta-llama/llama-3-8b-instruct:free",
  deepseek: "deepseek-chat",
  groq: "llama3-8b-8192",
  together: "meta-llama/Llama-3-70b-chat-hf",
  fireworks: "accounts/fireworks/models/llama-v3p1-70b-instruct",
  ollama: "llama3",
  lmstudio: "local-model",
};

export const getDefaultModel = (providerId: string): string => {
  return FALLBACK_DEFAULT_MODELS[providerId] || "gpt-4o";
};
