import { useState } from "react";
import { Clock, Play, Pause, Trash2, Plus, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { toast } from "../components/ToastContainer";
import { useTasks } from "../hooks/useTasks";
import { useAgents } from "../hooks/useAgents";
import type { ScheduledTask } from "../types/task";

function formatNextRun(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const now = Date.now();
  const diff = d.getTime() - now;
  if (diff < 0) return "Overdue";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `in ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `in ${hours}h`;
  return d.toLocaleDateString();
}

export const TasksPage = () => {
  const { tasks, isLoading, createTask, toggleTask, deleteTask } = useTasks();
  const { agents } = useAgents();

  const [createOpen, setCreateOpen] = useState(false);
  const [newAgent, setNewAgent] = useState("");
  const [newCron, setNewCron] = useState("0 * * * *");
  const [newType, setNewType] = useState("run_agent");
  const [creating, setCreating] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const total = tasks.length;
  const active = tasks.filter((t) => t.status === "active").length;
  const paused = tasks.filter((t) => t.status === "paused").length;
  const errored = tasks.filter((t) => t.status === "error").length;

  const handleCreate = async () => {
    if (!newAgent || !newCron || !newType) return;
    setCreating(true);
    try {
      await createTask({
        agent_name: newAgent,
        cron_expr: newCron,
        job_type: newType,
      });
      toast.success("Task created");
      setCreateOpen(false);
      setNewAgent("");
    } catch {
      toast.error("Failed to create task");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (task: ScheduledTask) => {
    const nextStatus = task.status === "active" ? "paused" : "active";
    try {
      await toggleTask({ taskId: task.id, status: nextStatus });
      toast.success(`Task ${nextStatus === "active" ? "resumed" : "paused"}`);
    } catch {
      toast.error("Failed to toggle task");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteTask(deleteTarget);
      toast.success("Task deleted");
      setDeleteTarget(null);
    } catch {
      toast.error("Failed to delete task");
    }
  };

  const STATUS_BADGE: Record<string, { color: string; label: string }> = {
    active: {
      color:
        "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      label: "Active",
    },
    scheduled: {
      color:
        "text-blue-500 dark:text-blue-400 bg-blue-500/10 border-blue-500/20",
      label: "Scheduled",
    },
    paused: {
      color:
        "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      label: "Paused",
    },
    error: {
      color:
        "text-rose-500 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      label: "Error",
    },
    completed: {
      color: "text-neutral-300 bg-slate-500/10 border-slate-500/20",
      label: "Done",
    },
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Clock className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Tasks"
        description="Automated cron scheduling and job management"
      >
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-[11px] font-semibold text-white transition-all uppercase tracking-wider"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Create</span>
        </button>
      </PageHeader>

      {/* Stats bar */}
      <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
        <div className="min-w-0 py-4 px-5">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="flex flex-col">
              <span className="text-lg font-bold tabular-nums leading-none text-zinc-800 dark:text-zinc-100">
                {total}
              </span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-0.5">
                Total
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tabular-nums leading-none text-emerald-600 dark:text-emerald-400">
                {active}
              </span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-0.5">
                Active
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tabular-nums leading-none text-amber-600 dark:text-amber-400">
                {paused}
              </span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-0.5">
                Paused
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tabular-nums leading-none text-rose-500 dark:text-rose-400">
                {errored}
              </span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mt-0.5">
                Error
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Loading */}
      {isLoading && tasks.length === 0 ? (
        <div className="flex items-center justify-center py-24">
          <RefreshCw className="w-6 h-6 animate-spin text-neutral-300" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50">
          <div className="py-12 flex flex-col items-center text-zinc-500">
            <Clock className="w-8 h-8 mb-3 opacity-40" />
            <p className="text-sm font-medium">No scheduled tasks</p>
            <p className="text-xs mt-1 text-neutral-300">
              Create a cron job to automate agent runs.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tasks.map((task) => {
            const badge = STATUS_BADGE[task.status] || STATUS_BADGE.error;
            return (
              <div
                key={task.id}
                className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden"
              >
                {/* Header */}
                <div className="p-4 pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 shrink-0 text-blue-500 dark:text-blue-400" />
                        <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300 truncate">
                          {task.job_type}
                        </span>
                        <span
                          className={`text-[9px] font-medium px-1.5 py-0.5 rounded border shrink-0 ${badge.color}`}
                        >
                          {badge.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <code className="text-[10px] text-zinc-500 font-mono bg-stone-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-200/60 dark:border-zinc-700/50">
                          {task.cron_expr}
                        </code>
                        <span className="text-[10px] text-neutral-300">→</span>
                        <span className="text-[10px] text-zinc-500">
                          {task.agent_name}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Body */}
                <div className="px-4 pb-3">
                  {task.next_run && (
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <Clock className="w-3 h-3" />
                      <span>Next: {formatNextRun(task.next_run)}</span>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between border-t border-zinc-200/60 dark:border-zinc-700/50 px-4 py-2">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleToggle(task)}
                      className="p-1 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded transition-colors"
                      title={task.status === "active" ? "Pause" : "Resume"}
                    >
                      {task.status === "active" ? (
                        <Pause className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                      ) : (
                        <Play className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      )}
                    </button>
                  </div>
                  <button
                    onClick={() => setDeleteTarget(task.id)}
                    className="p-1 text-zinc-500 hover:text-rose-500 dark:hover:text-rose-400 rounded transition-colors"
                    title="Delete task"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
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
            <h3 className="text-sm font-black text-zinc-800 dark:text-zinc-100 uppercase tracking-wider mb-1">
              New Task
            </h3>
            <p className="text-[11px] text-neutral-300 mb-5">
              Create a new scheduled cron job.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-[9px] text-neutral-300 font-extrabold uppercase block mb-1">
                  Agent
                </label>
                <select
                  value={newAgent}
                  onChange={(e) => setNewAgent(e.target.value)}
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                >
                  <option value="">Select an agent...</option>
                  {agents.map((a) => (
                    <option key={a.name} value={a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[9px] text-neutral-300 font-extrabold uppercase block mb-1">
                  Job Type
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                >
                  <option value="run_agent">Run Agent Reflection</option>
                  <option value="retrieve_news">Sync Knowledge</option>
                  <option value="sync_knowledge">Database Checkpoint</option>
                </select>
              </div>
              <div>
                <label className="text-[9px] text-neutral-300 font-extrabold uppercase block mb-1">
                  Cron Expression
                </label>
                <input
                  value={newCron}
                  onChange={(e) => setNewCron(e.target.value)}
                  placeholder="*/10 * * * *"
                  className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                />
                <p className="text-[9px] text-neutral-300 mt-1">
                  Standard 5-field cron notation.
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
                disabled={!newAgent || creating}
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
        title="Delete task"
        description="This will permanently remove this scheduled task."
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};

export default TasksPage;
