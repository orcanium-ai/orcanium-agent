import React from "react";
import { LucideIcon } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  colorClass: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  label,
  value,
  icon: Icon,
  colorClass,
}) => {
  return (
    <div className="bg-stone-100/80 dark:bg-zinc-800/50 p-6 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50 flex items-center justify-between">
      <div>
        <p className="text-xs font-medium text-neutral-300">{label}</p>
        <h3 className="text-3xl font-bold text-zinc-800 dark:text-zinc-100 mt-1">
          {value}
        </h3>
      </div>
      <div className={`p-3 rounded-xl border ${colorClass}`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
};
