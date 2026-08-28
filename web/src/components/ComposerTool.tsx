import React from "react";

interface Props {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

export function ToolButton({ active, onClick, icon, label }: Props) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left ${
        active
          ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-800 dark:text-zinc-200"
          : "text-zinc-500 dark:text-neutral-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
