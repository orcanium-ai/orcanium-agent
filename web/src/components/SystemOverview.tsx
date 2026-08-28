import React from "react";
import { Cpu, Server, HardDrive } from "lucide-react";

export const SystemOverview: React.FC = () => {
  return (
    <div className="bg-stone-100/80 dark:bg-zinc-800/50 p-6 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50 flex flex-col h-full">
      <div className="flex items-center space-x-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50">
        <Server className="w-5 h-5 text-blue-500 dark:text-blue-400" />
        <h3 className="font-semibold text-sm text-zinc-800 dark:text-zinc-100">
          System Overview &amp; Daemon Health
        </h3>
      </div>

      <div className="flex-1 mt-4 space-y-5">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-zinc-600 dark:text-neutral-300">
            <span className="flex items-center space-x-1.5">
              <Cpu className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" />
              <span>Daemon CPU Allocation</span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 font-semibold">
              12.4%
            </span>
          </div>
          <div className="h-2 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: "12.4%" }}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-zinc-600 dark:text-neutral-300">
            <span className="flex items-center space-x-1.5">
              <HardDrive className="w-3.5 h-3.5 text-purple-500 dark:text-purple-400" />
              <span>Dynamic Memory Buffer</span>
            </span>
            <span className="text-purple-600 dark:text-purple-400 font-semibold">
              421 MB / 4 GB
            </span>
          </div>
          <div className="h-2 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full"
              style={{ width: "10%" }}
            />
          </div>
        </div>

        <div className="pt-4 border-t border-zinc-200/60 dark:border-zinc-700/50 grid grid-cols-2 gap-4 text-xs font-medium">
          <div className="bg-stone-100 dark:bg-zinc-800 p-2.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 flex flex-col justify-between">
            <span className="text-[10px] text-neutral-300">Node Status</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold mt-1">
              Daemon Online
            </span>
          </div>
          <div className="bg-stone-100 dark:bg-zinc-800 p-2.5 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 flex flex-col justify-between">
            <span className="text-[10px] text-neutral-300">WebSocket Buffer</span>
            <span className="text-zinc-700 dark:text-zinc-300 font-semibold mt-1">
              0 ms latency
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
