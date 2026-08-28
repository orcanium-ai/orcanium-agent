import { useState, useEffect } from "react";
import {
  Sliders,
  Settings2,
  Download,
  Upload,
  RotateCcw,
  Save,
  Palette,
  Server,
  RefreshCw,
  BookOpen,
  Bot,
  FileText,
  Code,
  FormInput,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { configService } from "../services/config.service";
import { useSettingsStore } from "../stores/settingsStore";

const THEMES = [
  { id: "slate" as const, label: "Slate", color: "bg-slate-500" },
  { id: "violet" as const, label: "Violet", color: "bg-violet-500" },
  { id: "emerald" as const, label: "Emerald", color: "bg-emerald-500" },
  { id: "amber" as const, label: "Amber", color: "bg-amber-500" },
];

const SECTIONS = [
  { id: "daemon", label: "Daemon", icon: Server },
  { id: "default", label: "Default", icon: BookOpen },
  { id: "agent", label: "Agent", icon: Bot },
  { id: "settings", label: "Settings", icon: Settings2 },
  { id: "appearance", label: "Appearance", icon: Palette },
];

interface DefaultConfig {
  model: string;
  context_length: number;
  fallback_providers: string;
  toolsets: string;
  max_concurrent_sessions: number;
  file_read_max_chars: number;
  prefill_messages_file: string;
  timezone: string;
  command_allowlist: string;
  hooks_auto_accept: boolean;
  paste_collapse_threshold: number;
  paste_collapse_threshold_fallback: number;
  paste_collapse_char_threshold: number;
}

interface AgentConfig {
  max_turns: number;
  gateway_timeout: number;
  restart_drain_timeout: number;
  api_max_retries: number;
  service_tier: string;
  tool_use_enforcement: string;
  task_completion_guidance: string;
  environment_probe: string;
  environment_hint: string;
  gateway_timeout_warning: number;
  clarify_timeout: number;
  gateway_notify_interval: number;
  gateway_auto_continue_freshness: number;
  image_input_mode: string;
  disabled_toolsets: string;
}

export const ConfigPage = () => {
  const { apiBase, setApiBase, theme, setTheme } = useSettingsStore();
  const [draftApiBase, setDraftApiBase] = useState(apiBase);
  const [activeSection, setActiveSection] = useState("daemon");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [yamlMode, setYamlMode] = useState(false);
  const [yamlText, setYamlText] = useState("");
  const [yamlLoading, setYamlLoading] = useState(false);
  const [yamlSaving, setYamlSaving] = useState(false);
  const [configPath, setConfigPath] = useState("");

  // Settings fields
  const [telemetry, setTelemetry] = useState(false);
  const [autoBackup, setAutoBackup] = useState(true);

  // Default section fields
  const [defaultCfg, setDefaultCfg] = useState<DefaultConfig>({
    model: "orcanium-64k:latest",
    context_length: 0,
    fallback_providers: "",
    toolsets: "orcanium-cli",
    max_concurrent_sessions: 0,
    file_read_max_chars: 100000,
    prefill_messages_file: "",
    timezone: "",
    command_allowlist: "",
    hooks_auto_accept: false,
    paste_collapse_threshold: 5,
    paste_collapse_threshold_fallback: 5,
    paste_collapse_char_threshold: 0,
  });

  // Agent section fields
  const [agentCfg, setAgentCfg] = useState<AgentConfig>({
    max_turns: 90,
    gateway_timeout: 1800,
    restart_drain_timeout: 180,
    api_max_retries: 3,
    service_tier: "",
    tool_use_enforcement: "auto",
    task_completion_guidance: "",
    environment_probe: "",
    environment_hint: "",
    gateway_timeout_warning: 900,
    clarify_timeout: 600,
    gateway_notify_interval: 180,
    gateway_auto_continue_freshness: 3600,
    image_input_mode: "auto",
    disabled_toolsets: "",
  });

  useEffect(() => {
    Promise.all([
      configService.get(),
      configService.getRaw().catch(() => ({ yaml: "", path: "" })),
    ])
      .then(([cfg, raw]) => {
        if (raw.path) setConfigPath(raw.path);
        const d = cfg.model as Record<string, any> | undefined;
        const a = cfg.agent as Record<string, any> | undefined;
        const s = cfg.settings as Record<string, any> | undefined;
        setTelemetry(s?.telemetry ?? false);
        setAutoBackup(s?.auto_backup ?? true);
        setDefaultCfg((prev) => ({
          ...prev,
          model: (d?.default_model as string) ?? prev.model,
          context_length: (d?.context_length as number) ?? prev.context_length,
          fallback_providers:
            (d?.fallback_providers as string) ?? prev.fallback_providers,
          toolsets: (d?.toolsets as string) ?? prev.toolsets,
          max_concurrent_sessions:
            (d?.max_concurrent_sessions as number) ??
            prev.max_concurrent_sessions,
          file_read_max_chars:
            (d?.file_read_max_chars as number) ?? prev.file_read_max_chars,
          prefill_messages_file:
            (d?.prefill_messages_file as string) ?? prev.prefill_messages_file,
          timezone: (d?.timezone as string) ?? prev.timezone,
          command_allowlist:
            (d?.command_allowlist as string) ?? prev.command_allowlist,
          hooks_auto_accept:
            (d?.hooks_auto_accept as boolean) ?? prev.hooks_auto_accept,
          paste_collapse_threshold:
            (d?.paste_collapse_threshold as number) ??
            prev.paste_collapse_threshold,
          paste_collapse_threshold_fallback:
            (d?.paste_collapse_threshold_fallback as number) ??
            prev.paste_collapse_threshold_fallback,
          paste_collapse_char_threshold:
            (d?.paste_collapse_char_threshold as number) ??
            prev.paste_collapse_char_threshold,
        }));
        setAgentCfg((prev) => ({
          ...prev,
          max_turns: (a?.max_turns as number) ?? prev.max_turns,
          gateway_timeout:
            (a?.gateway_timeout as number) ?? prev.gateway_timeout,
          restart_drain_timeout:
            (a?.restart_drain_timeout as number) ?? prev.restart_drain_timeout,
          api_max_retries:
            (a?.api_max_retries as number) ?? prev.api_max_retries,
          service_tier: (a?.service_tier as string) ?? prev.service_tier,
          tool_use_enforcement:
            (a?.tool_use_enforcement as string) ?? prev.tool_use_enforcement,
          task_completion_guidance:
            (a?.task_completion_guidance as string) ??
            prev.task_completion_guidance,
          environment_probe:
            (a?.environment_probe as string) ?? prev.environment_probe,
          environment_hint:
            (a?.environment_hint as string) ?? prev.environment_hint,
          gateway_timeout_warning:
            (a?.gateway_timeout_warning as number) ??
            prev.gateway_timeout_warning,
          clarify_timeout:
            (a?.clarify_timeout as number) ?? prev.clarify_timeout,
          gateway_notify_interval:
            (a?.gateway_notify_interval as number) ??
            prev.gateway_notify_interval,
          gateway_auto_continue_freshness:
            (a?.gateway_auto_continue_freshness as number) ??
            prev.gateway_auto_continue_freshness,
          image_input_mode:
            (a?.image_input_mode as string) ?? prev.image_input_mode,
          disabled_toolsets:
            (a?.disabled_toolsets as string) ?? prev.disabled_toolsets,
        }));
      })
      .catch(() => toast.error("Failed to load config"))
      .finally(() => setLoading(false));
  }, []);

  // Load YAML when switching to YAML mode
  useEffect(() => {
    if (yamlMode && !yamlText) {
      setYamlLoading(true);
      configService
        .getRaw()
        .then((resp) => setYamlText(resp.yaml))
        .catch(() => toast.error("Failed to load raw config"))
        .finally(() => setYamlLoading(false));
    }
  }, [yamlMode, yamlText]);

  const saveAll = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        settings: { theme, telemetry, auto_backup: autoBackup },
        model: {
          default_model: defaultCfg.model,
          context_length: defaultCfg.context_length,
          fallback_providers: defaultCfg.fallback_providers,
          toolsets: defaultCfg.toolsets,
          max_concurrent_sessions: defaultCfg.max_concurrent_sessions,
          file_read_max_chars: defaultCfg.file_read_max_chars,
          prefill_messages_file: defaultCfg.prefill_messages_file,
          timezone: defaultCfg.timezone,
          command_allowlist: defaultCfg.command_allowlist,
          hooks_auto_accept: defaultCfg.hooks_auto_accept,
          paste_collapse_threshold: defaultCfg.paste_collapse_threshold,
          paste_collapse_threshold_fallback:
            defaultCfg.paste_collapse_threshold_fallback,
          paste_collapse_char_threshold:
            defaultCfg.paste_collapse_char_threshold,
        },
        agent: agentCfg,
      };
      setApiBase(draftApiBase);
      await configService.update(payload);
      toast.success("Configuration saved");
    } catch {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setDraftApiBase("http://localhost:8000/api/v1");
    setTheme("slate");
    setTelemetry(false);
    setAutoBackup(true);
    setDefaultCfg({
      model: "orcanium-64k:latest",
      context_length: 0,
      fallback_providers: "",
      toolsets: "orcanium-cli",
      max_concurrent_sessions: 0,
      file_read_max_chars: 100000,
      prefill_messages_file: "",
      timezone: "",
      command_allowlist: "",
      hooks_auto_accept: false,
      paste_collapse_threshold: 5,
      paste_collapse_threshold_fallback: 5,
      paste_collapse_char_threshold: 0,
    });
    setAgentCfg({
      max_turns: 90,
      gateway_timeout: 1800,
      restart_drain_timeout: 180,
      api_max_retries: 3,
      service_tier: "",
      tool_use_enforcement: "auto",
      task_completion_guidance: "",
      environment_probe: "",
      environment_hint: "",
      gateway_timeout_warning: 900,
      clarify_timeout: 600,
      gateway_notify_interval: 180,
      gateway_auto_continue_freshness: 3600,
      image_input_mode: "auto",
      disabled_toolsets: "",
    });
    toast.success("Settings reset to defaults");
  };

  const handleYamlSave = async () => {
    setYamlSaving(true);
    try {
      await configService.saveRaw(yamlText);
      toast.success("Raw config saved");
    } catch {
      toast.error("Failed to save raw config");
    } finally {
      setYamlSaving(false);
    }
  };

  const handleExport = () => {
    const data = JSON.stringify(
      {
        apiBase,
        theme,
        settings: { telemetry, auto_backup: autoBackup },
        model: defaultCfg,
        agent: agentCfg,
      },
      null,
      2,
    );
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "orcanium-config.json";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Config exported");
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data.apiBase) {
          setDraftApiBase(data.apiBase);
          setApiBase(data.apiBase);
        }
        if (data.theme) setTheme(data.theme);
        if (data.model) setDefaultCfg((p) => ({ ...p, ...data.model }));
        if (data.agent) setAgentCfg((p) => ({ ...p, ...data.agent }));
        if (data.settings) {
          setTelemetry(data.settings.telemetry ?? false);
          setAutoBackup(data.settings.auto_backup ?? false);
        }
        toast.success("Config imported");
      } catch {
        toast.error("Invalid config file");
      }
    };
    input.click();
  };

  if (loading)
    return (
      <div className="p-6 flex items-center justify-center py-24">
        <RefreshCw className="w-6 h-6 animate-spin text-neutral-300" />
      </div>
    );

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      {/* Config path */}
      {configPath && (
        <div className="flex items-center gap-2 bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-4 py-2.5">
          <FileText className="w-4 h-4 shrink-0 text-zinc-500" />
          <code className="text-[11px] text-neutral-300 font-mono break-all">
            {configPath}
          </code>
        </div>
      )}

      <PageHeader
        icon={<Sliders className="w-4 h-4 text-blue-500 dark:text-blue-400" />}
        title="Config"
        description="Platform daemon settings and configuration"
      >
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleExport}
            className="p-1.5 text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
            title="Export config"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleImport}
            className="p-1.5 text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
            title="Import config"
          >
            <Upload className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleReset}
            className="p-1.5 text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
            title="Reset to defaults"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <div className="w-px h-5 bg-zinc-200/60 dark:bg-zinc-700/50 mx-1" />
          {!yamlMode && (
            <button
              onClick={saveAll}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 rounded-lg text-[11px] font-semibold text-white transition-all uppercase"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saving ? "Saving..." : "Save"}</span>
            </button>
          )}
          {yamlMode && (
            <button
              onClick={handleYamlSave}
              disabled={yamlSaving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300 rounded-lg text-[11px] font-semibold text-white transition-all uppercase"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{yamlSaving ? "Saving..." : "Save"}</span>
            </button>
          )}
          <div className="w-px h-5 bg-zinc-200/60 dark:bg-zinc-700/50 mx-1" />
          <button
            onClick={() => setYamlMode(!yamlMode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all ${
              yamlMode
                ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-500/20"
                : "text-neutral-300 border-zinc-200/60 dark:border-zinc-700/50 hover:text-zinc-600 dark:hover:text-zinc-300"
            }`}
          >
            {yamlMode ? (
              <FormInput className="w-3.5 h-3.5" />
            ) : (
              <Code className="w-3.5 h-3.5" />
            )}
            <span>{yamlMode ? "Form" : "YAML"}</span>
          </button>
        </div>
      </PageHeader>

      <div className="flex min-w-0 flex-col gap-4 sm:flex-row">
        <aside className="sm:w-48 sm:shrink-0">
          <div className="sm:sticky sm:top-4">
            <div className="flex flex-col border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl bg-stone-100/80 dark:bg-zinc-800/50 overflow-hidden">
              <div className="hidden sm:flex items-center gap-2 px-3 py-2.5 border-b border-zinc-200/60 dark:border-zinc-700/50">
                <Settings2 className="w-3 h-3 text-zinc-500" />
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-zinc-500">
                  Sections
                </span>
              </div>
              <div className="flex sm:flex-col gap-px p-1 overflow-x-auto sm:overflow-x-visible">
                {SECTIONS.map((sec) => {
                  const Icon = sec.icon;
                  const isActive = activeSection === sec.id;
                  return (
                    <button
                      key={sec.id}
                      onClick={() => setActiveSection(sec.id)}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all ${
                        isActive
                          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                          : "text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700/50"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      <span>{sec.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </aside>

        <div className="flex-1 min-w-0 space-y-4">
          {/* ── YAML mode ── */}
          {yamlMode ? (
            <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-zinc-200/60 dark:border-zinc-700/50 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                <span className="text-xs font-bold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider">
                  Raw Config YAML
                </span>
              </div>
              {yamlLoading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-5 h-5 animate-spin text-neutral-300" />
                </div>
              ) : (
                <textarea
                  value={yamlText}
                  onChange={(e) => setYamlText(e.target.value)}
                  className="w-full min-h-[500px] bg-[#070A13] px-4 py-3 text-xs font-mono text-zinc-700 dark:text-zinc-300 leading-relaxed focus:outline-none resize-vertical border-t border-zinc-200/60 dark:border-zinc-700/50"
                  spellCheck={false}
                />
              )}
            </div>
          ) : (
            <>
              {activeSection === "daemon" && (
                <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center gap-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50 mb-5">
                      <Server className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <h3 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                        Daemon Connection
                      </h3>
                    </div>
                    <div className="max-w-md">
                      <label className="text-[9px] text-neutral-300 font-extrabold uppercase block mb-1.5">
                        Backend Server URL
                      </label>
                      <input
                        type="text"
                        value={draftApiBase}
                        onChange={(e) => setDraftApiBase(e.target.value)}
                        className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2.5 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 font-mono"
                      />
                      <p className="text-[10px] text-zinc-500 mt-1.5">
                        Default:{" "}
                        <code className="text-blue-500 dark:text-blue-400 font-mono">
                          http://localhost:8000/api/v1
                        </code>
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Default ── */}
              {activeSection === "default" && (
                <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center gap-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50 mb-5">
                      <BookOpen className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <h3 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                        Default Configuration
                      </h3>
                    </div>
                    <div className="max-w-lg space-y-5">
                      <ConfigField
                        label="Default Model"
                        hint="e.g. anthropic/claude-sonnet-4.6"
                      >
                        <input
                          type="text"
                          value={defaultCfg.model}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              model: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Model Context Length"
                        hint="Context window override (0 = auto-detect from model metadata)"
                      >
                        <input
                          type="number"
                          value={defaultCfg.context_length}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              context_length: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Fallback Providers"
                        hint="comma-separated values"
                      >
                        <input
                          type="text"
                          value={defaultCfg.fallback_providers}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              fallback_providers: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Toolsets"
                        hint="Default toolsets to load"
                      >
                        <input
                          type="text"
                          value={defaultCfg.toolsets}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              toolsets: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Max Concurrent Sessions">
                        <input
                          type="number"
                          value={defaultCfg.max_concurrent_sessions}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              max_concurrent_sessions: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="File Read Max Chars">
                        <input
                          type="number"
                          value={defaultCfg.file_read_max_chars}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              file_read_max_chars: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Prefill Messages File">
                        <input
                          type="text"
                          value={defaultCfg.prefill_messages_file}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              prefill_messages_file: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Timezone">
                        <input
                          type="text"
                          value={defaultCfg.timezone}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              timezone: e.target.value,
                            }))
                          }
                          placeholder="UTC"
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Command Allowlist"
                        hint="comma-separated values"
                      >
                        <input
                          type="text"
                          value={defaultCfg.command_allowlist}
                          onChange={(e) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              command_allowlist: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Hooks Auto Accept">
                        <ToggleSwitch
                          checked={defaultCfg.hooks_auto_accept}
                          onChange={(v) =>
                            setDefaultCfg((p) => ({
                              ...p,
                              hooks_auto_accept: v,
                            }))
                          }
                        />
                      </ConfigField>
                      <div className="border-t border-zinc-200/60 dark:border-zinc-700/50 pt-4">
                        <h4 className="text-[9px] text-zinc-500 font-semibold mb-3">
                          Paste Collapse
                        </h4>
                        <div className="space-y-4 pl-0">
                          <ConfigField label="Paste Collapse Threshold">
                            <input
                              type="number"
                              value={defaultCfg.paste_collapse_threshold}
                              onChange={(e) =>
                                setDefaultCfg((p) => ({
                                  ...p,
                                  paste_collapse_threshold: Number(
                                    e.target.value,
                                  ),
                                }))
                              }
                              className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                            />
                          </ConfigField>
                          <ConfigField label="Paste Collapse Threshold Fallback">
                            <input
                              type="number"
                              value={
                                defaultCfg.paste_collapse_threshold_fallback
                              }
                              onChange={(e) =>
                                setDefaultCfg((p) => ({
                                  ...p,
                                  paste_collapse_threshold_fallback: Number(
                                    e.target.value,
                                  ),
                                }))
                              }
                              className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                            />
                          </ConfigField>
                          <ConfigField label="Paste Collapse Char Threshold">
                            <input
                              type="number"
                              value={defaultCfg.paste_collapse_char_threshold}
                              onChange={(e) =>
                                setDefaultCfg((p) => ({
                                  ...p,
                                  paste_collapse_char_threshold: Number(
                                    e.target.value,
                                  ),
                                }))
                              }
                              className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                            />
                          </ConfigField>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Agent ── */}
              {activeSection === "agent" && (
                <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center gap-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50 mb-5">
                      <Bot className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <h3 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                        Agent Configuration
                      </h3>
                    </div>
                    <div className="max-w-lg space-y-5">
                      <ConfigField label="Max Turns">
                        <input
                          type="number"
                          value={agentCfg.max_turns}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              max_turns: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Gateway Timeout"
                        hint="Seconds before gateway times out"
                      >
                        <input
                          type="number"
                          value={agentCfg.gateway_timeout}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              gateway_timeout: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Restart Drain Timeout">
                        <input
                          type="number"
                          value={agentCfg.restart_drain_timeout}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              restart_drain_timeout: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="API Max Retries">
                        <input
                          type="number"
                          value={agentCfg.api_max_retries}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              api_max_retries: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField
                        label="Service Tier"
                        hint="API service tier (OpenAI/Anthropic)"
                      >
                        <input
                          type="text"
                          value={agentCfg.service_tier}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              service_tier: e.target.value,
                            }))
                          }
                          placeholder="(none)"
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Tool Use Enforcement">
                        <select
                          value={agentCfg.tool_use_enforcement}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              tool_use_enforcement: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        >
                          <option value="auto">auto</option>
                          <option value="force">force</option>
                          <option value="none">none</option>
                        </select>
                      </ConfigField>
                      <ConfigField label="Task Completion Guidance">
                        <input
                          type="text"
                          value={agentCfg.task_completion_guidance}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              task_completion_guidance: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Environment Probe">
                        <input
                          type="text"
                          value={agentCfg.environment_probe}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              environment_probe: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Environment Hint">
                        <input
                          type="text"
                          value={agentCfg.environment_hint}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              environment_hint: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Gateway Timeout Warning">
                        <input
                          type="number"
                          value={agentCfg.gateway_timeout_warning}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              gateway_timeout_warning: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Clarify Timeout">
                        <input
                          type="number"
                          value={agentCfg.clarify_timeout}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              clarify_timeout: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Gateway Notify Interval">
                        <input
                          type="number"
                          value={agentCfg.gateway_notify_interval}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              gateway_notify_interval: Number(e.target.value),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Gateway Auto Continue Freshness">
                        <input
                          type="number"
                          value={agentCfg.gateway_auto_continue_freshness}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              gateway_auto_continue_freshness: Number(
                                e.target.value,
                              ),
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                      <ConfigField label="Image Input Mode">
                        <select
                          value={agentCfg.image_input_mode}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              image_input_mode: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        >
                          <option value="auto">auto</option>
                          <option value="base64">base64</option>
                          <option value="url">url</option>
                          <option value="none">none</option>
                        </select>
                      </ConfigField>
                      <ConfigField
                        label="Disabled Toolsets"
                        hint="comma-separated values"
                      >
                        <input
                          type="text"
                          value={agentCfg.disabled_toolsets}
                          onChange={(e) =>
                            setAgentCfg((p) => ({
                              ...p,
                              disabled_toolsets: e.target.value,
                            }))
                          }
                          className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl px-3.5 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        />
                      </ConfigField>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Settings ── */}
              {activeSection === "settings" && (
                <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center gap-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50 mb-5">
                      <Settings2 className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <h3 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                        Platform Settings
                      </h3>
                    </div>
                    <div className="max-w-md space-y-4">
                      <ToggleRow
                        label="Telemetry"
                        hint="Send anonymous usage data"
                        checked={telemetry}
                        onChange={setTelemetry}
                      />
                      <ToggleRow
                        label="Auto Backup"
                        hint="Automatically backup configuration on changes"
                        checked={autoBackup}
                        onChange={setAutoBackup}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* ── Appearance ── */}
              {activeSection === "appearance" && (
                <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-hidden">
                  <div className="p-5">
                    <div className="flex items-center gap-2 pb-4 border-b border-zinc-200/60 dark:border-zinc-700/50 mb-5">
                      <Palette className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <h3 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                        Theme
                      </h3>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      {THEMES.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-bold uppercase tracking-wider transition-all ${theme === t.id ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-500/20" : "border-zinc-200/60 dark:border-zinc-700/50 text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300"}`}
                        >
                          <span className={`w-3 h-3 rounded-full ${t.color}`} />
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

function ConfigField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-[9px] text-neutral-300 font-semibold">
          {label}
        </label>
      </div>
      {hint && <p className="text-[9px] text-neutral-300 mb-1">{hint}</p>}
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <span className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
          {label}
        </span>
        <p className="text-[10px] text-zinc-500">{hint}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${checked ? "bg-blue-600" : "bg-[#1F2C47]"}`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`}
        />
      </button>
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-5 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-[#1F2C47]"}`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`}
      />
    </button>
  );
}
