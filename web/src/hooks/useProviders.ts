import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { providerService } from "../services/provider.service";
import type { ModelProvider } from "../types/model";

const FALLBACK_PROVIDERS: ModelProvider[] = [
  {
    provider_id: "openai",
    provider_name: "OpenAI",
    type: "provider",
    env_var: "OPENAI_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "anthropic",
    provider_name: "Anthropic",
    type: "provider",
    env_var: "ANTHROPIC_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "gemini",
    provider_name: "Gemini",
    type: "provider",
    env_var: "GEMINI_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "google",
    provider_name: "Gemini",
    type: "provider",
    env_var: "GOOGLE_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "openrouter",
    provider_name: "OpenRouter",
    type: "provider",
    env_var: "OPENROUTER_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "deepseek",
    provider_name: "DeepSeek",
    type: "provider",
    env_var: "DEEPSEEK_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "groq",
    provider_name: "Groq Cloud",
    type: "provider",
    env_var: "GROQ_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "together",
    provider_name: "Together AI",
    type: "provider",
    env_var: "TOGETHER_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "fireworks",
    provider_name: "Fireworks AI",
    type: "provider",
    env_var: "FIREWORKS_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "ollama",
    provider_name: "Ollama",
    type: "provider",
    env_var: "OLLAMA_BASE_URL",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "lmstudio",
    provider_name: "LM Studio",
    type: "provider",
    env_var: "LMSTUDIO_BASE_URL",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "grok",
    provider_name: "xAI Grok",
    type: "oauth",
    env_var: "GROK_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "qwen",
    provider_name: "Alibaba Qwen",
    type: "oauth",
    env_var: "QWEN_API_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
  {
    provider_id: "claudecode",
    provider_name: "Claude Code",
    type: "oauth",
    env_var: "CLAUDE_CODE_KEY",
    configured: false,
    masked_value: "",
    enabled: true,
    status: "disconnected",
    last_checked: null,
  },
];

export const useProviders = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["providers"],
    queryFn: async () => {
      try {
        return await providerService.list();
      } catch {
        return FALLBACK_PROVIDERS;
      }
    },
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: ({
      providerId,
      value,
      enabled,
    }: {
      providerId: string;
      value?: string;
      enabled?: boolean;
    }) => providerService.save(providerId, { value, enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (providerId: string) =>
      providerService.testConnection(providerId),
  });

  const reloadMutation = useMutation({
    mutationFn: providerService.reload,
  });

  return {
    providers: query.data || FALLBACK_PROVIDERS,
    isLoading: query.isLoading,
    saveProvider: saveMutation.mutateAsync,
    testConnection: testMutation.mutateAsync,
    testResult: testMutation.data,
    isTesting: testMutation.isPending,
    reloadConfig: reloadMutation.mutateAsync,
    refetch: query.refetch,
  };
};
