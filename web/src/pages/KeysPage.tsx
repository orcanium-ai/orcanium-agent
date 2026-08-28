import { useState, useMemo } from "react";
import {
  KeyRound,
  Eye,
  EyeOff,
  Pencil,
  Trash2,
  Save,
  X,
  Zap,
  ShieldCheck,
  ShieldOff,
  Search,
  Wrench,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { toast } from "../components/ToastContainer";
import { useProviders } from "../hooks/useProviders";
import { providerService } from "../services/provider.service";
import type { ModelProvider } from "../types/model";

const PROVIDER_GROUPS: { prefix: string; name: string; priority: number }[] = [
  { prefix: "OPENAI_", name: "OpenAI", priority: 0 },
  { prefix: "ANTHROPIC_", name: "Anthropic", priority: 1 },
  { prefix: "GOOGLE_", name: "Gemini", priority: 2 },
  { prefix: "GEMINI_", name: "Gemini", priority: 2 },
  { prefix: "OPENROUTER_", name: "OpenRouter", priority: 3 },
  { prefix: "DEEPSEEK_", name: "DeepSeek", priority: 4 },
  { prefix: "GROQ_", name: "Groq Cloud", priority: 5 },
  { prefix: "TOGETHER_", name: "Together AI", priority: 6 },
  { prefix: "FIREWORKS_", name: "Fireworks AI", priority: 7 },
  { prefix: "OLLAMA_", name: "Ollama", priority: 8 },
  { prefix: "GROK_", name: "xAI Grok", priority: 9 },
  { prefix: "QWEN_", name: "Alibaba Qwen", priority: 10 },
  { prefix: "CLAUDE_", name: "Claude Code", priority: 11 },
  { prefix: "LMSTUDIO_", name: "LM Studio", priority: 12 },
];

function getProviderGroup(envVar: string): string {
  for (const g of PROVIDER_GROUPS) {
    if (envVar.startsWith(g.prefix)) return g.name;
  }
  return "Other";
}

const OAUTH_PROVIDERS = [
  { id: "openai", name: "OpenAI" },
  { id: "anthropic", name: "Anthropic" },
  { id: "gemini", name: "Google Gemini" },
  { id: "openrouter", name: "OpenRouter" },
  { id: "grok", name: "xAI Grok" },
  { id: "qwen", name: "Alibaba Qwen" },
  { id: "claudecode", name: "Claude Code" },
];

const ENV_DESCRIPTIONS: Record<string, string> = {
  OPENAI_API_KEY: "OpenAI API key for GPT models",
  ANTHROPIC_API_KEY: "Anthropic API key for Claude models",
  GEMINI_API_KEY: "Google Gemini API key",
  OPENROUTER_API_KEY: "OpenRouter API key for multi-model access",
  GROQ_API_KEY: "Groq Cloud API key for fast inference",
  DEEPSEEK_API_KEY: "DeepSeek API key",
  TOGETHER_API_KEY: "Together AI API key",
  FIREWORKS_API_KEY: "Fireworks AI API key",
  OLLAMA_BASE_URL: "Ollama server base URL (local)",
  LMSTUDIO_BASE_URL: "LM Studio server base URL (local)",
  GROK_API_KEY: "xAI Grok API key",
  QWEN_API_KEY: "Alibaba Qwen API key",
  CLAUDE_CODE_KEY: "Claude Code credential key",
};

const TOOL_ENV_VARS = [
  {
    key: "SEARXNG_URL",
    description: "URL of your SearXNG instance for self-hosted web search",
    category: "web_search",
  },
  {
    key: "BRAVE_API_KEY",
    description: "Brave Search API key for web search capability",
    category: "web_search",
  },
];

const GATEWAY_ENV_VARS = [
  {
    key: "GATEWAY_ALLOW_ALL_USERS",
    description: "Allow all users to interact with messaging bots (true/false)",
    category: "Gateway",
  },
  {
    key: "GATEWAY_PROXY_URL",
    description:
      "URL of a remote API server to forward messages to (proxy mode)",
    category: "Gateway",
  },
  {
    key: "GATEWAY_PROXY_KEY",
    description: "Bearer token for authenticating with the remote API server",
    category: "Gateway",
  },
  {
    key: "SUDO_PASSWORD",
    description: "Sudo password for privileged operations",
    category: "Gateway",
  },
  {
    key: "ORCANIUM_SIMPLEX_TEXT_BATCH_DELAY",
    description: "Quiet-period seconds for inbound text batching",
    category: "Gateway",
  },
];

export const KeysPage = () => {
  const { providers, isLoading, refetch } = useProviders();

  const [expandedTools, setExpandedTools] = useState(false);
  const [expandedGateway, setExpandedGateway] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [clearTarget, setClearTarget] = useState<string | null>(null);
  const [showAllOauth, setShowAllOauth] = useState(false);
  const [search, setSearch] = useState("");

  const groups = useMemo(() => {
    const map = new Map<string, ModelProvider[]>();
    for (const p of providers) {
      const group = getProviderGroup(p.env_var);
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(p);
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => {
        const ai = PROVIDER_GROUPS.findIndex((g) => g.name === a);
        const bi = PROVIDER_GROUPS.findIndex((g) => g.name === b);
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
      })
      .map(([name, entries]) => ({
        name,
        entries,
        configuredCount: entries.filter((p) => p.configured).length,
        hasAnyConfigured: entries.some((p) => p.configured),
        totalKeys: entries.length,
      }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providers]);

  const configuredTotal = providers.filter((p) => p.configured).length;

  const handleSave = async (providerId: string, envVar: string) => {
    const value = edits[providerId];
    if (!value) return;
    setSaving(providerId);
    try {
      await providerService.save(providerId, { value });
      setEdits((prev) => {
        const n = { ...prev };
        delete n[providerId];
        return n;
      });
      setRevealed((prev) => {
        const n = { ...prev };
        delete n[providerId];
        return n;
      });
      toast.success(`${envVar} saved`);
      refetch();
    } catch {
      toast.error(`Failed to save ${envVar}`);
    } finally {
      setSaving(null);
    }
  };

  const handleClear = async () => {
    if (!clearTarget) return;
    setSaving(clearTarget);
    try {
      await providerService.save(clearTarget, { value: "" });
      setRevealed((prev) => {
        const n = { ...prev };
        delete n[clearTarget];
        return n;
      });
      toast.success("Value cleared");
      setClearTarget(null);
      refetch();
    } catch {
      toast.error("Failed to clear value");
    } finally {
      setSaving(null);
    }
  };

  const startEdit = (id: string) => setEdits((prev) => ({ ...prev, [id]: "" }));
  const cancelEdit = (id: string) =>
    setEdits((prev) => {
      const n = { ...prev };
      delete n[id];
      return n;
    });

  function renderEnvRow(
    providerId: string,
    envVar: string,
    maskedValue: string | undefined,
    isSet: boolean,
    desc: string,
    catBadge?: string,
  ) {
    const isEditing = edits[providerId] !== undefined;
    const isRevealed = !!revealed[providerId];
    const displayValue = isRevealed
      ? revealed[providerId]
      : maskedValue || "---";

    if (!isSet && !isEditing) {
      return (
        <div
          key={providerId}
          className="flex items-center justify-between gap-3 py-2"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[11px] font-mono text-zinc-700 dark:text-zinc-300">
              {envVar}
            </span>
            {catBadge && (
              <span className="text-[9px] text-zinc-500 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                {catBadge}
              </span>
            )}
            <span className="text-[10px] text-slate-600 truncate hidden sm:block">
              {desc}
            </span>
          </div>
          <button
            onClick={() => startEdit(providerId)}
            className="px-2.5 py-1 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
          >
            Set
          </button>
        </div>
      );
    }

    return (
      <div
        key={providerId}
        className="border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl p-3 space-y-2"
      >
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold text-zinc-700 dark:text-zinc-300">
              {envVar}
            </span>
            {catBadge && (
              <span className="text-[9px] text-zinc-500 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                {catBadge}
              </span>
            )}
            <span
              className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${isSet ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-zinc-500 bg-slate-500/10 border-slate-500/20"}`}
            >
              {isSet ? "Set" : "Not set"}
            </span>
          </div>
        </div>
        <p className="text-[10px] text-zinc-500">{desc}</p>
        {!isEditing ? (
          <div className="flex items-center gap-2">
            <div
              className={`flex-1 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg px-3 py-2 text-[11px] font-mono ${isRevealed ? "bg-stone-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 select-all" : "bg-stone-100/50 dark:bg-zinc-800/50 text-zinc-500"}`}
            >
              {isSet ? displayValue : "---"}
            </div>
            {isSet && (
              <button
                onClick={() =>
                  setRevealed((prev) =>
                    prev[providerId]
                      ? (() => {
                          const n = { ...prev };
                          delete n[providerId];
                          return n;
                        })()
                      : { ...prev, [providerId]: maskedValue || "********" },
                  )
                }
                className="p-1.5 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
                title={isRevealed ? "Hide" : "Reveal"}
              >
                {isRevealed ? (
                  <EyeOff className="w-3.5 h-3.5" />
                ) : (
                  <Eye className="w-3.5 h-3.5" />
                )}
              </button>
            )}
            <button
              onClick={() => startEdit(providerId)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
            >
              <Pencil className="w-3 h-3" /> {isSet ? "Replace" : "Set"}
            </button>
            {isSet && (
              <button
                onClick={() => setClearTarget(providerId)}
                className="p-1.5 text-zinc-500 hover:text-rose-400 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              autoFocus
              type="text"
              value={edits[providerId] || ""}
              onChange={(e) =>
                setEdits((prev) => ({ ...prev, [providerId]: e.target.value }))
              }
              placeholder={
                isSet ? `Replace ${maskedValue || "current"}` : "Enter value..."
              }
              className="flex-1 bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
            />
            <button
              onClick={() => handleSave(providerId, envVar)}
              disabled={saving === providerId || !edits[providerId]}
              className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 rounded-lg text-[10px] font-semibold text-white transition-all"
            >
              <Save className="w-3 h-3" />{" "}
              {saving === providerId ? "..." : "Save"}
            </button>
            <button
              onClick={() => cancelEdit(providerId)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-[10px] font-medium text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
            >
              <X className="w-3 h-3" /> Cancel
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<KeyRound className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Keys"
        description="Manage API keys and secrets stored in ~/.orcanium/.env"
      />

      <div className="flex items-center justify-between bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-5 py-3">
        <p className="text-[11px] text-neutral-300">
          {configuredTotal} of {providers.length} keys configured ·{" "}
          {groups.length} providers
        </p>
        <p className="text-[9px] text-slate-600">
          Changes are persisted to disk immediately.
        </p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
        <input
          type="text"
          placeholder="Search keys..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl pl-9 pr-8 py-2 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <KeyRound className="w-5 h-5 animate-spin text-neutral-300" />
        </div>
      ) : (
        <>
          {/* ── LLM Providers ── */}
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-200/60 dark:border-zinc-700/50">
              <div className="flex items-center gap-2 mb-0.5">
                <Zap className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  LLM Providers
                </span>
              </div>
              <p className="text-[10px] text-zinc-500">
                {configuredTotal} of {providers.length} providers configured
              </p>
            </div>
            <div className="px-4 py-3 space-y-3">
              {groups.flatMap((group) =>
                group.entries.map((p) =>
                  renderEnvRow(
                    p.provider_id,
                    p.env_var,
                    p.masked_value,
                    p.configured,
                    ENV_DESCRIPTIONS[p.env_var] || p.provider_name,
                  ),
                ),
              )}
            </div>
          </div>

          {/* ── OAuth ── */}
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-200/60 dark:border-zinc-700/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Provider Logins (OAuth)
                </span>
              </div>
              <span className="text-[10px] text-zinc-500">
                0 of {OAUTH_PROVIDERS.length} connected
              </span>
            </div>
            <div className="divide-y divide-[#1B253D]/50">
              {(showAllOauth
                ? OAUTH_PROVIDERS
                : OAUTH_PROVIDERS.slice(0, 3)
              ).map((oauth) => (
                <div
                  key={oauth.id}
                  className="flex items-center justify-between px-4 py-3"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <ShieldOff className="w-4 h-4 text-zinc-500 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
                        {oauth.name}
                      </span>
                      <p className="text-[9px] text-slate-600">Not connected</p>
                    </div>
                  </div>
                  <button className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 rounded-lg text-[10px] font-semibold text-white transition-all">
                    Login
                  </button>
                </div>
              ))}
              {OAUTH_PROVIDERS.length > 3 && (
                <button
                  onClick={() => setShowAllOauth(!showAllOauth)}
                  className="w-full px-4 py-2 text-[10px] font-bold text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors text-center"
                >
                  {showAllOauth
                    ? "Show less"
                    : `Show all ${OAUTH_PROVIDERS.length} providers`}
                </button>
              )}
            </div>
          </div>

          {/* ── TOOL KEYS ── */}
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-200/60 dark:border-zinc-700/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                  <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    TOOL KEYS
                  </span>
                </div>
                <button
                  onClick={() => setExpandedTools(!expandedTools)}
                  className="text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
                >
                  {expandedTools ? "Show less" : "Show more"}
                </button>
              </div>
            </div>
            <div className="px-4 py-3 space-y-2">
              {(expandedTools ? TOOL_ENV_VARS : TOOL_ENV_VARS.slice(0, 1)).map(
                (env) => (
                  <div key={env.key}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-mono font-bold text-zinc-700 dark:text-zinc-300">
                        {env.key}
                      </span>
                      <span className="text-[9px] text-zinc-500 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                        {env.category}
                      </span>
                    </div>
                    <p className="text-[10px] text-zinc-500 mb-2">
                      {env.description}
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg px-3 py-2 text-[11px] font-mono bg-stone-100/50 dark:bg-zinc-800/50 text-zinc-500">
                        ---
                      </div>
                      <button
                        onClick={() => startEdit(env.key)}
                        className="px-2.5 py-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
                      >
                        Set
                      </button>
                    </div>
                  </div>
                ),
              )}
            </div>
          </div>

          {/* ── GATEWAY ── */}
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-200/60 dark:border-zinc-700/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                  <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    GATEWAY
                  </span>
                </div>
                <button
                  onClick={() => setExpandedGateway(!expandedGateway)}
                  className="text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
                >
                  {expandedGateway ? "Show less" : "Show more"}
                </button>
              </div>
            </div>
            <div className="px-4 py-3 space-y-2">
              {(expandedGateway
                ? GATEWAY_ENV_VARS
                : GATEWAY_ENV_VARS.slice(0, 1)
              ).map((env) => (
                <div key={env.key}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-mono font-bold text-zinc-700 dark:text-zinc-300">
                      {env.key}
                    </span>
                    <span className="text-[9px] text-zinc-500 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                      {env.category}
                    </span>
                  </div>
                  <p className="text-[10px] text-zinc-500 mb-2">
                    {env.description}
                  </p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg px-3 py-2 text-[11px] font-mono bg-stone-100/50 dark:bg-zinc-800/50 text-zinc-500">
                      ---
                    </div>
                    <button
                      onClick={() => startEdit(env.key)}
                      className="px-2.5 py-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-[10px] font-bold text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
                    >
                      Set
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <ConfirmDialog
        open={clearTarget !== null}
        title="Clear credential"
        description="This will remove the API key from ~/.orcanium/.env."
        confirmLabel="Clear"
        destructive
        onConfirm={handleClear}
        onCancel={() => setClearTarget(null)}
      />
    </div>
  );
};

export default KeysPage;
