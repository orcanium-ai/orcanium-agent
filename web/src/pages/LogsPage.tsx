import { useState, useMemo } from "react";
import { Terminal, Filter } from "lucide-react";
import { useRuntimeStatus } from "../hooks/useRuntimeStatus";
import { PageHeader } from "../components/PageHeader";

const CATEGORIES = [
  { key: "agent", label: "agent", color: "text-blue-400" },
  { key: "gateway", label: "gateway", color: "text-emerald-400" },
  { key: "error", label: "error", color: "text-rose-400" },
] as const;

const LINE_OPTIONS = [50, 100, 200] as const;

export const LogsPage: React.FC = () => {
  const [category, setCategory] = useState<string>("agent");
  const [maxLines, setMaxLines] = useState<number>(100);
  const { logs } = useRuntimeStatus(maxLines * 3); // fetch enough raw data for filtering

  // Filter + truncate
  const filteredLogs = useMemo(() => {
    if (!logs) return "";
    const lines = logs.split("\n").filter((l) => {
      if (!l.trim()) return false;
      if (category === "error") {
        return /\[error\]|error|traceback|exception|failed|fail|unable/i.test(
          l,
        );
      }
      return l.toLowerCase().includes(`${category}`);
    });
    return lines.slice(-maxLines).join("\n");
  }, [logs, category, maxLines]);

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn flex-1 min-h-0">
      <PageHeader
        icon={<Terminal className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Live Daemon Console Logs"
        description="Orcanium daemon runtime logs"
      />

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Category pills */}
        <div className="flex items-center gap-1.5 bg-stone-100/80 dark:bg-zinc-800/50 rounded-3xl border border-zinc-200/60 dark:border-zinc-700/50 px-2 py-1.5">
          <Filter className="w-3 h-3 text-neutral-400 mr-2 ml-2" />
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              onClick={() => setCategory(c.key)}
              className={`text-[11px] font-semibold px-2.5 py-1 mb-1 rounded-2xl transition-all ${
                category === c.key
                  ? "bg-zinc-200/80 dark:bg-zinc-700 text-zinc-800 dark:text-zinc-100 shadow-sm"
                  : "text-neutral-400 hover:text-zinc-600 dark:hover:text-zinc-300"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Line count selector */}
        <div className="flex items-center gap-1 bg-stone-100/80 dark:bg-zinc-800/50 rounded-3xl border border-zinc-200/60 dark:border-zinc-700/50 px-2 py-1.5">
          {LINE_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => setMaxLines(n)}
              className={`text-[11px] font-semibold px-2 py-1 mb-1 rounded-2xl transition-all ${
                maxLines === n
                  ? "bg-zinc-200/80 dark:bg-zinc-700 text-zinc-800 dark:text-zinc-100 shadow-sm"
                  : "text-neutral-400 hover:text-zinc-600 dark:hover:text-zinc-300"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Log viewer */}
      <div className="bg-stone-100/80 dark:bg-zinc-800/50 p-6 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50 flex-1 flex flex-col min-h-0">
        <div className="flex-1 bg-[#070A13] border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl p-5 font-mono text-[11px] text-zinc-300 overflow-y-auto leading-relaxed whitespace-pre-wrap select-text custom-scrollbar">
          {filteredLogs || (
            <span className="text-neutral-500 italic">
              No {category} log entries found.
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
