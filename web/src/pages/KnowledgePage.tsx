import { useState, useEffect } from "react";
import {
  BookOpen,
  RefreshCw,
  Search,
  Upload,
  CheckCircle,
  XCircle,
  Download,
  Activity,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { knowledgeService, KnowledgeEntry, Candidate, HealthStats } from "../services/knowledge.service";

type Tab = "entries" | "documents" | "pending" | "health";

export const KnowledgePage = () => {
  const [tab, setTab] = useState<Tab>("entries");
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [health, setHealth] = useState<HealthStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[] | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      if (tab === "entries") {
        const data = await knowledgeService.listEntries();
        setEntries(data);
      } else if (tab === "pending") {
        const data = await knowledgeService.listPending();
        setCandidates(data);
      } else if (tab === "health") {
        const data = await knowledgeService.health();
        setHealth(data);
      }
    } catch {
      toast.error("Failed to load knowledge data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tab]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const data = await knowledgeService.search(searchQuery);
      setSearchResults(data.results || []);
    } catch {
      toast.error("Search failed");
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await knowledgeService.approve(id);
      toast.success("Candidate approved");
      loadData();
    } catch {
      toast.error("Failed to approve");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await knowledgeService.reject(id);
      toast.success("Candidate rejected");
      loadData();
    } catch {
      toast.error("Failed to reject");
    }
  };

  const handleUpload = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".md,.txt,.pdf";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        await knowledgeService.upload(file);
        toast.success("File uploaded and indexed");
      } catch {
        toast.error("Upload failed");
      }
    };
    input.click();
  };

  const handleExport = async () => {
    try {
      const data = await knowledgeService.exportMd();
      toast.success(`Exported ${data.exported} entries`);
    } catch {
      toast.error("Export failed");
    }
  };

  const handleSync = async () => {
    try {
      const data = await knowledgeService.sync();
      toast.success(`Sync: ${data.promoted} promoted`);
      loadData();
    } catch {
      toast.error("Sync failed");
    }
  };

  const healthScore = health?.PENDING !== undefined
    ? Math.round(
        (health.PROMOTED / Math.max(1, health.PENDING + health.APPROVED + health.REJECTED + health.PROMOTED)) * 100
      )
    : null;
  const healthLabel = healthScore === null ? "—" : healthScore >= 80 ? "Good" : healthScore >= 60 ? "Fair" : "Poor";
  const healthColor = healthScore === null ? "text-zinc-500" : healthScore >= 80 ? "text-emerald-500" : healthScore >= 60 ? "text-amber-500" : "text-rose-500";

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<BookOpen className="w-4 h-4 text-amber-400" />}
        title="Knowledge"
        description="Global knowledge base — promoted entries, document ingestion, and candidate queue"
      >
        <div className="flex items-center gap-2">
          <button onClick={handleSync} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-[11px] font-bold text-white transition-all uppercase">
            <Activity className="w-3.5 h-3.5" />
            <span>Sync</span>
          </button>
          <button onClick={loadData} disabled={loading} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 rounded-lg text-[11px] font-bold text-white transition-all uppercase">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </PageHeader>

      {/* Health status bar */}
      <div className="flex items-center gap-4 bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-4 py-3">
        <div className="flex items-center gap-2 text-[11px]">
          <span className="text-zinc-500">Health:</span>
          <span className={`font-semibold ${healthColor}`}>{healthLabel}</span>
          {healthScore !== null && <span className="text-[10px] text-zinc-400">({healthScore}/100)</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-zinc-200/60 dark:border-zinc-700/50 pb-2">
        {[
          { key: "entries" as Tab, label: "Knowledge Entries", icon: BookOpen },
          { key: "documents" as Tab, label: "Documents", icon: Upload },
          { key: "pending" as Tab, label: "Promotion Queue", icon: CheckCircle },
          { key: "health" as Tab, label: "Health", icon: Activity },
        ].map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-lg transition-all ${
              tab === t.key ? "bg-blue-600/15 text-blue-500" : "text-zinc-500 hover:text-zinc-700"
            }`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-500">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" /> <span>Loading...</span>
        </div>
      ) : tab === "entries" ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 mb-3">
            <div className="relative flex-1">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search knowledge..."
                className="w-full bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg pl-7 pr-3 py-1.5 text-[11px] text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400" />
            </div>
            <button onClick={handleSearch} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-[11px] font-semibold text-white">Search</button>
            <button onClick={handleExport} className="flex items-center gap-1 px-3 py-1.5 bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg text-[11px] text-zinc-600 hover:text-zinc-800">
              <Download className="w-3 h-3" /> Export
            </button>
          </div>
          {searchResults !== null ? (
            searchResults.length === 0 ? <p className="text-xs text-zinc-500 text-center py-8">No results</p> :
            searchResults.map((r, i) => (
              <div key={i} className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4">
                <span className="text-[10px] font-medium text-zinc-500">{r.category}</span>
                <p className="text-xs text-zinc-700 dark:text-zinc-300 mt-1">{r.content}</p>
              </div>
            ))
          ) : entries.length === 0 ? (
            <p className="text-xs text-zinc-500 text-center py-8">No knowledge entries. Upload a document or run a sync.</p>
          ) : entries.map((e) => (
            <div key={e.id} className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-medium text-zinc-500">{e.category}</span>
                <span className="text-[9px] text-zinc-400">score: {e.score.toFixed(2)}</span>
              </div>
              <p className="text-xs text-zinc-700 dark:text-zinc-300">{e.content}</p>
            </div>
          ))}
        </div>
      ) : tab === "documents" ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border">
          <Upload className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600">Document Ingestion</p>
          <p className="text-xs text-zinc-500 mt-1 mb-4">Upload Markdown, text, or PDF files for indexing</p>
          <button onClick={handleUpload} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white">Upload File</button>
        </div>
      ) : tab === "pending" ? (
        candidates.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-8">No pending candidates.</p>
        ) : candidates.map((c) => (
          <div key={c.id} className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-medium text-zinc-500">{c.category}</span>
                  <span className="text-[9px] text-zinc-400">confidence: {c.confidence}</span>
                </div>
                <p className="text-xs text-zinc-700 dark:text-zinc-300">{c.content}</p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => handleApprove(c.id)} className="p-1.5 text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors" title="Approve">
                  <CheckCircle className="w-4 h-4" />
                </button>
                <button onClick={() => handleReject(c.id)} className="p-1.5 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg transition-colors" title="Reject">
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))
      ) : tab === "health" && health ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(health).map(([status, count]) => (
            <div key={status} className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4 text-center">
              <span className="text-2xl font-bold text-zinc-700 dark:text-zinc-300">{count}</span>
              <p className="text-[10px] text-zinc-500 mt-1">{status}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default KnowledgePage;
