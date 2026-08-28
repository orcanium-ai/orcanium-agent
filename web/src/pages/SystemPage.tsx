import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Cpu,
  Database,
  Globe,
  HardDrive,
  KeyRound,
  Play,
  Power,
  RefreshCw,
  RotateCw,
  Server,
  WifiOff,
  Monitor,
  Clock,
  MemoryStick,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { API_BASE } from "../services/api";
import { systemService } from "../services/system.service";
import { EventTimeline } from "../features/events/EventTimeline";
import type {
  RootStatus,
  GatewayChannel,
  ProviderEntry,
  SystemStats,
} from "../services/system.service";

/* ── Helpers ─────────────────────────────────────────── */

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/* ── Sub-components ──────────────────────────────────── */

function SectionHeader({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <h3 className="flex items-center gap-2 text-[11px] font-medium text-neutral-300">
      {icon}
      {children}
    </h3>
  );
}

function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden ${className}`}
    >
      {children}
    </div>
  );
}

function CardContent({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`p-4 ${className}`}>{children}</div>;
}

/** Badge colors for different statuses */
function StatusBadge({
  tone,
  children,
}: {
  tone: "success" | "warning" | "muted" | "danger";
  children: React.ReactNode;
}) {
  const colors = {
    success:
      "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
    warning:
      "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
    muted:
      "bg-zinc-100 dark:bg-zinc-800 text-neutral-300 border-zinc-200/60 dark:border-zinc-700/50",
    danger:
      "bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/20",
  };
  return (
    <span
      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${colors[tone]}`}
    >
      {children}
    </span>
  );
}

/** Inline label-value pair */
function StatRow({
  label,
  value,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[10px] font-medium text-neutral-300 flex items-center gap-1">
        {icon}
        {label}
      </div>
      <div className="text-zinc-700 dark:text-zinc-300 mt-0.5 text-xs">
        {value ?? (
          <span className="text-neutral-300 italic">Not available</span>
        )}
      </div>
    </div>
  );
}

