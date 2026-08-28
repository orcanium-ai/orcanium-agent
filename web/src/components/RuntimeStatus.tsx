import React from "react";
import { useAgents } from "../hooks/useAgents";
import { useTasks } from "../hooks/useTasks";
import { useGateways } from "../hooks/useGateways";

export const RuntimeStatus: React.FC = () => {
  const { agents } = useAgents();
  const { tasks } = useTasks();
  const { gateways } = useGateways();

  const activeAgentsCount = agents.filter((a) => a.status === "running").length;
  const telegramGateway = gateways.find((g) => g.platform === "telegram");
  const gatewayStatus = telegramGateway?.enabled ? "connected" : "disconnected";

  return (
    <div className="bg-stone-100/80 dark:bg-zinc-800/50 p-4 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 space-y-3">
      <h4 className="text-xs font-medium text-neutral-300">
        System Daemon Telemetry
      </h4>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-stone-100 dark:bg-zinc-800 p-3 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-center">
          <p className="text-[10px] font-medium text-neutral-300">Agents Active</p>
          <p className="text-xl font-bold text-zinc-800 dark:text-zinc-100 mt-1">
            {activeAgentsCount} / {agents.length}
          </p>
        </div>
        <div className="bg-stone-100 dark:bg-zinc-800 p-3 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-center">
          <p className="text-[10px] font-medium text-neutral-300">
            Scheduled Jobs
          </p>
          <p className="text-xl font-bold text-zinc-800 dark:text-zinc-100 mt-1">
            {tasks.length}
          </p>
        </div>
        <div className="bg-stone-100 dark:bg-zinc-800 p-3 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-center">
          <p className="text-[10px] font-medium text-neutral-300">
            Gateway Daemon
          </p>
          <p
            className={`text-xs font-bold mt-2 ${gatewayStatus === "connected" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-500 dark:text-rose-400"}`}
          >
            {gatewayStatus}
          </p>
        </div>
      </div>
    </div>
  );
};
