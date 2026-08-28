import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { RefreshCw, Download, ChevronLeft, ChevronRight } from "lucide-react";
import { SIDEBAR_ITEMS } from "../constants/sidebar";
import { useAgents } from "../hooks/useAgents";
import { useTasks } from "../hooks/useTasks";
import { useGateways } from "../hooks/useGateways";

const COLLAPSED_KEY = "orcanium-sidebar-collapsed";

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  onMobileClose,
}) => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(COLLAPSED_KEY, String(next));
      } catch {}
      return next;
    });
  };

  const { agents } = useAgents();
  const { tasks } = useTasks();
  const { gateways } = useGateways();

  const agentsCount = agents.length;
  const tasksCount = tasks.length;
  const telegramGateway = gateways.find((g) => g.platform === "telegram");
  const gatewayConnected = telegramGateway?.enabled ?? false;

  const currentPath = location.pathname;

  // Close mobile sidebar on Escape
  React.useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onMobileClose?.();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [mobileOpen, onMobileClose]);

  // Auto-close mobile sidebar when expanding past lg breakpoint
  React.useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const onChange = (e: MediaQueryListEvent) => {
      if (e.matches) onMobileClose?.();
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [onMobileClose]);

  const sidebarContent = (
    <>
      <div className="flex h-full min-h-0 flex-col bg-[#191917]">
        <div
          className={`flex h-16 items-center border-b border-white/10 ${
            collapsed ? "justify-center px-0" : "px-4 justify-between"
          }`}
        >
          <div className={`flex items-center gap-3 ${collapsed && "hidden"}`}>
            <div className="grid h-9 w-9 shrink-0 grid-cols-2 gap-[3px] rounded-full p-[5px]">
              <span className="rounded-full bg-white" />
              <span className="rounded-full bg-white/80" />
              <span className="rounded-full bg-white/60" />
              <span className="rounded-full bg-[#ff8a50]" />
            </div>
            <div>
              <h1 className="font-medium text-sm tracking-tight text-white leading-tight">
                Orcanium
              </h1>
              <p className="text-[9px] uppercase tracking-[0.18em] text-white/45 leading-tight">
                Agent OS
              </p>
            </div>
          </div>

          <button
            onClick={toggleCollapsed}
            className="hidden text-white/40 transition-colors hover:text-white/80 lg:flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <ChevronLeft className="w-5 h-5" />
            )}
          </button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-4">
          <ul className="flex flex-col">
            {SIDEBAR_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                currentPath === item.path ||
                (item.path !== "/" && currentPath.startsWith(item.path));

              return (
                <li key={item.id}>
                  <NavLink
                    to={item.path}
                    onClick={onMobileClose}
                    className={`group/nav relative mx-3 my-1 md:my-0.5 flex cursor-pointer items-center gap-3 whitespace-nowrap rounded-xl border border-transparent px-3 py-2 text-sm font-mono uppercase tracking-[0.12em] transition-all duration-200 ${
                      isActive
                        ? "border-white/5 bg-stone-200/[0.06] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                        : "text-white/60 hover:border-white/8 hover:bg-stone-200/[0.03] hover:text-white/90"
                    } ${collapsed ? "justify-center px-0 mx-0" : ""}`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span
                      className={`truncate transition-opacity duration-300 ${
                        collapsed
                          ? "lg:absolute lg:opacity-0"
                          : "lg:opacity-100"
                      }`}
                    >
                      {item.label}
                    </span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      <div
        className={`bg-[#191917] border-t border-white/5 pt-3 ${collapsed ? "hidden" : ""}`}
      >
        <div className="px-4 pb-3 space-y-2">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center justify-between rounded-xl px-2.5 py-0.5">
              <span className="text-[9px] font-medium text-white/35">
                Agents
              </span>
              <span className="text-xs font-bold tabular-nums text-white/45">
                {agentsCount}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-xl px-2.5 py-0.5">
              <span className="text-[9px] font-medium text-white/35">
                Tasks
              </span>
              <span className="text-xs font-bold tabular-nums text-white/45">
                {tasksCount}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-xl px-2.5 py-0.5">
            <span className="text-[9px] font-medium text-white/35">
              Gateway
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full ${gatewayConnected ? "bg-emerald-500" : "bg-white/25"}`}
              />
              <span
                className={`text-[9px] font-semibold ${gatewayConnected ? "text-emerald-400" : "text-white/40"}`}
              >
                {gatewayConnected ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 px-4 pb-3">
          <button
            title="Reload runtime configuration"
            className="flex cursor-not-allowed items-center justify-center gap-1 rounded-xl border border-white/10 px-2 py-1.5 text-[8px] font-medium text-white/50 opacity-60 transition-all hover:bg-white/10"
            disabled
          >
            <RefreshCw className="w-3 h-3" />
            <span>Restart</span>
          </button>
          <button
            title="Not available in this version"
            className="flex cursor-not-allowed items-center justify-center gap-1 rounded-xl border border-white/10 px-2 py-1.5 text-[8px] font-medium text-white/50 opacity-60 transition-all hover:bg-white/10"
            disabled
          >
            <Download className="w-3 h-3" />
            <span>Update</span>
          </button>
        </div>

        <div className="px-4 py-2 border-t border-white/5 text-center">
          <span className="text-[7px] font-bold tracking-[0.12em] uppercase text-white/25">
            Orcanium AOS v1.0.0
          </span>
        </div>
      </div>
    </>
  );

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-3/5 flex-col border-r border-white/10 bg-[#191917] text-white backdrop-blur-xl transition-transform duration-300 ease-[cubic-bezier(0.33,1.35,0.62,1)] lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </aside>

      <aside
        className={`hidden h-screen shrink-0 flex-col justify-between select-none border-r border-white/10 bg-[linear-gradient(180deg,rgba(18,15,17,0.96),rgba(18,15,17,0.88),rgba(18,15,17,0.94))] text-white backdrop-blur-xl transition-all duration-300 ease-[cubic-bezier(0.33,1.35,0.62,1)] lg:flex ${
          collapsed ? "w-14" : "w-60"
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
};
