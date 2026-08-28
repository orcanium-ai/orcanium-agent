import { useState, useEffect, useCallback } from "react";
import {
  Radio,
  Wifi,
  WifiOff,
  RotateCw,
  Settings2,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { API_BASE } from "../services/api";
import { gatewayService } from "../services/channel.service";
import { useAgents } from "../hooks/useAgents";
import type { GatewayChannel } from "../types/gateway";

interface ChannelDef {
  id: string;
  name: string;
  icon: string;
  env_vars: { key: string; prompt: string; required: boolean; is_password: boolean }[];
}

const CHANNEL_DEFS: ChannelDef[] = [
  { id: "telegram", name: "Telegram", icon: "📱", env_vars: [
    { key: "TELEGRAM_BOT_TOKEN", prompt: "Bot Token", required: true, is_password: true },
    { key: "TELEGRAM_ALLOWED_USERS", prompt: "Allowed User IDs", required: false, is_password: false },
  ]},
  { id: "discord", name: "Discord", icon: "💬", env_vars: [
    { key: "DISCORD_BOT_TOKEN", prompt: "Bot Token", required: true, is_password: true },
  ]},
  { id: "slack", name: "Slack", icon: "🔷", env_vars: [
    { key: "SLACK_BOT_TOKEN", prompt: "Bot Token", required: true, is_password: true },
  ]},
  { id: "whatsapp", name: "WhatsApp", icon: "💚", env_vars: [
    { key: "WHATSAPP_MODE", prompt: "Mode (bot/self-chat)", required: true, is_password: false },
  ]},
  { id: "email", name: "Email", icon: "📧", env_vars: [
    { key: "EMAIL_ADDRESS", prompt: "Email Address", required: true, is_password: false },
    { key: "EMAIL_PASSWORD", prompt: "Password", required: true, is_password: true },
  ]},
  { id: "signal", name: "Signal", icon: "🔐", env_vars: [
    { key: "SIGNAL_PHONE", prompt: "Phone Number", required: true, is_password: false },
  ]},
];

export const ChannelsPage = () => {
  const { agents } = useAgents();
  const [channels, setChannels] = useState<GatewayChannel[]>([]);
  const [loading, setLoading] = useState(false);
  const [configuring, setConfiguring] = useState<{ agent: string; platform: string } | null>(null);
  const [envValues, setEnvValues] = useState<Record<string, string>>({});

  const loadChannels = useCallback(async () => {
    setLoading(true);
    try {
      const data = await gatewayService.list();
      setChannels(data);
    } catch {
      toast.error("Failed to load gateway channels");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  const getAgentChannels = (agentName: string): GatewayChannel[] => {
    return channels.filter((ch) => {
      const cfgAgent = ch.config?.agent_name || ch.id.split("_").slice(1).join("_");
      return cfgAgent === agentName;
    });
  };

  const getPlatformDef = (platform: string) => CHANNEL_DEFS.find((d) => d.id === platform);

  const handleConfigure = (agent: string, platform: string) => {
    setConfiguring({ agent, platform });
    setEnvValues({});
  };

  const handleSave = async () => {
    if (!configuring) return;
    const { agent, platform } = configuring;
    const channelId = `${platform}_${agent}`;
    const body: Record<string, string> = { agent_name: agent };
    for (const v of CHANNEL_DEFS.find((d) => d.id === platform)?.env_vars || []) {
      if (envValues[v.key]) body[v.key] = envValues[v.key];
    }
    try {
      const res = await fetch(`${API_BASE}/gateways/register?channel_id=${channelId}&platform=${platform}&enabled=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to register");
      toast.success(`${platform} channel configured for ${agent}`);
      setConfiguring(null);
      loadChannels();
    } catch {
      toast.error("Failed to save channel");
    }
  };

  const handleDelete = async (channelId: string) => {
    try {
      const res = await fetch(`${API_BASE}/gateways/${encodeURIComponent(channelId)}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      toast.success("Channel deleted");
      loadChannels();
    } catch {
      toast.error("Failed to delete channel");
    }
  };

  const handleToggle = async (channelId: string, enabled: boolean) => {
    try {
      await gatewayService.toggle(channelId, enabled);
      toast.success(enabled ? "Channel enabled" : "Channel disabled");
      loadChannels();
    } catch {
      toast.error("Failed to toggle channel");
    }
  };

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Radio className="w-4 h-4 text-green-400" />}
        title="Gateway Channels"
        description="Manage messaging channels per agent — Telegram, Discord, Slack, and more"
      >
        <button onClick={loadChannels} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 rounded-lg text-[11px] font-bold text-white transition-all uppercase">
          <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </PageHeader>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-500">
          <RotateCw className="w-5 h-5 animate-spin mr-2" /> <span>Loading...</span>
        </div>
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50">
          <Radio className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600 dark:text-neutral-300">No agents configured</p>
          <p className="text-xs text-zinc-500 mt-1">Create an agent first to configure gateway channels.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {agents.map((agent) => {
            const agentChannels = getAgentChannels(agent.name);
            const configuredPlatforms = new Set(agentChannels.map((c) => c.platform));
            const availablePlatforms = CHANNEL_DEFS.filter((d) => !configuredPlatforms.has(d.id));

            return (
              <div key={agent.name} className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                {/* Agent header */}
                <div className="flex items-center justify-between px-4 py-3 bg-zinc-200/30 dark:bg-zinc-700/30 border-b border-zinc-200/60 dark:border-zinc-700/50">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-zinc-800 dark:text-zinc-100">{agent.name}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">{agent.model_provider}/{agent.model_name}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">{agentChannels.length} channel(s)</span>
                </div>

                {/* Channel list */}
                {agentChannels.length > 0 && (
                  <div className="divide-y divide-zinc-200/60 dark:divide-zinc-700/50">
                    {agentChannels.map((ch) => {
                      const def = getPlatformDef(ch.platform);
                      return (
                        <div key={ch.id} className="flex items-center justify-between px-4 py-3">
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-lg shrink-0">{def?.icon || "🔌"}</span>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">{def?.name || ch.platform}</span>
                                <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded border ${
                                  ch.enabled
                                    ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                    : "text-zinc-500 bg-slate-500/10 border-slate-500/20"
                                }`}>
                                  {ch.enabled ? "Connected" : "Disabled"}
                                </span>
                              </div>
                              <span className="text-[10px] text-zinc-500 font-mono">{ch.id}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button onClick={() => handleConfigure(agent.name, ch.platform)}
                              className="p-1.5 text-zinc-500 hover:text-blue-500 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors" title="Configure">
                              <Settings2 className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => handleToggle(ch.id, !ch.enabled)}
                              className="p-1.5 text-zinc-500 hover:text-emerald-500 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors" title={ch.enabled ? "Disable" : "Enable"}>
                              {ch.enabled ? <Wifi className="w-3.5 h-3.5 text-emerald-500" /> : <WifiOff className="w-3.5 h-3.5" />}
                            </button>
                            <button onClick={() => handleDelete(ch.id)}
                              className="p-1.5 text-zinc-500 hover:text-rose-500 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors" title="Delete">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Available platforms / Add new */}
                {availablePlatforms.length > 0 && (
                  <div className="px-4 py-3 border-t border-zinc-200/60 dark:border-zinc-700/50">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] text-zinc-500 font-medium mr-1">Add:</span>
                      {availablePlatforms.map((def) => (
                        <button key={def.id} onClick={() => handleConfigure(agent.name, def.id)}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 bg-zinc-200/40 dark:bg-zinc-700/30 hover:bg-zinc-200 dark:hover:bg-zinc-700/50 rounded-lg transition-all">
                          <Plus className="w-3 h-3" /> {def.icon} {def.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Configure modal */}
      {configuring && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setConfiguring(null); }}>
          <div className="bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-md rounded-2xl p-6 shadow-2xl">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-100">
                  {getPlatformDef(configuring.platform)?.icon} {getPlatformDef(configuring.platform)?.name || configuring.platform}
                </h3>
                <p className="text-[11px] text-zinc-500">Configure for <strong>{configuring.agent}</strong></p>
              </div>
              <button onClick={() => setConfiguring(null)} className="text-zinc-500 hover:text-zinc-700">✕</button>
            </div>

            <div className="space-y-3">
              {getPlatformDef(configuring.platform)?.env_vars.map((v) => (
                <div key={v.key}>
                  <label className="text-[10px] font-medium text-neutral-300 block mb-1">
                    {v.prompt} {v.required ? "*" : ""}
                  </label>
                  <input type={v.is_password ? "password" : "text"} value={envValues[v.key] || ""}
                    onChange={(e) => setEnvValues((prev) => ({ ...prev, [v.key]: e.target.value }))}
                    placeholder={v.key}
                    className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400" />
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-zinc-200/60 dark:border-zinc-700/50">
              <button onClick={() => setConfiguring(null)}
                className="px-4 py-2 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-xs font-medium text-zinc-500 hover:text-zinc-700 transition-all">Cancel</button>
              <button onClick={handleSave}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-all">Save & Enable</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChannelsPage;
