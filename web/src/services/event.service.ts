import { API_BASE } from "./api";

/* ── Types ───────────────────────────────────────────── */

export interface TimelineEvent {
  id: number;
  timestamp: string;
  category: string;
  event_name: string;
  agent_id: string | null;
  session_id: string | null;
  workflow_id: string | null;
  parent_event_id: string | null;
  payload: Record<string, unknown>;
}

export interface EventHistoryResponse {
  events: TimelineEvent[];
  total: number;
  limit: number;
  offset: number;
}

/* ── Helpers ─────────────────────────────────────────── */

function formatEventTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString();
  } catch {
    return ts;
  }
}

function eventIcon(event_name: string): string {
  if (event_name.includes("tool")) return "🔧";
  if (event_name.includes("memory") || event_name.includes("learned")) return "🧠";
  if (event_name.includes("skill")) return "⚡";
  if (event_name.includes("knowledge")) return "📚";
  if (event_name.includes("state")) return "📌";
  if (event_name.includes("retrieval")) return "🔍";
  if (event_name.includes("reasoning")) return "💭";
  if (event_name.includes("attention")) return "🎯";
  if (event_name.includes("execution")) return "▶️";
  if (event_name.includes("review")) return "🔬";
  if (event_name.includes("gateway")) return "🌐";
  if (event_name.includes("approval")) return "✅";
  if (event_name.includes("snapshot")) return "📸";
  return "📋";
}

function eventLabel(event_name: string): string {
  const labels: Record<string, string> = {
    tool_started: "Tool Started",
    tool_completed: "Tool Completed",
    tool_failed: "Tool Failed",
    memory_added: "Memory Added",
    memory_deleted: "Memory Deleted",
    memory_learned: "Memory Learned",
    user_preference_learned: "User Preference Learned",
    user_updated: "User Updated",
    skill_created: "Skill Created",
    skill_updated: "Skill Updated",
    skill_reactivated: "Skill Reactivated",
    skill_dormant: "Skill Dormant",
    knowledge_candidate_created: "Knowledge Candidate",
    knowledge_candidate_promoted: "Knowledge Promoted",
    knowledge_candidate_rejected: "Knowledge Rejected",
    knowledge_candidate_deferred: "Knowledge Deferred",
    knowledge_candidate_merged: "Knowledge Merged",
    state_updated: "State Updated",
    state_completed: "State Completed",
    state_blocked: "State Blocked",
    review_completed: "Review Completed",
    retrieval_started: "Retrieval Started",
    retrieval_completed: "Retrieval Completed",
    attention_ranked: "Attention Ranked",
    working_memory_created: "Working Memory Built",
    reasoning_started: "Reasoning Started",
    reasoning_completed: "Reasoning Completed",
    execution_started: "Execution Started",
    execution_completed: "Execution Completed",
    execution_failed: "Execution Failed",
    snapshot_created: "Snapshot Created",
    snapshot_invalidated: "Snapshot Invalidated",
    gateway_online: "Gateway Online",
    gateway_offline: "Gateway Offline",
    gateway_connected: "Gateway Connected",
    gateway_disconnected: "Gateway Disconnected",
    message_received: "Message Received",
    message_sent: "Message Sent",
    approval_requested: "Approval Requested",
    approval_granted: "Approval Granted",
    approval_denied: "Approval Denied",
  };
  return labels[event_name] || event_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function eventColor(event_name: string): string {
  if (event_name.includes("failed") || event_name.includes("offline") || event_name.includes("denied")) return "text-rose-500 border-l-rose-500";
  if (event_name.includes("completed") || event_name.includes("promoted") || event_name.includes("granted")) return "text-emerald-600 dark:text-emerald-400 border-l-emerald-500";
  if (event_name.includes("started") || event_name.includes("created") || event_name.includes("learned")) return "text-blue-600 dark:text-blue-400 border-l-blue-500";
  if (event_name.includes("updated") || event_name.includes("ranked") || event_name.includes("received")) return "text-purple-600 dark:text-purple-400 border-l-purple-500";
  return "text-zinc-600 dark:text-zinc-400 border-l-zinc-400";
}

/* ── SSE Client ──────────────────────────────────────── */

export function connectEventStream(
  onEvent: (event: TimelineEvent) => void,
  onError?: (err: Event) => void,
): EventSource {
  const base = API_BASE.replace("/api/v1", "");
  const es = new EventSource(`${base}/events/stream`);

  es.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as TimelineEvent;
      onEvent(data);
    } catch {
      // ignore parse errors
    }
  };

  es.onerror = (err) => {
    if (onError) onError(err);
  };

  return es;
}

/* ── History API ──────────────────────────────────────── */

export async function fetchEventHistory(
  limit = 50,
  offset = 0,
  category?: string,
  agent_id?: string,
): Promise<EventHistoryResponse | null> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (category) params.set("category", category);
  if (agent_id) params.set("agent_id", agent_id);

  try {
    const res = await fetch(`${API_BASE}/events/history?${params}`);
    if (!res.ok) return null;
    return (await res.json()) as EventHistoryResponse;
  } catch {
    return null;
  }
}

export { formatEventTime, eventIcon, eventLabel, eventColor };
