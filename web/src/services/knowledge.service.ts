import { API_BASE } from "./api";

export interface KnowledgeEntry {
  id: string;
  agent_name: string;
  content: string;
  category: string;
  score: number;
  source: string;
  created_at?: string;
}

export interface Candidate {
  id: string;
  agent_name: string;
  content: string;
  category: string;
  status: string;
  score: number;
  confidence: number;
  evidence_count: number;
  validation_reason?: string;
  created_at?: string;
}

export interface HealthStats {
  PENDING: number;
  APPROVED: number;
  REJECTED: number;
  PROMOTED: number;
  REVIEWING: number;
}

export const knowledgeService = {
  /** List promoted knowledge entries. */
  listEntries: async (agent?: string): Promise<KnowledgeEntry[]> => {
    const res = await fetch(`${API_BASE}/knowledge/entries${agent ? `?agent=${encodeURIComponent(agent)}` : ""}`);
    if (!res.ok) throw new Error("Failed to fetch entries");
    return res.json();
  },

  /** Search knowledge. */
  search: async (query: string, topN = 5) => {
    const res = await fetch(`${API_BASE}/knowledge/search?query=${encodeURIComponent(query)}&top_n=${topN}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to search");
    return res.json();
  },

  /** Upload a document. */
  upload: async (file: File, docType = "md") => {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    const res = await fetch(`${API_BASE}/knowledge/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Failed to upload");
    return res.json();
  },

  /** List pending candidates. */
  listPending: async (agent?: string): Promise<Candidate[]> => {
    const res = await fetch(`${API_BASE}/knowledge/pending${agent ? `?agent=${encodeURIComponent(agent)}` : ""}`);
    if (!res.ok) throw new Error("Failed to fetch pending");
    return res.json();
  },

  /** Approve a candidate. */
  approve: async (candidateId: string) => {
    const res = await fetch(`${API_BASE}/knowledge/approve/${encodeURIComponent(candidateId)}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to approve");
    return res.json();
  },

  /** Reject a candidate. */
  reject: async (candidateId: string, reason = "Rejected via dashboard") => {
    const res = await fetch(`${API_BASE}/knowledge/reject/${encodeURIComponent(candidateId)}?reason=${encodeURIComponent(reason)}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to reject");
    return res.json();
  },

  /** Export to markdown. */
  exportMd: async (agent: string) => {
    const res = await fetch(`${API_BASE}/knowledge/export?agent=${encodeURIComponent(agent)}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to export");
    return res.json();
  },

  /** Import from markdown. */
  importMd: async (agent: string) => {
    const res = await fetch(`${API_BASE}/knowledge/import?agent=${encodeURIComponent(agent)}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to import");
    return res.json();
  },

  /** Get health stats. */
  health: async (): Promise<HealthStats> => {
    const res = await fetch(`${API_BASE}/knowledge/health`);
    if (!res.ok) throw new Error("Failed to fetch health");
    return res.json();
  },

  /** Run curator tick. */
  sync: async (agent = "") => {
    const res = await fetch(`${API_BASE}/knowledge/sync?agent=${encodeURIComponent(agent)}`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to sync");
    return res.json();
  },
};
