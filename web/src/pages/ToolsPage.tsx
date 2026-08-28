import { useState, useEffect } from "react";
import {
  Wrench,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { toolService, ToolInfo } from "../services/tool.service";

const CATEGORY_ICONS: Record<string, string> = {
  web: "🔍",
  browser: "🌐",
  terminal: "💻",
  file: "📁",
  code_execution: "⚡",
  vision: "👁️",
  video: "🎬",
  image_gen: "🎨",
  video_gen: "🎬",
  x_search: "🐦",
  moa: "🧠",
  tts: "🔊",
  skills: "📚",
  todo: "📋",
  memory: "💾",
  context_engine: "🧩",
  session_search: "🔎",
  clarify: "❓",
  delegation: "👥",
  cronjob: "⏰",
  messaging: "📨",
  homeassistant: "🏠",
  spotify: "🎵",
  discord: "💬",
  discord_admin: "🛡️",
  yuanbao: "🤖",
  computer_use: "🖱️",
};

const CATEGORY_ORDER = [
  "web", "browser", "terminal", "file", "code_execution",
  "vision", "video", "image_gen", "video_gen",
  "tts", "skills", "memory", "todo",
  "cronjob", "messaging", "delegation", "clarify",
  "moa", "x_search", "session_search", "context_engine",
  "homeassistant", "spotify", "discord", "discord_admin",
  "computer_use", "yuanbao",
];

function toolCategory(key: string): string {
  if (["web", "browser", "x_search"].includes(key)) return "web";
  if (["terminal", "code_execution", "file"].includes(key)) return "system";
  if (["vision", "video", "image_gen", "video_gen", "tts"].includes(key)) return "media";
  if (["skills", "memory", "todo", "cronjob", "messaging", "delegation", "clarify", "session_search", "context_engine"].includes(key)) return "productivity";
  if (["moa"].includes(key)) return "intelligence";
  if (["homeassistant", "spotify", "discord", "discord_admin", "computer_use", "yuanbao"].includes(key)) return "integrations";
  return "other";
}

const CATEGORY_LABELS: Record<string, string> = {
  web: "Web & Browser",
  system: "System & Code",
  media: "Media & Vision",
  productivity: "Productivity",
  intelligence: "Intelligence",
  integrations: "Integrations",
  other: "Other",
};

export const ToolsPage = () => {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<Set<string>>(new Set());
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const loadTools = async () => {
    setLoading(true);
    try {
      const data = await toolService.list();
      setTools(data.tools);
    } catch {
      toast.error("Failed to load tools");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTools();
  }, []);

  const categories = [...new Set(tools.map((t) => toolCategory(t.key)))].sort(
    (a, b) => (CATEGORY_LABELS[a] || a).localeCompare(CATEGORY_LABELS[b] || b),
  );
  const enabledCount = tools.filter((t) => t.enabled).length;

  const displayTools = activeCategory
    ? tools.filter((t) => toolCategory(t.key) === activeCategory)
    : tools;

  const handleToggle = async (key: string) => {
    if (toggling.has(key)) return;
    setToggling((prev) => new Set(prev).add(key));
    const tool = tools.find((t) => t.key === key);
    if (!tool) return;
    try {
      if (tool.enabled) {
        await toolService.disable([key]);
        toast.success(`${tool.name} disabled`);
      } else {
        await toolService.enable([key]);
        toast.success(`${tool.name} enabled`);
      }
      setTools((prev) =>
        prev.map((t) => (t.key === key ? { ...t, enabled: !t.enabled } : t)),
      );
    } catch {
      toast.error(`Failed to ${tool.enabled ? "disable" : "enable"} ${tool.name}`);
    } finally {
      setToggling((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
        <PageHeader
          icon={<Wrench className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
          title="Tools"
          description="Agent Tools Registry"
        />
        <div className="flex items-center justify-center py-16 text-zinc-500">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          <span className="text-sm">Loading tools...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Wrench className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Tools"
        description="Agent Tools Registry — enable or disable toolsets per platform"
      >
        <button
          onClick={loadTools}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 rounded-lg text-[11px] font-bold text-white transition-all uppercase"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </PageHeader>

      {/* Stats + category bar */}
      <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-[10px] text-zinc-500">
            <span className="font-semibold">
              {enabledCount}/{tools.length} enabled
            </span>
            <span className="text-slate-600">·</span>
            <span>{categories.length} categories</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap mt-3">
          <button
            onClick={() => setActiveCategory(null)}
            className={`text-[10px] font-medium px-2.5 py-1 rounded-lg border transition-all ${
              !activeCategory
                ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30"
                : "text-zinc-500 border-zinc-200/60 dark:border-zinc-700/50 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() =>
                setActiveCategory(activeCategory === cat ? null : cat)
              }
              className={`text-[10px] font-medium px-2.5 py-1 rounded-lg border transition-all ${
                activeCategory === cat
                  ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30"
                  : "text-zinc-500 border-zinc-200/60 dark:border-zinc-700/50 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              {CATEGORY_LABELS[cat] || cat}
            </button>
          ))}
        </div>
      </div>

      {tools.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50">
          <Wrench className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600 dark:text-neutral-300">
            No tools found
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            Run the setup wizard to configure your tools.
          </p>
        </div>
      ) : (
        <div className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {displayTools.map((tool) => {
            const emoji = CATEGORY_ICONS[tool.key] || "🔧";
            return (
              <div
                key={tool.key}
                className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors"
              >
                {/* Card Header */}
                <div className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{emoji}</span>
                        <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
                          {tool.name}
                        </span>
                        <span
                          className={`text-[9px] font-medium px-1.5 py-0.5 rounded border shrink-0 ${
                            tool.enabled
                              ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                              : "text-zinc-500 bg-slate-500/10 border-slate-500/20"
                          }`}
                        >
                          {tool.enabled ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[9px] text-zinc-500 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20 uppercase tracking-wider">
                          {toolCategory(tool.key)}
                        </span>
                        {tool.default_off && (
                          <span className="text-[9px] text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                            Off by default
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleToggle(tool.key)}
                      disabled={toggling.has(tool.key)}
                      className="shrink-0 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors disabled:opacity-50"
                      title={tool.enabled ? "Disable" : "Enable"}
                    >
                      {tool.enabled ? (
                        <ToggleRight className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <ToggleLeft className="w-5 h-5 text-zinc-500" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Card Body */}
                <div className="px-4 pb-3">
                  <p className="text-[11px] text-neutral-300 leading-relaxed">
                    {tool.description}
                  </p>
                </div>

                {/* Card Footer */}
                <div className="flex items-center justify-between border-t border-zinc-200/60 dark:border-zinc-700/50 px-4 py-2">
                  <span className="text-[9px] text-slate-600 font-mono uppercase tracking-wider">
                    {tool.default_off ? "Optional" : "Built-in"}
                  </span>
                  <span
                    className={`text-[9px] font-medium ${
                      tool.enabled
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-zinc-500"
                    }`}
                  >
                    {tool.enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ToolsPage;
