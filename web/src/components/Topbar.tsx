import {
  LogOut,
  Menu,
  MessageSquare,
  Bot,
  Cpu,
  LayoutDashboard,
  Wrench,
  BookOpen,
  Radio,
  Settings2,
  KeyRound,
  Server,
  FileText,
  ListTodo,
  Puzzle,
  GitBranch,
  type LucideIcon,
} from "lucide-react";
import { useLocation } from "react-router-dom";
import { useAgents } from "../hooks/useAgents";
import { useAuth } from "../hooks/useAuth";

interface PageMeta {
  icon: LucideIcon;
  title: string;
}

const PAGE_META: Record<string, PageMeta> = {
  dashboard: { icon: LayoutDashboard, title: "Dashboard" },
  chat: { icon: MessageSquare, title: "Chat" },
  sessions: { icon: MessageSquare, title: "Sessions" },
  agents: { icon: Bot, title: "Agents" },
  models: { icon: Cpu, title: "Models" },
  skills: { icon: Puzzle, title: "Skills" },
  tasks: { icon: ListTodo, title: "Tasks" },
  knowledge: { icon: BookOpen, title: "Knowledge" },
  tools: { icon: Wrench, title: "Tools" },
  mcp: { icon: GitBranch, title: "MCP" },
  channels: { icon: Radio, title: "Channels" },
  config: { icon: Settings2, title: "Config" },
  keys: { icon: KeyRound, title: "Keys" },
  system: { icon: Server, title: "System" },
  logs: { icon: FileText, title: "Logs" },
  documentation: { icon: FileText, title: "Docs" },
};

interface TopbarProps {
  onMenuClick?: () => void;
}

function LogoutButton() {
  const { logout, token } = useAuth();
  if (!token) return null;
  return (
    <button
      onClick={logout}
      className="flex items-center gap-1 rounded-lg bg-stone-100/80 dark:bg-zinc-800/50 px-2 py-1 border border-zinc-200/60 dark:border-zinc-700/50 text-neutral-400 hover:text-red-400 transition-colors"
      title="Sign out"
    >
      <LogOut className="w-3 h-3" />
      <span className="text-[9px] font-medium">Logout</span>
    </button>
  );
}

export const Topbar = ({ onMenuClick }: TopbarProps) => {
  const { agents } = useAgents();
  const activeCount = agents.filter((a) => a.status === "running").length;
  const location = useLocation();
  const path = location.pathname.replace("/", "");
  const meta = PAGE_META[path] || { icon: null, title: "Orcanium" };

  return (
    <header className="flex items-center justify-between h-16 px-5 py-2 border-b border-zinc-200/50 dark:border-zinc-700/40 bg-neutral-500/70 dark:bg-neutral-900/70 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile hamburger */}
        <button
          onClick={onMenuClick}
          className="p-1 -ml-1 mr-1 text-neutral-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="w-4 h-4" />
        </button>
        <span className="text-base font-black text-zinc-800 dark:text-zinc-100 tracking-[0.1em] uppercase truncate">
          {meta.title}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 bg-stone-100/80 dark:bg-zinc-800/50 px-2 py-1 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50">
          <span
            className={`w-1.5 h-1.5 rounded-full ${activeCount > 0 ? "bg-emerald-500 animate-pulse" : "bg-zinc-400"}`}
          />
          <span className="text-[9px] font-medium text-zinc-500 dark:text-neutral-300">
            {activeCount}/{agents.length} agents
          </span>
        </div>
        <LogoutButton />
      </div>
    </header>
  );
};
