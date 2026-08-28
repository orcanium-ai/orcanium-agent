import { Clock, Plus, PanelLeft, PanelRight } from "lucide-react";
import type { SessionInfo } from "../services/session.service";

interface ChatSidebarProps {
  sessions: SessionInfo[];
  loadingSessions: boolean;
  selectedSessionId: string | null;
  sidebarOpen: boolean;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onClose: () => void;
  onOpen: () => void;
}

export const ChatSidebar = ({
  sessions,
  loadingSessions,
  selectedSessionId,
  sidebarOpen,
  onSelectSession,
  onNewSession,
  onClose,
  onOpen,
}: ChatSidebarProps) => {
  return (
    <>
      {sidebarOpen && (
        <div className="w-60 shrink-0 flex flex-col bg-stone-100/50 dark:bg-neutral-700/15 rounded-3xl border border-zinc-200/10 dark:border-zinc-800/10 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-zinc-200/50 dark:border-zinc-800/50">
            <span className="text-[10px] ml-1 font-medium text-neutral-300 uppercase tracking-wider">
              Sessions
            </span>
            <button
              onClick={onClose}
              className="p-1 text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
              aria-label="Close sidebar"
            >
              <PanelLeft className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingSessions ? (
              <div className="flex items-center justify-center py-8">
                <Clock className="w-4 h-4 animate-spin text-neutral-300" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-500 px-3">
                No sessions yet.
              </div>
            ) : (
              <div className="py-1">
                {sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => onSelectSession(s.id)}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between gap-2 ${
                      selectedSessionId === s.id
                        ? "bg-zinc-100 dark:bg-zinc-700/50 font-medium text-zinc-800 dark:text-zinc-100"
                        : "text-zinc-500 dark:text-neutral-300 hover:bg-zinc-50 dark:hover:bg-zinc-700/30"
                    }`}
                  >
                    <span className="truncate flex-1">
                      {s.title || s.agent_name || "Untitled"}
                    </span>
                    <span className="shrink-0 text-[9px] text-neutral-300">
                      {s.message_count ?? 0}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="py-3 px-4">
            <button
              onClick={onNewSession}
              className="w-full flex items-center justify-center gap-1.5 px-4 py-1.5 rounded-full bg-stone-100/50 dark:bg-zinc-800/50 hover:bg-stone-200 dark:hover:bg-zinc-700 text-[10px] font-medium text-zinc-500 dark:text-neutral-300 border border-zinc-200/50 dark:border-zinc-800/50 transition-all"
            >
              <Plus className="w-3 h-3" /> New conversation
            </button>
          </div>
        </div>
      )}

      {!sidebarOpen && (
        <button
          onClick={onOpen}
          className="shrink-0 self-start p-3 mt-1 rounded-3xl text-neutral-300 hover:text-zinc-600 bg-neutral-800 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all hidden lg:block"
          aria-label="Open sidebar"
        >
          <PanelRight className="w-4 h-4" />
        </button>
      )}
    </>
  );
};