function ActionButton({
  onClick,
  disabled,
  variant = "default",
  icon,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "primary" | "danger" | "ghost";
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  const styles = {
    default:
      "border border-zinc-200/60 dark:border-zinc-700/50 text-zinc-600 dark:text-zinc-300 hover:text-zinc-800 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700/50",
    primary:
      "bg-blue-600 hover:bg-blue-500 text-white disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300",
    danger:
      "border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20",
    ghost:
      "text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700/50",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all disabled:opacity-50 ${styles[variant]}`}
    >
      {icon}
      {children}
    </button>
  );
}

/* ── Proxy / unavailable section card ────────────────── */

function UnavailableCard({ label }: { label: string }) {
  return (
    <Card>
      <CardContent className="py-6 text-center text-xs text-neutral-300">
        <WifiOff className="w-4 h-4 mx-auto mb-2 opacity-50" />
        <p className="font-medium">{label}</p>
        <p className="mt-1 text-[10px]">Backend endpoint not available.</p>
      </CardContent>
    </Card>
  );
}

/* ── Progress bar component ──────────────────────────── */

function ProgressBar({
  pct,
  color = "blue",
}: {
  pct: number;
  color?: "blue" | "purple" | "amber";
}) {
  const colors = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    amber: "bg-amber-500",
  };
  return (
    <div className="h-2 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
      <div
        className={`h-full ${colors[color]} rounded-full transition-all duration-500`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

/* ── Main page ───────────────────────────────────────── */

export const SystemPage = () => {
  const [status, setStatus] = useState<RootStatus | null>(null);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [gateways, setGateways] = useState<GatewayChannel[] | null>(null);
  const [providers, setProviders] = useState<ProviderEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState<boolean | null>(null);

  const loadAll = useCallback(async () => {
    const [s, st, g, p] = await Promise.all([
      systemService.getStatus(),
      systemService.getSystemStats(),
      systemService.getGateways(),
      systemService.getProviders(),
    ]);
    setStatus(s);
    setStats(st);
    setGateways(g);
    setProviders(p);
    setConnected(s !== null);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  /* ── Gateway toggle ── */
  const toggleGateway = async (id: string, enabled: boolean) => {
    await systemService.toggleGateway(id, enabled);
    const g = await systemService.getGateways();
    if (g) setGateways(g);
  };

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center py-24">
        <RefreshCw className="w-6 h-6 animate-spin text-neutral-300" />
      </div>
    );
  }

  const configuredCount = providers?.filter((p) => p.configured).length ?? 0;
  const totalProviders = providers?.length ?? 0;
  const enabledGateways = gateways?.filter((g) => g.enabled) ?? [];

  /* ── Render ── */
  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Server className="w-4 h-4 text-blue-400" />}
        title="System"
        description="System diagnostics and runtime configuration"
      />

      {/* ── Connection banner ── */}
      {connected === false && (
        <Card className="border-amber-200 dark:border-amber-500/20">
          <CardContent className="flex items-center gap-3 py-3">
            <WifiOff className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                Backend unreachable
              </p>
              <p className="text-[10px] text-neutral-300 mt-0.5">
                Could not connect to {API_BASE.replace("/api/v1", "/")}. Some
                sections will show limited data.
              </p>
            </div>
            <button
              onClick={loadAll}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold border border-zinc-200/60 dark:border-zinc-700/50 text-zinc-600 dark:text-zinc-300 hover:text-zinc-800 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </button>
          </CardContent>
        </Card>
      )}

      {/* ── Host ──────────────────────────────────────── */}
      <section className="flex flex-col gap-3">
        <SectionHeader icon={<Monitor className="w-3.5 h-3.5" />}>
          Host
        </SectionHeader>
        <Card>
          <CardContent className="divide-y divide-zinc-200/60 dark:divide-zinc-700/50">
            {/* Identity row */}
            <div className="pb-3 grid grid-cols-2 gap-y-4 gap-x-4">
              <StatRow
                label="OS"
                value={stats?.host?.os || status?.system || "Unknown"}
              />
              <StatRow label="Arch" value={stats?.host?.arch || "\u2014"} />
              <StatRow label="Host" value={stats?.host?.hostname || "\u2014"} />
              <StatRow
                label="Python"
                value={
                  stats?.host?.python
                    ? `CPython ${stats.host.python}`
                    : "\u2014"
                }
              />
            </div>

            {/* CPU */}
            {stats && (
              <div className="py-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-neutral-500" /> CPU
                  </span>
                  <span className="text-zinc-700 dark:text-zinc-300">
                    {stats.cpu.cores} cores &middot;{" "}
                    <span
                      className={`font-semibold ${stats.cpu.usage_pct > 80 ? "text-rose-500" : stats.cpu.usage_pct > 50 ? "text-amber-500" : "text-emerald-500"}`}
                    >
                      {stats.cpu.usage_pct.toFixed(1)}%
                    </span>
                  </span>
                </div>
                <ProgressBar pct={stats.cpu.usage_pct} color="blue" />
              </div>
            )}

            {/* Memory */}
            {stats && (
              <div className="py-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                    <MemoryStick className="w-3.5 h-3.5 text-neutral-500" />{" "}
                    Memory
                  </span>
                  <span className="text-zinc-700 dark:text-zinc-300">
                    {formatBytes(stats.memory.available_bytes)} available
                    &middot; {formatBytes(stats.memory.used_bytes)} used
                    &middot;{" "}
                    <span
                      className={`font-semibold ${stats.memory.usage_pct > 80 ? "text-rose-500" : stats.memory.usage_pct > 50 ? "text-amber-500" : "text-emerald-500"}`}
                    >
                      {stats.memory.usage_pct.toFixed(1)}%
                    </span>
                  </span>
                </div>
                <ProgressBar pct={stats.memory.usage_pct} color="purple" />
              </div>
            )}

            {/* Storage */}
            {stats && (
              <div className="py-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                    <HardDrive className="w-3.5 h-3.5 text-neutral-500" />{" "}
                    Storage
                  </span>
                  <span className="text-zinc-700 dark:text-zinc-300">
                    {stats.disk.free_gb} GB available &middot;{" "}
                    {stats.disk.used_gb} GB used &middot;{" "}
                    <span
                      className={`font-semibold ${stats.disk.usage_pct > 80 ? "text-rose-500" : stats.disk.usage_pct > 50 ? "text-amber-500" : "text-emerald-500"}`}
                    >
                      {stats.disk.usage_pct.toFixed(1)}%
                    </span>
                  </span>
                </div>
                <ProgressBar pct={stats.disk.usage_pct} color="amber" />
              </div>
            )}

            {/* Uptime */}
            {stats && (
              <div className="pt-3 flex items-center justify-between text-xs">
                <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-emerald-500" /> Uptime
                </span>
                <span className="text-zinc-700 dark:text-zinc-300 font-mono">
                  {stats.uptime || "\u2014"}
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* ── Runtime overview cards ────────────────────── */}
      <section className="flex flex-col gap-3">
        <SectionHeader icon={<Activity className="w-3.5 h-3.5" />}>
          Runtime
        </SectionHeader>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-3">
              <Cpu className="w-4 h-4 text-blue-500 dark:text-blue-400 mb-1" />
              <div className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
                {connected ? `${configuredCount}/${totalProviders}` : "\u2014"}
              </div>
              <div className="text-[10px] font-medium text-neutral-300 mt-0.5">
                Providers
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <Server className="w-4 h-4 text-emerald-500 dark:text-emerald-400 mb-1" />
              <div className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
                {connected
                  ? `${enabledGateways.length}/${gateways?.length ?? 0}`
                  : "\u2014"}
              </div>
              <div className="text-[10px] font-medium text-neutral-300 mt-0.5">
                Gateways
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <Globe className="w-4 h-4 text-purple-500 dark:text-purple-400 mb-1" />
              <div className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
                {connected ? (
                  <span
                    className={`${status?.status === "online" ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-300"}`}
                  >
                    {status?.status === "online" ? "Online" : "Offline"}
                  </span>
                ) : (
                  "\u2014"
                )}
              </div>
              <div className="text-[10px] font-medium text-neutral-300 mt-0.5">
                Backend
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <Database className="w-4 h-4 text-amber-500 dark:text-amber-400 mb-1" />
              <div className="text-lg font-bold text-zinc-800 dark:text-zinc-100">
                {connected ? "OK" : "\u2014"}
              </div>
              <div className="text-[10px] font-medium text-neutral-300 mt-0.5">
                Config
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ── Gateway channels ──────────────────────────── */}
      <section className="flex flex-col gap-3">
        <SectionHeader icon={<Power className="w-3.5 h-3.5" />}>
          Gateway
        </SectionHeader>
        {!connected ? (
          <UnavailableCard label="Gateway status unavailable" />
        ) : gateways === null ? (
          <UnavailableCard label="Failed to load gateways" />
        ) : gateways.length === 0 ? (
          <Card>
            <CardContent className="py-6 text-center text-xs text-zinc-500">
              No gateway channels configured.
            </CardContent>
          </Card>
        ) : (
          gateways.map((gw) => (
            <Card key={gw.id}>
              <CardContent className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <StatusBadge tone={gw.enabled ? "success" : "muted"}>
                    {gw.enabled ? "running" : "stopped"}
                  </StatusBadge>
                  <span className="text-xs text-zinc-700 dark:text-zinc-300 font-medium">
                    {gw.platform}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">
                    {gw.id}
                  </span>
                </div>
                <ActionButton
                  variant={gw.enabled ? "danger" : "primary"}
                  icon={
                    gw.enabled ? (
                      <Power className="w-3 h-3" />
                    ) : (
                      <Play className="w-3 h-3" />
                    )
                  }
                  onClick={() => toggleGateway(gw.id, !gw.enabled)}
                >
                  {gw.enabled ? "Stop" : "Start"}
                </ActionButton>
              </CardContent>
            </Card>
          ))
        )}
      </section>

      {/* ── Providers / Keys ──────────────────────────── */}
      <section className="flex flex-col gap-3">
        <SectionHeader icon={<KeyRound className="w-3.5 h-3.5" />}>
          Providers
        </SectionHeader>
        {!connected || providers === null ? (
          <UnavailableCard label="Provider data unavailable" />
        ) : (
          <Card>
            <CardContent className="p-0 divide-y divide-zinc-200/60 dark:divide-zinc-700/50">
              {providers.map((p) => (
                <div
                  key={p.provider_id}
                  className="flex items-center gap-3 px-4 py-2.5"
                >
                  <StatusBadge tone={p.configured ? "success" : "muted"}>
                    {p.configured ? "configured" : "not configured"}
                  </StatusBadge>
                  <span className="text-xs text-zinc-700 dark:text-zinc-300 font-medium min-w-[80px]">
                    {p.provider_name}
                  </span>
                  {p.masked_value && (
                    <span className="font-mono text-[10px] text-zinc-500">
                      {p.masked_value}
                    </span>
                  )}
                  <span className="text-[10px] text-zinc-500 ml-auto">
                    {p.status}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </section>

      {/* ── Event Timeline ────────────────────────────── */}
      <EventTimeline maxEvents={100} />

      {/* ── Operations ────────────────────────────────── */}
      <section className="flex flex-col gap-3">
        <SectionHeader icon={<Activity className="w-3.5 h-3.5" />}>
          Operations
        </SectionHeader>
        <Card>
          <CardContent className="flex flex-wrap gap-2">
            <ActionButton
              icon={<RotateCw className="w-3.5 h-3.5" />}
              variant={connected ? "default" : "ghost"}
              disabled={!connected}
              onClick={() => systemService.reloadConfig().then(loadAll)}
            >
              Reload config
            </ActionButton>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default SystemPage;
