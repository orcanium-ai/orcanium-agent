import { useState } from "react";
import {
  Cpu,
  Wifi,
  WifiOff,
  RefreshCw,
  KeyRound,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { useProviders } from "../hooks/useProviders";
import { useModels } from "../hooks/useModels";

export const ModelsPage = () => {
  const { providers, isLoading, reloadConfig, refetch } = useProviders();
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  const total = providers.length;
  const configured = providers.filter((p) => p.configured).length;
  const active = providers.filter((p) => p.status === "active").length;
  const apiKeyProviders = providers.filter((p) => p.type === "provider").length;
  const oauthProviders = providers.filter((p) => p.type === "oauth").length;

  const handleReload = async () => {
    await reloadConfig();
    toast.success("Provider config reloaded");
    refetch();
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Cpu className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Models"
        description="Manage language model configurations and providers"
      >
        <button
          onClick={handleReload}
          disabled={isLoading}
          className="p-1.5 text-neutral-300 hover:text-zinc-800 dark:hover:text-zinc-100 hover:bg-stone-100 dark:hover:bg-zinc-800 rounded-lg border border-transparent hover:border-zinc-200/60 dark:hover:border-zinc-700/50 transition-all"
          title="Reload provider configuration"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
        </button>
      </PageHeader>

      {/* Two-column top section — stats card + summary */}
      <div className="grid min-w-0 gap-6 lg:grid-cols-2">
        {/* Stats card */}
        <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
          <div className="min-w-0 py-5 px-5">
            <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] gap-y-4">
              {/* Provider stats */}
              <div className="flex flex-col col-span-3">
                <span className="text-[10px] text-zinc-500 font-medium mb-1">
                  Model Providers
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="flex flex-col">
                    <span className="text-lg font-bold tabular-nums leading-none text-zinc-800 dark:text-zinc-100">
                      {total}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-medium mt-0.5">
                      Total
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold tabular-nums leading-none text-emerald-600 dark:text-emerald-400">
                      {active}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-medium mt-0.5">
                      Active
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold tabular-nums leading-none text-blue-500 dark:text-blue-400">
                      {configured}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-medium mt-0.5">
                      Configured
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold tabular-nums leading-none text-zinc-700 dark:text-zinc-300">
                      {total - configured}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-medium mt-0.5">
                      Unset
                    </span>
                  </div>
                </div>
              </div>

              {/* Auth method breakdown */}
              <div className="flex flex-col col-span-3 pt-3 border-t border-zinc-200/60 dark:border-zinc-700/50">
                <span className="text-[10px] text-zinc-500 font-medium mb-2">
                  Authentication
                </span>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold tabular-nums leading-none text-zinc-700 dark:text-zinc-300">
                      {apiKeyProviders}
                    </span>
                    <span className="text-[10px] text-zinc-500 mt-0.5">
                      API Key
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-bold tabular-nums leading-none text-zinc-700 dark:text-zinc-300">
                      {oauthProviders}
                    </span>
                    <span className="text-[10px] text-zinc-500 mt-0.5">
                      OAuth
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Config reload card */}
        <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-5 flex flex-col justify-center">
          <p className="text-xs text-neutral-300 leading-relaxed">
            Provider credentials are managed in the{" "}
            <a
              href="/keys"
              className="text-blue-500 dark:text-blue-400 hover:underline font-semibold"
            >
              Keys
            </a>{" "}
            page. Changes to{" "}
            <code className="text-[10px] text-zinc-500 font-mono bg-stone-100 dark:bg-zinc-800 px-1 py-0.5 rounded">
              ~/.orcanium/.env
            </code>{" "}
            are picked up after reloading the runtime configuration.
          </p>
          <button
            onClick={handleReload}
            disabled={isLoading}
            className="self-start mt-3 flex items-center gap-1.5 px-3 py-1.5 bg-stone-100 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-lg text-[11px] font-semibold border border-zinc-200/60 dark:border-zinc-700/50 transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            <span>Reload Runtime</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && providers.length === 0 ? (
        <div className="flex items-center justify-center py-24">
          <RefreshCw className="w-6 h-6 animate-spin text-neutral-300" />
        </div>
      ) : providers.length === 0 ? (
        <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50">
          <div className="py-12 flex flex-col items-center text-zinc-500">
            <Cpu className="w-8 h-8 mb-3 opacity-40" />
            <p className="text-sm font-medium">No providers found</p>
            <p className="text-xs mt-1 text-neutral-300">
              Configure API keys in the{" "}
              <a
                href="/keys"
                className="text-blue-500 dark:text-blue-400 hover:underline"
              >
                Keys
              </a>{" "}
              page to add providers.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {providers.map((p) => {
            const isActive = p.status === "active";
            const isConfigured = p.configured;
            return (
              <div
                key={p.provider_id}
                className={`bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border overflow-hidden ${
                  isActive
                    ? "border-emerald-200 dark:border-emerald-500/30"
                    : "border-zinc-200/60 dark:border-zinc-700/50"
                }`}
              >
                {/* Card Header */}
                <div className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Cpu
                          className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-emerald-600 dark:text-emerald-400" : isConfigured ? "text-blue-500 dark:text-blue-400" : "text-zinc-500"}`}
                        />
                        <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300 truncate">
                          {p.provider_name}
                        </span>
                        {isActive && (
                          <span className="inline-flex items-center gap-0.5 bg-emerald-100 dark:bg-emerald-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-600 dark:text-emerald-400">
                            active
                          </span>
                        )}
                        {!isActive && isConfigured && (
                          <span className="inline-flex items-center bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-amber-600 dark:text-amber-400">
                            inactive
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {p.env_var}
                        </span>
                        {p.type && (
                          <span className="text-[9px] text-neutral-300 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                            {p.type}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Body */}
                <div className="px-4 pb-2 space-y-3">
                  {p.masked_value ? (
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <KeyRound className="w-3 h-3 text-zinc-500" />
                      <span className="font-mono">{p.masked_value}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[10px] text-neutral-400">
                      <KeyRound className="w-3 h-3" />
                      <span className="italic">Not configured</span>
                    </div>
                  )}

                  {/* Show models toggle (only for configured providers) */}
                  {isConfigured && (
                    <button
                      onClick={() =>
                        setExpandedProvider(
                          expandedProvider === p.provider_id
                            ? null
                            : p.provider_id,
                        )
                      }
                      className="flex items-center gap-1 py-0.5 px-2 text-[10px] font-medium text-zinc-300 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-full bg-zinc-200 dark:bg-zinc-700/50 transition-colors"
                    >
                      {expandedProvider === p.provider_id ? (
                        <ChevronDown className="w-3 h-3" />
                      ) : (
                        <ChevronRight className="w-3 h-3" />
                      )}
                      <span>
                        {expandedProvider === p.provider_id
                          ? "Hide models"
                          : "Show models"}
                      </span>
                    </button>
                  )}
                </div>

                {/* Expandable model list */}
                {expandedProvider === p.provider_id && (
                  <ModelsList providerId={p.provider_id} />
                )}

                {/* Card Footer */}
                <div className="flex items-center justify-between text-[10px] text-zinc-400 border-t border-zinc-200/60 dark:border-zinc-700/50 px-4 py-2">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      {isActive ? (
                        <Wifi className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <WifiOff className="w-3 h-3 text-zinc-500" />
                      )}
                      {isActive ? "Connected" : "Disconnected"}
                    </span>
                  </div>
                  {p.last_checked && (
                    <span>{new Date(p.last_checked).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/* ── ModelsList — fetches and displays models for a provider ── */

function ModelsList({ providerId }: { providerId: string }) {
  const { models, isLoading } = useModels(providerId);

  return (
    <div className="border-t border-zinc-200/50 dark:border-zinc-700/50">
      {isLoading ? (
        <div className="flex items-center gap-2 px-4 py-3 text-[10px] text-zinc-400">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>Discovering models...</span>
        </div>
      ) : models.length > 0 ? (
        <div className="py-1">
          {models.map((m) => (
            <div
              key={m}
              className="flex items-center gap-2 px-4 py-1.5 text-[10px] text-zinc-400 font-mono hover:bg-zinc-100/50 dark:hover:bg-zinc-700/30 transition-colors"
            >
              <div className="w-1 h-1 rounded-full bg-zinc-400 shrink-0" />
              <span>{m}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="px-4 py-3 text-[10px] text-neutral-300 italic">
          No models discovered
        </div>
      )}
    </div>
  );
}

export default ModelsPage;
