import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  MessageSquare,
  Send,
  Bot,
  Trash2,
  PanelLeft,
  PanelRight,
  Globe,
  Code,
  Settings2,
  Loader2,
  ChevronDown,
  Play,
  Square,
} from "lucide-react";
import { ChatSidebar } from "../components/ChatSidebar";
import { MessageBubble } from "../components/MessageBubble";

import { ToolButton } from "../components/ComposerTool";
import { PageHeader } from "../components/PageHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { toast } from "../components/ToastContainer";
import { useSessions, useSession } from "../hooks/useSession";
import { useAgents } from "../hooks/useAgents";
import type { Message } from "../types/agent";

/* ── Helpers ─────────────────────────────────────────────── */

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

/* ── Main Page ───────────────────────────────────────────── */

export const ChatPage = () => {
  const { sessions, isLoading: loadingSessions, deleteSession } = useSessions();
  const { agents, updateStatus } = useAgents();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const { messages, sendMessage, createSession, isCreating } = useSession(
    selectedSessionId ?? undefined,
  );
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(
    () => window.innerWidth >= 1024,
  );
  const [showTools, setShowTools] = useState(false);
  const [isSearchEnabled, setIsSearchEnabled] = useState(false);
  const [isCodingMode, setIsCodingMode] = useState(false);
  const [_isImageMode, _setIsImageMode] = useState(false);
  const [agentSelectorOpen, setAgentSelectorOpen] = useState(false);
  const [pendingSession, setPendingSession] = useState<{
    id: string;
    agent_name: string;
    title?: string;
    source?: string;
    updated_at?: string;
    message_count?: number;
  } | null>(null);
  // Optimistically track user messages sent while waiting for server response
  const [pendingMessages, setPendingMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const toolsRef = useRef<HTMLDivElement | null>(null);
  const agentSelectRef = useRef<HTMLDivElement | null>(null);

  // Selected session from list, with fallback to pending session data
  const selectedSession =
    sessions.find((s) => s.id === selectedSessionId) ?? pendingSession;
  const defaultAgent = agents[0]?.name ?? "";
  const [selectedAgent, setSelectedAgent] = useState<string>(defaultAgent);

  // Sync selectedAgent when session changes
  useEffect(() => {
    if (selectedSession?.agent_name) {
      setSelectedAgent(selectedSession.agent_name);
    }
  }, [selectedSession?.agent_name]);

  // Sync selectedAgent when agents list loads
  useEffect(() => {
    if (!selectedAgent && agents.length > 0) {
      setSelectedAgent(agents[0].name);
    }
  }, [agents, selectedAgent]);

  // Clear pendingSession once the sessions list has the new session
  useEffect(() => {
    if (pendingSession && sessions.find((s) => s.id === pendingSession.id)) {
      setPendingSession(null);
    }
  }, [sessions, pendingSession]);

  // Combine server messages + optimistic pending messages for display.
  // Deduplicate: if a pending message already exists in server data (by content+sender), skip it.
  const displayMessages = (() => {
    if (pendingMessages.length === 0) return messages;
    const existingKeys = new Set(
      messages.map((m) => `${m.sender ?? ""}:${m.content}`),
    );
    const uniquePending = pendingMessages.filter(
      (pm) => !existingKeys.has(`${pm.sender ?? ""}:${pm.content}`),
    );
    return uniquePending.length > 0
      ? [...messages, ...uniquePending]
      : messages;
  })();

  // Auto-scroll to bottom on new messages or when sending
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, sending]);

  // Close tools popover on outside click
  useEffect(() => {
    if (!showTools) return;
    const onPointerDown = (e: PointerEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
        setShowTools(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [showTools]);

  // Close agent selector on outside click
  useEffect(() => {
    if (!agentSelectorOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (
        agentSelectRef.current &&
        !agentSelectRef.current.contains(e.target as Node)
      ) {
        setAgentSelectorOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [agentSelectorOpen]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  // ── Helpers ──

  const ensureSessionAndSend = useCallback(
    async (text: string) => {
      if (!selectedAgent) return;

      let sessionId = selectedSessionId;

      // Auto-create session if none selected
      if (!sessionId) {
        try {
          const result = await createSession({
            agentName: selectedAgent,
          });
          sessionId = result.session.id;
          // Store session data immediately so header shows correct info
          setPendingSession({
            id: result.session.id,
            agent_name: result.session.agent_name,
            title: result.session.title,
            source: result.session.source,
            updated_at: result.session.updated_at,
            message_count: 0,
          });
          setSelectedSessionId(sessionId);
        } catch {
          toast.error("Failed to create session");
          return;
        }
      }

      // Optimistically add user message so it's visible immediately
      const optimisticMsg: Message = {
        session_id: sessionId,
        sender: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      setPendingMessages((prev) => [...prev, optimisticMsg]);
      setSending(true);
      setInput("");
      try {
        await sendMessage({
          sessionId,
          agentName: selectedAgent,
          message: text,
        });
      } catch {
        // Remove optimistic message on failure
        setPendingMessages((prev) => prev.filter((m) => m !== optimisticMsg));
        setInput(text);
        toast.error("Failed to send message");
      } finally {
        setSending(false);
      }
    },
    [selectedSessionId, selectedAgent, createSession, sendMessage],
  );

  const handleSend = useCallback(
    async (textOverride?: string) => {
      const text = (textOverride ?? input).trim();
      if (!text || !selectedAgent || sending || isCreating) return;
      await ensureSessionAndSend(text);
    },
    [input, selectedAgent, sending, isCreating, ensureSessionAndSend],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteSession(deleteTarget);
    if (selectedSessionId === deleteTarget) setSelectedSessionId(null);
    setDeleteTarget(null);
  };

  const handleNewSession = () => {
    setSelectedSessionId(null);
    setPendingSession(null);
    setPendingMessages([]);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const hasConversation = selectedSessionId !== null;

  // Agent selector component
  const AgentSelector = () => (
    <div className="relative" ref={agentSelectRef}>
      <button
        onClick={() => setAgentSelectorOpen(!agentSelectorOpen)}
        className="flex items-center gap-1.5 text-[10px] font-medium text-neutral-300 bg-stone-100 dark:bg-zinc-800 px-2 py-1 rounded-lg border border-zinc-200/60 dark:border-zinc-700/50 hover:border-zinc-300 dark:hover:border-zinc-600 transition-all"
      >
        <Bot className="w-3 h-3" />
        <span>
          {agents.find((a) => a.name === selectedAgent)?.name ||
            selectedAgent ||
            "Select agent"}
        </span>
        <ChevronDown className="w-3 h-3" />
      </button>
      {agentSelectorOpen && (
        <div className="absolute right-0 top-full mt-1 z-20 min-w-[200px] bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-xl py-1 shadow-2xl">
          {agents.length === 0 ? (
            <div className="px-3 py-2 text-[10px] text-zinc-500">No agents</div>
          ) : (
            agents.map((agent) => (
              <div
                key={agent.name}
                className={`flex items-center gap-1 px-1 ${
                  selectedAgent === agent.name
                    ? "bg-zinc-200/50 dark:bg-zinc-700/50"
                    : "hover:bg-zinc-100 dark:hover:bg-zinc-700/30"
                }`}
              >
                <button
                  onClick={() => {
                    setSelectedAgent(agent.name);
                    setAgentSelectorOpen(false);
                  }}
                  className="flex-1 text-left px-2 py-1.5 text-[11px] font-medium transition-colors flex items-center gap-2 min-w-0"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      agent.status === "running"
                        ? "bg-emerald-500"
                        : "bg-zinc-400"
                    }`}
                  />
                  <span className="truncate flex-1">{agent.name}</span>
                  <span className="text-[9px] text-zinc-400 shrink-0">
                    {agent.model_provider}
                  </span>
                </button>
                <button
                  onClick={async () => {
                    const action =
                      agent.status === "running" ? "stop" : "start";
                    try {
                      await updateStatus({ name: agent.name, action });
                      toast.success(`${agent.name} ${action}ed`);
                    } catch {
                      toast.error(`Failed to ${action} ${agent.name}`);
                    }
                  }}
                  className={`p-1.5 rounded-lg shrink-0 transition-colors ${
                    agent.status === "running"
                      ? "text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20"
                      : "text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
                  }`}
                  title={
                    agent.status === "running" ? "Stop agent" : "Start agent"
                  }
                >
                  {agent.status === "running" ? (
                    <Square className="w-3 h-3" />
                  ) : (
                    <Play className="w-3 h-3" />
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 h-full animate-fadeIn">
      <PageHeader
        icon={<MessageSquare className="w-4 h-4 text-blue-400" />}
        title="Chat"
        description="Interactive agent conversation sessions"
        hideDescription
      >
        {agents.length > 0 && (
          <div className="flex items-center gap-2">
            {/* Session sidebar toggle — visible on mobile */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-full text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all lg:hidden"
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? (
                <PanelLeft className="w-4 h-4" />
              ) : (
                <PanelRight className="w-4 h-4" />
              )}
            </button>
            <AgentSelector />
          </div>
        )}
      </PageHeader>

      {agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center p-12 bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50">
          <div className="p-4 bg-stone-100 dark:bg-zinc-800 rounded-full border border-zinc-200/60 dark:border-zinc-700/50 mb-4">
            <Bot className="w-10 h-10 text-neutral-300" />
          </div>
          <h3 className="text-base font-bold text-zinc-700 dark:text-zinc-300">
            No agents configured
          </h3>
          <p className="text-xs text-zinc-500 mt-1 max-w-sm">
            Create an agent first to start a chat conversation.
          </p>
          <Link
            to="/agents"
            className="mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-semibold text-white transition-all shadow-md"
          >
            Go to Agents
          </Link>
        </div>
      ) : (
        <div className="flex flex-1 max-h-[calc(100dvh-10rem)] md:max-h-[calc(100dvh-14rem)] gap-4">
          <ChatSidebar
            sessions={sessions}
            loadingSessions={loadingSessions}
            selectedSessionId={selectedSessionId}
            sidebarOpen={sidebarOpen}
            onSelectSession={setSelectedSessionId}
            onNewSession={handleNewSession}
            onClose={() => setSidebarOpen(false)}
            onOpen={() => setSidebarOpen(true)}
          />

          {/* ── Main chat area ── */}
          <div className="flex-1 flex flex-col max-h-[calc(100dvh-10rem)] bg-neutral-200/70 dark:bg-neutral-900/50 rounded-3xl border border-zinc-200/50 dark:border-zinc-800/50 overflow-hidden">
            {hasConversation ? (
              <>
                {/* Chat header */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-200/50 dark:border-zinc-800/50 bg-neutral-100/50 dark:bg-neutral-900/80">
                  <div className="flex items-center gap-3 min-w-0">
                    <Bot className="w-5 h-5 text-neutral-300 shrink-0" />
                    <div className="min-w-0">
                      <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100 truncate">
                        {selectedSession?.agent_name ?? "Agent"}
                      </h2>
                      <p className="text-[10px] text-neutral-300">
                        {selectedSession?.message_count ?? 0} messages
                        {selectedSession?.updated_at &&
                          ` • ${timeAgo(selectedSession.updated_at)}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-medium text-neutral-300 bg-stone-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-200/60 dark:border-zinc-700/50">
                      {selectedSession?.source ?? "local"}
                    </span>
                    <button
                      onClick={() => setDeleteTarget(selectedSessionId)}
                      className="p-1 text-neutral-300 hover:text-rose-500 transition-colors"
                      title="Delete session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-4">
                  <div className="max-w-3xl mx-auto space-y-5">
                    {displayMessages.length === 0 && !sending ? (
                      <div className="flex flex-col items-center justify-center py-16 text-center">
                        <MessageSquare className="w-10 h-10 text-zinc-300 dark:text-zinc-600 mb-3" />
                        <p className="text-sm text-zinc-500">
                          Send a message to start the conversation.
                        </p>
                      </div>
                    ) : (
                      displayMessages.map((msg, i) => (
                        <MessageBubble
                          key={msg.id || `pending-${i}`}
                          message={{ ...msg, sender: msg.sender as string }}
                        />
                      ))
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </div>

                {/* Composer */}
                <Composer
                  value={input}
                  onChange={setInput}
                  onSend={() => handleSend()}
                  onKeyDown={handleKeyDown}
                  sending={sending}
                  disabled={!selectedAgent}
                  isSearchEnabled={isSearchEnabled}
                  setIsSearchEnabled={setIsSearchEnabled}
                  isCodingMode={isCodingMode}
                  setIsCodingMode={setIsCodingMode}
                  showTools={showTools}
                  setShowTools={setShowTools}
                  toolsRef={toolsRef}
                  inputRef={inputRef}
                />
              </>
            ) : (
              /* ── Welcome screen ── */
              <div className="flex-1 flex flex-col items-center justify-center px-4">
                <div className="flex-1 flex flex-col items-center justify-center w-full max-w-2xl mx-auto space-y-8">
                  <div className="w-full max-w-2xl flex flex-col items-start space-y-3 px-2">
                    <div className="flex items-center gap-3 mt-24">
                      <div className="p-2 rounded-xl bg-gradient-to-br  from-amber-500/80 to-amber-600/80 shadow-lg shadow-indigo-500/20">
                        <MessageSquare className="w-5 h-5 text-stone-200" />
                      </div>
                      <h1 className="text-3xl font-semibold tracking-tight text-zinc-800 dark:text-zinc-100">
                        <span className="bg-gradient-to-r from-amber-500 to-amber-600 bg-clip-text text-transparent">
                          Hi there
                        </span>
                      </h1>
                    </div>
                    <p className="text-3xl font-medium text-stone-500 dark:text-stone-400">
                      How can I help you today?
                    </p>
                  </div>

                  {/* Start new conversation button */}
                  {sessions.length > 0 && (
                    <button
                      onClick={() =>
                        setSelectedSessionId(sessions[0]?.id ?? null)
                      }
                      className="text-xs text-blue-600/50 dark:text-blue-400/50 hover:underline"
                    >
                      Or continue our last conversation
                    </button>
                  )}
                </div>

                {/* Composer on welcome screen */}
                <div className="w-full max-w-2xl mx-auto pb-6 pt-8">
                  <Composer
                    value={input}
                    onChange={setInput}
                    onSend={() => handleSend()}
                    onKeyDown={handleKeyDown}
                    sending={sending}
                    disabled={!selectedAgent}
                    isSearchEnabled={isSearchEnabled}
                    setIsSearchEnabled={setIsSearchEnabled}
                    isCodingMode={isCodingMode}
                    setIsCodingMode={setIsCodingMode}
                    showTools={showTools}
                    setShowTools={setShowTools}
                    toolsRef={toolsRef}
                    inputRef={inputRef}
                    placeholder={
                      selectedAgent
                        ? `Ask ${selectedAgent}...`
                        : "Select an agent to start chatting..."
                    }
                  />
                </div>
                <div className="h-8 shrink-0" />
              </div>
            )}
          </div>
        </div>
      )}

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
};

export default ChatPage;

/* ── Composer ── */

function Composer({
  value,
  onChange,
  onSend,
  onKeyDown,
  sending,
  disabled,
  isSearchEnabled,
  setIsSearchEnabled,
  isCodingMode,
  setIsCodingMode,
  showTools,
  setShowTools,
  toolsRef,
  inputRef,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  sending: boolean;
  disabled?: boolean;
  isSearchEnabled: boolean;
  setIsSearchEnabled: (v: boolean) => void;
  isCodingMode: boolean;
  setIsCodingMode: (v: boolean) => void;
  showTools: boolean;
  setShowTools: (v: boolean) => void;
  toolsRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  placeholder?: string;
}) {
  return (
    <div className="border-none px-4 pb-4 pt-2">
      <div className="mx-auto max-w-3xl">
        <div className="flex flex-col rounded-3xl border border-zinc-200 dark:border-neutral-700/50 bg-neutral-300 dark:bg-neutral-900 shadow-inner transition-all duration-200 relative">
          <div className="flex-1 px-4 pt-4 pb-2">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                placeholder ??
                (disabled ? "No running agent available" : "Ask Orcanium...")
              }
              rows={1}
              disabled={disabled}
              className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-neutral-300/50 dark:placeholder:text-zinc-500/50 min-h-[24px] leading-6 text-zinc-800 dark:text-zinc-200 disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between px-3 pb-3 pl-4">
            <div className="flex items-center gap-1">
              {/* Tools popover */}
              <div className="relative" ref={toolsRef}>
                <button
                  onClick={() => setShowTools(!showTools)}
                  className="p-2 rounded-full text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-200/50 dark:hover:bg-zinc-800 transition-all"
                  aria-label="Tools"
                >
                  <Settings2 className="w-4 h-4" />
                </button>
                {showTools && (
                  <div className="absolute bottom-full left-0 mb-2 w-44 p-2 rounded-2xl bg-neutral-200/90 dark:bg-neutral-900 border border-zinc-300/50 dark:border-zinc-800/50 shadow-lg z-10">
                    <div className="grid gap-1">
                      <ToolButton
                        active={isSearchEnabled}
                        onClick={() => setIsSearchEnabled(!isSearchEnabled)}
                        icon={<Globe className="w-4 h-4" />}
                        label="Search"
                      />
                      <ToolButton
                        active={isCodingMode}
                        onClick={() => setIsCodingMode(!isCodingMode)}
                        icon={<Code className="w-4 h-4" />}
                        label="Coding mode"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isSearchEnabled && (
                <span className="flex items-center gap-1 text-[8px] bg-cyan-100/50 text-cyan-600 dark:bg-cyan-900/50 dark:text-cyan-300 px-2 py-0.5 rounded-full font-semibold tracking-wider">
                  <Globe className="w-3 h-3" /> Search
                </span>
              )}
              {isCodingMode && (
                <span className="flex items-center gap-1 text-[8px] bg-indigo-100/50 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-300 px-2 py-0.5 rounded-full font-semibold tracking-wider">
                  <Code className="w-3 h-3" /> Code
                </span>
              )}

              <button
                onClick={onSend}
                disabled={!value.trim() || sending || disabled}
                className={`rounded-full h-9 w-9 flex items-center justify-center transition-all ${
                  value.trim() && !disabled
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-500 hover:bg-zinc-800 dark:hover:bg-zinc-200"
                    : "bg-zinc-200 dark:bg-zinc-600 text-neutral-300 dark:text-zinc-100"
                }`}
                aria-label="Send message"
              >
                {sending ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>
        <p className="text-center text-[7px] text-neutral-400/50 mt-4">
          AI can make mistakes, double check important information.
        </p>
      </div>
    </div>
  );
}
