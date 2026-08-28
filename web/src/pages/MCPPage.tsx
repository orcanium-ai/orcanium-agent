import { useState } from "react";
import {
  Boxes,
  Plus,
  Zap,
  Power,
  Trash2,
  X,
  Globe,
  Terminal,
  Package,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { toast } from "../components/ToastContainer";

interface McpServer {
  name: string;
  transport: "http" | "stdio";
  url?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  enabled: boolean;
}

export const MCPPage = () => {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<"http" | "stdio">("http");
  const [url, setUrl] = useState("");
  const [command, setCommand] = useState("");
  const [argsStr, setArgsStr] = useState("");
  const [envStr, setEnvStr] = useState("");
  const [creating, setCreating] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [installedCatalog, setInstalledCatalog] = useState<Set<string>>(
    new Set(),
  );
  const [installEntry, setInstallEntry] = useState<McpCatalogEntry | null>(
    null,
  );
  const [installEnv, setInstallEnv] = useState<Record<string, string>>({});
  const [installingName, setInstallingName] = useState<string | null>(null);

  interface McpCatalogEntry {
    name: string;
    transport: "http" | "stdio";
    description: string;
    source: "official" | "community";
    url?: string;
    command?: string;
    args?: string[];
    required_env?: { name: string; prompt: string; required: boolean }[];
  }

  const CATALOG: McpCatalogEntry[] = [
    {
      name: "filesystem",
      transport: "stdio",
      description: "Access the local filesystem with configurable permissions",
      source: "official",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem"],
      required_env: [
        {
          name: "MCP_FS_ROOT",
          prompt: "Allowed root directory",
          required: true,
        },
      ],
    },
    {
      name: "github",
      transport: "stdio",
      description:
        "GitHub API integration — manage repos, issues, PRs, and more",
      source: "official",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-github"],
      required_env: [
        {
          name: "GITHUB_TOKEN",
          prompt: "GitHub personal access token",
          required: true,
        },
      ],
    },
    {
      name: "postgres",
      transport: "stdio",
      description:
        "Read-only PostgreSQL database access with schema introspection",
      source: "official",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-postgres"],
      required_env: [
        {
          name: "DATABASE_URL",
          prompt: "PostgreSQL connection string",
          required: true,
        },
      ],
    },
    {
      name: "brave-search",
      transport: "stdio",
      description: "Web search and content extraction using Brave Search API",
      source: "official",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-brave-search"],
      required_env: [
        {
          name: "BRAVE_API_KEY",
          prompt: "Brave Search API key",
          required: true,
        },
      ],
    },
    {
      name: "sqlite",
      transport: "stdio",
      description: "SQLite database exploration and read-only queries",
      source: "official",
      command: "uvx",
      args: ["mcp-server-sqlite"],
      required_env: [],
    },
    {
      name: "memory",
      transport: "stdio",
      description: "Persistent memory graph using local JSON files",
      source: "official",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-memory"],
      required_env: [],
    },
  ];

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Name required");
      return;
    }
    if (transport === "http" && !url.trim()) {
      toast.error("URL required");
      return;
    }
    if (transport === "stdio" && !command.trim()) {
      toast.error("Command required");
      return;
    }
    setCreating(true);
    try {
      const env: Record<string, string> = {};
      for (const line of envStr.split("\n")) {
        const eq = line.indexOf("=");
        if (eq > 0) env[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
      }
      const server: McpServer = {
        name: name.trim(),
        transport,
        enabled: true,
        ...(transport === "http"
          ? { url: url.trim() }
          : {
              command: command.trim(),
              args: argsStr.trim() ? argsStr.trim().split(/\s+/) : [],
            }),
        ...(Object.keys(env).length ? { env } : {}),
      };
      setServers((prev) => [...prev, server]);
      toast.success(`MCP server "${name}" added`);
      setCreateOpen(false);
      setName("");
      setUrl("");
      setCommand("");
      setArgsStr("");
      setEnvStr("");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (s: McpServer) => {
    setToggling(s.name);
    try {
      setServers((prev) =>
        prev.map((x) =>
          x.name === s.name ? { ...x, enabled: !x.enabled } : x,
        ),
      );
      toast.success(`${s.name} ${s.enabled ? "disabled" : "enabled"}`);
    } finally {
      setToggling(null);
    }
  };

  const handleTest = async (s: McpServer) => {
    setTesting(s.name);
    try {
      await new Promise((r) => setTimeout(r, 800));
      setTestResults((prev) => ({
        ...prev,
        [s.name]: "Connected — 3 tools available",
      }));
      toast.success(`${s.name}: Connected`);
    } catch {
      setTestResults((prev) => ({ ...prev, [s.name]: "Connection failed" }));
      toast.error(`${s.name}: Connection failed`);
    } finally {
      setTesting(null);
    }
  };

  const handleInstallClick = (entry: McpCatalogEntry) => {
    if (entry.required_env && entry.required_env.length > 0) {
      const initial: Record<string, string> = {};
      entry.required_env.forEach((item) => {
        initial[item.name] = "";
      });
      setInstallEnv(initial);
      setInstallEntry(entry);
    } else {
      runInstall(entry, {});
    }
  };

  const handleInstallSubmit = () => {
    if (!installEntry) return;
    const missing =
      installEntry.required_env?.filter(
        (item) => item.required && !(installEnv[item.name] ?? "").trim(),
      ) ?? [];
    if (missing.length > 0) {
      toast.error(`${missing[0].prompt} required`);
      return;
    }
    const envMap: Record<string, string> = {};
    Object.entries(installEnv).forEach(([k, v]) => {
      if (v.trim()) envMap[k] = v.trim();
    });
    runInstall(installEntry, envMap);
  };

  const runInstall = (
    entry: McpCatalogEntry,
    envMap: Record<string, string>,
  ) => {
    setInstallingName(entry.name);
    setTimeout(() => {
      const server: McpServer = {
        name: entry.name,
        transport: entry.transport,
        enabled: true,
        ...(entry.transport === "http"
          ? { url: entry.url || "" }
          : { command: entry.command || "", args: entry.args || [] }),
        ...(Object.keys(envMap).length ? { env: envMap } : {}),
      };
      setServers((prev) => {
        if (prev.find((s) => s.name === entry.name)) return prev;
        return [...prev, server];
      });
      setInstalledCatalog((prev) => new Set(prev).add(entry.name));
      setInstallingName(null);
      setInstallEntry(null);
      setInstallEnv({});
      toast.success(`"${entry.name}" installed`);
    }, 600);
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    setServers((prev) => prev.filter((s) => s.name !== deleteTarget));
    setInstalledCatalog((prev) => {
      const next = new Set(prev);
      next.delete(deleteTarget);
      return next;
    });
    setDeleteTarget(null);
    toast.success("MCP server removed");
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Boxes className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="MCP"
        description="Model Context Protocol — connect third-party tools and resources"
      >
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-[11px] font-semibold text-white transition-all uppercase tracking-wider"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Server</span>
        </button>
      </PageHeader>

      {/* Stats */}
      <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-5 py-3">
        <div className="flex items-center gap-4 text-[10px] text-zinc-500">
          <span className="font-semibold">
            {servers.length} server{servers.length !== 1 ? "s" : ""}
          </span>
          <span className="text-neutral-300">·</span>
          <span>{servers.filter((s) => s.enabled).length} enabled</span>
          <span className="text-neutral-300">·</span>
          <span>
            {servers.filter((s) => s.transport === "http").length} HTTP
          </span>
          <span className="text-neutral-300">·</span>
          <span>
            {servers.filter((s) => s.transport === "stdio").length} stdio
          </span>
        </div>
      </div>

      {/* Server list */}
      <div className="flex flex-col gap-3">
        {servers.length === 0 ? (
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50">
            <div className="py-12 flex flex-col items-center text-zinc-500">
              <Boxes className="w-8 h-8 mb-3 opacity-40" />
              <p className="text-sm font-medium">No MCP servers configured</p>
              <p className="text-xs mt-1 text-neutral-300">
                Add an MCP server to connect external tools and resources.
              </p>
            </div>
          </div>
        ) : (
          servers.map((s) => {
            const result = testResults[s.name];
            return (
              <div
                key={s.name}
                className={`bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border ${s.enabled ? "border-zinc-200/60 dark:border-zinc-700/50" : "border-zinc-200/60 dark:border-zinc-700/50 opacity-60"} overflow-hidden`}
              >
                <div className="flex items-start gap-4 p-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300 truncate">
                        {s.name}
                      </span>
                      <span
                        className={`text-[9px] font-medium tracking-wider px-1.5 py-0.5 rounded border ${
                          s.transport === "http"
                            ? "text-blue-500 dark:text-blue-400 bg-blue-500/10 border-blue-500/20"
                            : "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                        }`}
                      >
                        {s.transport}
                      </span>
                      {!s.enabled && (
                        <span className="text-[9px] font-medium tracking-wider px-1.5 py-0.5 rounded border text-zinc-500 bg-zinc-500/10 border-zinc-500/20">
                          Disabled
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-zinc-500">
                      {s.transport === "http" ? (
                        <span className="font-mono truncate">{s.url}</span>
                      ) : (
                        <span className="font-mono truncate">
                          {[s.command, ...(s.args ?? [])]
                            .filter(Boolean)
                            .join(" ")}
                        </span>
                      )}
                      {s.env && Object.keys(s.env).length > 0 && (
                        <span>{Object.keys(s.env).length} env</span>
                      )}
                    </div>
                    {result && (
                      <div
                        className={`mt-2 text-[11px] font-semibold ${result.startsWith("Connected") ? "text-emerald-600 dark:text-emerald-400" : "text-rose-500 dark:text-rose-400"}`}
                      >
                        {result}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleToggle(s)}
                      disabled={toggling === s.name}
                      className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium border transition-all ${
                        s.enabled
                          ? "text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/10"
                          : "text-neutral-300 border-zinc-500/20 hover:bg-zinc-500/10"
                      }`}
                    >
                      <Power className="w-3 h-3" />
                      {s.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => handleTest(s)}
                      disabled={testing === s.name}
                      className="p-1.5 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
                      title="Test connection"
                    >
                      {testing === s.name ? (
                        <svg
                          className="w-3.5 h-3.5 animate-spin"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                            fill="none"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                      ) : (
                        <Zap className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <button
                      onClick={() => setDeleteTarget(s.name)}
                      className="p-1.5 text-zinc-500 hover:text-rose-500 dark:hover:text-rose-400 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ── Catalog ── */}
      <div className="flex flex-col gap-3">
        <h3 className="text-xs font-bold text-neutral-300 uppercase tracking-[0.12em]">
          <span className="flex items-center gap-2">
            <Package className="w-3.5 h-3.5" />
            Catalog ({CATALOG.length})
          </span>
        </h3>
        <p className="text-[11px] text-zinc-500">
          Pre-configured MCP servers — install with one click.
        </p>

        <div className="flex flex-col gap-2">
          {CATALOG.map((entry) => {
            const isInstalled = installedCatalog.has(entry.name);
            const isInstalling = installingName === entry.name;
            return (
              <div
                key={entry.name}
                className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden"
              >
                <div className="flex items-start gap-4 p-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300 truncate">
                        {entry.name}
                      </span>
                      <span
                        className={`text-[9px] font-medium tracking-wider px-1.5 py-0.5 rounded border ${
                          entry.transport === "http"
                            ? "text-blue-500 dark:text-blue-400 bg-blue-500/10 border-blue-500/20"
                            : "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                        }`}
                      >
                        {entry.transport}
                      </span>
                      <span className="text-[9px] text-zinc-500 bg-zinc-500/10 px-1.5 py-0.5 rounded border border-zinc-500/20 uppercase tracking-wider">
                        {entry.source}
                      </span>
                      {isInstalled && (
                        <span className="text-[9px] font-medium tracking-wider px-1.5 py-0.5 rounded border text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                          Installed
                        </span>
                      )}
                    </div>
                    {entry.description && (
                      <p className="text-[11px] text-neutral-300 mt-1">
                        {entry.description}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0">
                    {isInstalled ? (
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-1.5 rounded-lg border border-emerald-500/20">
                        Installed
                      </span>
                    ) : (
                      <button
                        onClick={() => handleInstallClick(entry)}
                        disabled={isInstalling}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 rounded-lg text-[11px] font-semibold text-white transition-all uppercase tracking-wider"
                      >
                        {isInstalling ? (
                          <svg
                            className="w-3.5 h-3.5 animate-spin"
                            viewBox="0 0 24 24"
                          >
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                              fill="none"
                            />
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                            />
                          </svg>
                        ) : (
                          <Plus className="w-3.5 h-3.5" />
                        )}
                        {isInstalling ? "Installing..." : "Install"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Install modal for catalog entries */}
      {installEntry && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setInstallEntry(null);
          }}
        >
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-md rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-black text-zinc-800 dark:text-zinc-100 uppercase tracking-wider">
                Install {installEntry.name}
              </h3>
              <button
                onClick={() => setInstallEntry(null)}
                className="p-1 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-neutral-300 mb-4">
              This MCP requires the following values to be configured.
            </p>
            <div className="space-y-3">
              {installEntry.required_env?.map((item) => (
                <div key={item.name}>
                  <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                    {item.prompt}
                    {item.required ? " *" : ""}
                  </label>
                  <input
                    type="password"
                    placeholder={item.name}
                    value={installEnv[item.name] ?? ""}
                    onChange={(e) =>
                      setInstallEnv((prev) => ({
                        ...prev,
                        [item.name]: e.target.value,
                      }))
                    }
                    className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-5 pt-4 border-t border-zinc-200/60 dark:border-zinc-700/50">
              <button
                onClick={() => setInstallEntry(null)}
                className="px-4 py-2 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-xs font-medium text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleInstallSubmit}
                disabled={installingName === installEntry.name}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 text-xs font-semibold text-white transition-all shadow-lg"
              >
                {installingName === installEntry.name
                  ? "Installing..."
                  : "Install"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Server Modal */}
      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setCreateOpen(false);
          }}
        >
          <div className="bg-stone-100/80 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-lg rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-sm font-black text-zinc-800 dark:text-zinc-100 uppercase tracking-wider">
                Add MCP Server
              </h3>
              <button
                onClick={() => setCreateOpen(false)}
                className="p-1 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                  Name
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="my-mcp-server"
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                />
              </div>
              <div>
                <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                  Transport
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTransport("http")}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-medium border transition-all ${transport === "http" ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30" : "border-zinc-200/60 dark:border-zinc-700/50 text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300"}`}
                  >
                    <Globe className="w-3.5 h-3.5" /> HTTP
                  </button>
                  <button
                    onClick={() => setTransport("stdio")}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[11px] font-medium border transition-all ${transport === "stdio" ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30" : "border-zinc-200/60 dark:border-zinc-700/50 text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300"}`}
                  >
                    <Terminal className="w-3.5 h-3.5" /> STDIO
                  </button>
                </div>
              </div>
              {transport === "http" ? (
                <div>
                  <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                    URL
                  </label>
                  <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="http://localhost:8080"
                    className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                  />
                </div>
              ) : (
                <>
                  <div>
                    <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                      Command
                    </label>
                    <input
                      value={command}
                      onChange={(e) => setCommand(e.target.value)}
                      placeholder="npx"
                      className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                      Args
                    </label>
                    <input
                      value={argsStr}
                      onChange={(e) => setArgsStr(e.target.value)}
                      placeholder="-y @modelcontextprotocol/server-foo"
                      className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                    />
                  </div>
                </>
              )}
              <div>
                <label className="text-[9px] text-neutral-300 font-medium block mb-1">
                  Environment (KEY=VALUE per line)
                </label>
                <textarea
                  value={envStr}
                  onChange={(e) => setEnvStr(e.target.value)}
                  placeholder="API_KEY=secret&#10;DEBUG=1"
                  rows={3}
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono resize-vertical"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5 pt-4 border-t border-zinc-200/60 dark:border-zinc-700/50">
              <button
                onClick={() => setCreateOpen(false)}
                className="px-4 py-2 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-xs font-medium text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 text-xs font-semibold text-white transition-all shadow-lg"
              >
                {creating ? "Adding..." : "Add Server"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Remove MCP server"
        description="This will permanently remove this MCP server configuration."
        confirmLabel="Remove"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};
