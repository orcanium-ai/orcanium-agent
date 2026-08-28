import { useState, useEffect } from "react";
import {
  History,
  ChevronDown,
  ChevronRight,
  Trash2,
  Search,
  X,
  MessageSquare,
  Globe,
  Terminal,
  Clock,
  ChevronLeft,
  ChevronRight as ChevronRightIcon,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useSessions, useSession } from "../hooks/useSession";
import { toast } from "../components/ToastContainer";
import type { SessionInfo } from "../services/session.service";

const PAGE_SIZE = 20;

const SOURCE_CONFIG: Record<string, { icon: typeof Terminal; color: string }> =
  {
    cli: { icon: Terminal, color: "text-blue-500 dark:text-blue-400" },
    telegram: { icon: MessageSquare, color: "text-sky-400" },
    discord: { icon: MessageSquare, color: "text-indigo-400" },
    slack: {
      icon: MessageSquare,
      color: "text-emerald-600 dark:text-emerald-400",
    },
    whatsapp: { icon: Globe, color: "text-emerald-600 dark:text-emerald-400" },
    cron: { icon: Clock, color: "text-amber-400" },
  };

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export function SessionsPage() {
  const { sessions, isLoading, deleteSession } = useSessions();
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const filtered = search.trim()
    ? sessions.filter(
        (s) =>
          s.title?.toLowerCase().includes(search.toLowerCase()) ||
          s.agent_name?.toLowerCase().includes(search.toLowerCase()) ||
          s.source?.toLowerCase().includes(search.toLowerCase()),
      )
    : sessions;

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  useEffect(() => {
    setPage(0);
  }, [search]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSession(deleteTarget);
      toast.success("Session deleted");
      setDeleteTarget(null);
      if (expandedId === deleteTarget) setExpandedId(null);
    } catch {
      toast.error("Failed to delete session");
    }
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<History className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Sessions"
        description="Conversation history and episodic session ledger"
      />

      {/* Stats bar */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 bg-stone-100/80 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50 px-4 py-3 rounded-xl">
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-zinc-800 dark:text-zinc-100">
            {sessions.length}
          </span>
          <span className="text-[10px] text-zinc-500 font-medium">Total</span>
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-emerald-600 dark:text-emerald-400">
            {sessions.filter((s) => s.is_active).length}
          </span>
          <span className="text-[10px] text-zinc-500 font-medium">Active</span>
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tabular-nums leading-none text-zinc-700 dark:text-zinc-300">
            {sessions.filter((s) => !s.is_active).length}
          </span>
          <span className="text-[10px] text-zinc-500 font-medium">
            Archived
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
        <input
          type="text"
          placeholder="Search sessions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-neutral-300">
          <Clock className="w-5 h-5 animate-spin mr-2" />
          <span className="text-sm font-semibold">Loading sessions...</span>
        </div>
      ) : paged.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500">
          <History className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold">
            {search ? "No matching sessions" : "No sessions yet"}
          </p>
          <p className="text-xs text-neutral-300 mt-1">
            {search
              ? "Try a different search term"
              : "Start a conversation with an agent to create a session"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {paged.map((s) => (
            <SessionRow
              key={s.id}
              session={s}
              isExpanded={expandedId === s.id}
              onToggle={() =>
                setExpandedId((prev) => (prev === s.id ? null : s.id))
              }
              onDelete={() => setDeleteTarget(s.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-zinc-500">
            {page * PAGE_SIZE + 1}–
            {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of{" "}
            {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
              className="p-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-neutral-300 hover:text-zinc-800 dark:hover:text-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 text-xs text-zinc-500">
              Page {page + 1} of {totalPages}
            </span>
            <button
              disabled={(page + 1) * PAGE_SIZE >= filtered.length}
              onClick={() => setPage(page + 1)}
              className="p-1.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 text-neutral-300 hover:text-zinc-800 dark:hover:text-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete session"
        description="This will permanently remove this session and all its messages."
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

/* ── SessionRow ────────────────────────────────────────── */
function SessionRow({
  session,
  isExpanded,
  onToggle,
  onDelete,
}: {
  session: SessionInfo;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const { messages, isLoading: msgsLoading } = useSession(
    isExpanded ? session.id : undefined,
  );

  const sourceInfo = (session.source
    ? SOURCE_CONFIG[session.source]
    : null) ?? { icon: Globe, color: "text-neutral-300" };
  const SourceIcon = sourceInfo.icon;

  return (
    <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden transition-colors">
      {/* Row header */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-colors"
        onClick={onToggle}
      >
        <div className={`shrink-0 pt-0.5 ${sourceInfo.color}`}>
          <SourceIcon className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300 truncate">
              {session.title || session.agent_name || "Untitled"}
            </span>
            {session.is_active && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 dark:bg-emerald-400 shrink-0" />
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-zinc-500 font-mono">
              {session.agent_name}
            </span>
            <span className="text-[10px] text-neutral-300">·</span>
            <span className="text-[10px] text-zinc-500">
              {session.message_count ?? 0} msgs
            </span>
            {session.updated_at && (
              <>
                <span className="text-[10px] text-neutral-300">·</span>
                <span className="text-[10px] text-zinc-500">
                  {timeAgo(session.updated_at)}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-medium text-zinc-500 bg-stone-100 dark:bg-zinc-800 px-2 py-0.5 rounded border border-zinc-200/60 dark:border-zinc-700/50">
            {session.source ?? "local"}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 text-zinc-500 hover:text-rose-400 transition-colors"
            title="Delete session"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-zinc-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-zinc-500" />
          )}
        </div>
      </div>

      {/* Expanded messages */}
      {isExpanded && (
        <div className="border-t border-zinc-200/60 dark:border-zinc-700/50">
          {msgsLoading ? (
            <div className="flex items-center justify-center py-8 text-zinc-500">
              <Clock className="w-4 h-4 animate-spin mr-2" />
              <span className="text-xs">Loading messages...</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="py-8 text-center text-xs text-zinc-500">
              No messages in this session.
            </div>
          ) : (
            <div className="divide-y divide-zinc-200/60 dark:divide-zinc-700/50">
              {messages.map((msg, i) => {
                const isUser = msg.sender === "user";
                const isAgent = msg.sender === "agent";
                return (
                  <div key={msg.id || i} className="px-4 py-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider ${
                          isUser
                            ? "text-blue-500 dark:text-blue-400"
                            : isAgent
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-zinc-500"
                        }`}
                      >
                        {isUser ? "You" : isAgent ? "Agent" : msg.sender}
                      </span>
                      {msg.timestamp && (
                        <span className="text-[9px] text-neutral-300 font-mono">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SessionsPage;
