import React from "react";
import { Plus, Key, Clock, FileText } from "lucide-react";
import { useUIStore } from "../stores/uiStore";

export const QuickActions: React.FC = () => {
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const setIsCreateAgentOpen = useUIStore((s) => s.setIsCreateAgentOpen);
  const setIsCreateTaskOpen = useUIStore((s) => s.setIsCreateTaskOpen);

  return (
    <div className="bg-stone-100/80 dark:bg-zinc-800/50 p-6 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50 flex flex-col h-full">
      <div className="flex items-center space-x-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50">
        <Plus className="w-5 h-5 text-amber-500 dark:text-amber-400" />
        <h3 className="font-semibold text-sm text-zinc-800 dark:text-zinc-100">
          Daemon Fast Tracks &amp; Actions
        </h3>
      </div>

      <div className="flex-1 mt-4 grid grid-cols-2 gap-3">
        <button
          onClick={() => setIsCreateAgentOpen(true)}
          className="bg-stone-100 dark:bg-zinc-800 hover:bg-blue-50 dark:hover:bg-blue-900/20 p-3.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-left transition-all hover:border-blue-300 dark:hover:border-blue-500/30 group flex flex-col justify-between"
        >
          <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-500 dark:text-blue-400 w-fit">
            <Plus className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] text-neutral-300 font-medium block mt-3">
              Agent Factory
            </span>
            <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mt-1 block group-hover:text-blue-600 dark:group-hover:text-blue-400">
              Instantiate Agent
            </span>
          </div>
        </button>

        <button
          onClick={() => setIsCreateTaskOpen(true)}
          className="bg-stone-100 dark:bg-zinc-800 hover:bg-amber-50 dark:hover:bg-amber-900/20 p-3.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-left transition-all hover:border-amber-300 dark:hover:border-amber-500/30 group flex flex-col justify-between"
        >
          <div className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-500 dark:text-amber-400 w-fit">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] text-neutral-300 font-medium block mt-3">
              Autonomy Daemon
            </span>
            <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mt-1 block group-hover:text-amber-600 dark:group-hover:text-amber-400">
              Schedule Task
            </span>
          </div>
        </button>

        <button
          onClick={() => setActiveTab("keys")}
          className="bg-stone-100 dark:bg-zinc-800 hover:bg-purple-50 dark:hover:bg-purple-900/20 p-3.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-left transition-all hover:border-purple-300 dark:hover:border-purple-500/30 group flex flex-col justify-between"
        >
          <div className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-900/30 text-purple-500 dark:text-purple-400 w-fit">
            <Key className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] text-neutral-300 font-medium block mt-3">
              Credentials Cabinet
            </span>
            <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mt-1 block group-hover:text-purple-600 dark:group-hover:text-purple-400">
              Manage LLM Keys
            </span>
          </div>
        </button>

        <button
          onClick={() => setActiveTab("documentation")}
          className="bg-stone-100 dark:bg-zinc-800 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 p-3.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-left transition-all hover:border-emerald-300 dark:hover:border-emerald-500/30 group flex flex-col justify-between"
        >
          <div className="p-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 dark:text-emerald-400 w-fit">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] text-neutral-300 font-medium block mt-3">
              Docs Vault
            </span>
            <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mt-1 block group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
              Read System Manual
            </span>
          </div>
        </button>
      </div>
    </div>
  );
};
