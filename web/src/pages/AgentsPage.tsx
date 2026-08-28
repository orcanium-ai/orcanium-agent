import { useState, useEffect } from "react";
import {
  Bot,
  Plus,
  MoreVertical,
  Play,
  Square,
  Trash2,
  Wifi,
  WifiOff,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { toast } from "../components/ToastContainer";
import { useAgents } from "../hooks/useAgents";
import { useProviders } from "../hooks/useProviders";
import { useModels, getDefaultModel } from "../hooks/useModels";
import type { Agent } from "../types/agent";

export const AgentsPage = () => {
  const { agents, isLoading, createAgent, updateStatus, deleteAgent } =
    useAgents();
  const { providers } = useProviders();
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newProvider, setNewProvider] = useState("openai");
  const [newModel, setNewModel] = useState("gpt-4o");
  const [newSoul, setNewSoul] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const { models: availableModels, isLoading: modelsLoading } =
    useModels(newProvider);

  // API-key providers only (exclude oauth)
  const apiProviders = providers.filter((p) => p.type === "provider");

  // When provider changes, pick a sensible default model
  useEffect(() => {
    setNewModel(getDefaultModel(newProvider));
  }, [newProvider]);

  // If we fetched models and the current model isn't in the list, pick first
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(newModel)) {
      setNewModel(availableModels[0]);
    }
  }, [availableModels, newModel]);

  const total = agents.length;
  const running = agents.filter((a) => a.status === "running").length;
  const stopped = agents.filter(
    (a) => a.status === "stopped" || a.status === "paused",
  ).length;

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createAgent({
        name: newName.trim(),
        provider: newProvider,
        model: newModel,
        soul: newSoul.trim() || undefined,
      });
      toast.success(`Agent "${newName}" created`);
      setCreateOpen(false);
      setNewName("");
      setNewSoul("");
    } catch {
      toast.error("Failed to create agent");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (agent: Agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    try {
      await updateStatus({ name: agent.name, action });
      toast.success(`${agent.name} ${action}ed`);
    } catch {
      toast.error(`Failed to ${action} agent`);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteAgent(deleteTarget);
      setDeleteTarget(null);
      toast.success("Agent removed");
    } catch {
      toast.error("Failed to remove agent");
    }
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Bot className="w-4 h-4 text-blue-400" />}
        title="Agents"
        description="Manage your agent nodes and runtime instances"
      >
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-[11px] font-bold text-white transition-all uppercase"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Create</span>
        </button>
      </PageHeader>

      {/* Stats bar */}
      <div className="flex items-center gap-x-6 bg-stone-100/80 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50 px-4 py-3 rounded-xl">
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-zinc-800 dark:text-zinc-100">
            {total}
          </span>
          <span className="text-[10px] font-medium text-neutral-300">
            Total
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-emerald-600 dark:text-emerald-400">
            {running}
          </span>
          <span className="text-[10px] font-medium text-neutral-300">
            Running
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-zinc-600 dark:text-zinc-300">
            {stopped}
          </span>
          <span className="text-[10px] font-medium text-neutral-300">
            Stopped
          </span>
        </div>
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-neutral-300">
          <span className="text-sm font-medium">Loading agents...</span>
        </div>
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50">
          <Bot className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600 dark:text-neutral-300">
            No agents registered
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            Create your first agent to get started.
          </p>
          <button
            onClick={() => setCreateOpen(true)}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition-all"
          >
            Create Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {agents.map((agent) => {
            const isRunning = agent.status === "running";
            return (
              <div
                key={agent.name}
                className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4 flex flex-col gap-3 hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors relative"
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`p-1.5 rounded-lg ${isRunning ? "bg-emerald-100 dark:bg-emerald-900/30" : "bg-zinc-100 dark:bg-zinc-800"}`}
                    >
                      <Bot
                        className={`w-4 h-4 ${isRunning ? "text-emerald-500 dark:text-emerald-400" : "text-neutral-300"}`}
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100 truncate">
                          {agent.name}
                        </span>
                        <span
                          className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${
                            isRunning
                              ? "text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-500/20"
                              : "text-neutral-300 bg-zinc-100 dark:bg-zinc-800 border-zinc-200/60 dark:border-zinc-700/50"
                          }`}
                        >
                          {agent.status}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-500 font-mono block mt-0.5">
                        {agent.model_name}
                      </span>
                    </div>
                  </div>

                  {/* Actions menu */}
                  <div className="relative shrink-0">
                    <button
                      onClick={() =>
                        setOpenMenu(openMenu === agent.name ? null : agent.name)
                      }
                      className="p-1 text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 rounded transition-colors"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    {openMenu === agent.name && (
                      <>
                        <div
                          className="fixed inset-0 z-10"
                          onClick={() => setOpenMenu(null)}
                        />
                        <div className="absolute right-0 top-full mt-1 z-20 bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl py-1 min-w-[140px] shadow-2xl">
                          <button
                            onClick={() => {
                              handleToggle(agent);
                              setOpenMenu(null);
                            }}
                            className="flex items-center gap-2.5 w-full px-3 py-2 text-[11px] font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors"
                          >
                            {isRunning ? (
                              <Square className="w-3.5 h-3.5 text-rose-500" />
                            ) : (
                              <Play className="w-3.5 h-3.5 text-emerald-500" />
                            )}
                            {isRunning ? "Stop" : "Start"}
                          </button>
                          <button
                            onClick={() => {
                              setDeleteTarget(agent.name);
                              setOpenMenu(null);
                            }}
                            className="flex items-center gap-2.5 w-full px-3 py-2 text-[11px] font-medium text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Details */}
                <div className="flex items-center gap-3 text-[10px] text-zinc-500">
                  <span className="flex items-center gap-1">
                    {isRunning ? (
                      <Wifi className="w-3 h-3 text-emerald-500" />
                    ) : (
                      <WifiOff className="w-3 h-3 text-neutral-300" />
                    )}
                    {agent.model_provider}
                  </span>
                  <span>·</span>
                  <span>{agent.active_sessions} sessions</span>
                  <span>·</span>
                  <span className="capitalize">{agent.health || "good"}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create modal */}
      {createOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setCreateOpen(false);
          }}
        >
          <div className="bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-md rounded-2xl p-6 shadow-2xl">
            <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-100 mb-1">
              New Agent
            </h3>
            <p className="text-[11px] text-zinc-500 mb-5">
              Create a new agent node with model and provider configuration.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-medium text-neutral-300 block mb-1">
                  Name
                </label>
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. ScraperAgent"
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
              </div>
              <div>
                <label className="text-[10px] font-medium text-neutral-300 block mb-1">
                  Provider
                </label>
                <select
                  value={newProvider}
                  onChange={(e) => setNewProvider(e.target.value)}
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                >
                  {apiProviders.map((p) => (
                    <option key={p.provider_id} value={p.provider_id}>
                      {p.provider_name} {p.configured ? "✓" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-neutral-300 block mb-1">
                  Model
                </label>
                {modelsLoading ? (
                  <div className="flex items-center gap-2 w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-500">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Loading models...</span>
                  </div>
                ) : availableModels.length > 0 ? (
                  <select
                    value={newModel}
                    onChange={(e) => setNewModel(e.target.value)}
                    className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                  >
                    {availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={newModel}
                    onChange={(e) => setNewModel(e.target.value)}
                    placeholder="e.g. gpt-4o"
                    className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                  />
                )}
              </div>
              <div>
                <label className="text-[10px] font-medium text-neutral-300 block mb-1">
                  SOUL.md
                </label>
                <textarea
                  value={newSoul}
                  onChange={(e) => setNewSoul(e.target.value)}
                  placeholder="Define the agent's core identity, purpose, and behavioral guidelines..."
                  rows={5}
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono resize-vertical"
                />
                <p className="text-[9px] text-zinc-500 mt-1">
                  Optional. The SOUL.md defines the agent's identity and core
                  behavior.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-zinc-200/60 dark:border-zinc-700/50">
              <button
                onClick={() => setCreateOpen(false)}
                className="px-4 py-2 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-xs font-medium text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || creating}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 text-xs font-semibold text-white transition-all shadow-lg"
              >
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete agent"
        description="This will stop and remove this agent node permanently."
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default AgentsPage;
