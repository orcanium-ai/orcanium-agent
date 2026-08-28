import { useState, useEffect } from "react";
import {
  Code,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  Search,
  BookOpen,
  Eye,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { toast } from "../components/ToastContainer";
import { useAgents } from "../hooks/useAgents";
import { skillService, Skill } from "../services/skill.service";

export const SkillsPage = () => {
  const { agents } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [detailSkill, setDetailSkill] = useState<Skill | null>(null);

  useEffect(() => {
    if (!selectedAgent && agents.length > 0) {
      setSelectedAgent(agents[0].name);
    }
  }, [agents, selectedAgent]);

  const loadSkills = async (agent: string) => {
    if (!agent) return;
    setLoading(true);
    try {
      const data = await skillService.list(agent);
      setSkills(data.skills);
    } catch {
      setSkills([]);
      toast.error("Failed to load skills");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkills(selectedAgent);
  }, [selectedAgent]);

  const handleToggle = async (skill: Skill) => {
    if (toggling.has(skill.id)) return;
    setToggling((prev) => new Set(prev).add(skill.id));
    const newEnabled = skill.state !== "ACTIVE";
    try {
      await skillService.toggle(selectedAgent, skill.id, newEnabled);
      setSkills((prev) =>
        prev.map((s) =>
          s.id === skill.id
            ? { ...s, state: newEnabled ? "ACTIVE" : "DORMANT" }
            : s,
        ),
      );
      toast.success(`${skill.title} ${newEnabled ? "enabled" : "disabled"}`);
    } catch {
      toast.error(`Failed to toggle ${skill.title}`);
    } finally {
      setToggling((prev) => {
        const next = new Set(prev);
        next.delete(skill.id);
        return next;
      });
    }
  };

  const categories = [...new Set(skills.map((s) => s.executable ? "executable" : "cognitive"))].sort();
  const enabledCount = skills.filter((s) => s.state === "ACTIVE").length;

  const displaySkills = skills
    .filter((s) => !activeCategory || (activeCategory === "executable" ? s.executable : !s.executable))
    .filter(
      (s) =>
        !search ||
        s.title.toLowerCase().includes(search.toLowerCase()) ||
        s.description.toLowerCase().includes(search.toLowerCase()),
    );

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 animate-fadeIn">
      <PageHeader
        icon={<Code className="w-4 h-4 text-blue-400" />}
        title="Skills"
        description="Per-agent skill registry — procedural capabilities and knowledge"
      >
        <button
          onClick={() => loadSkills(selectedAgent)}
          disabled={loading || !selectedAgent}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 rounded-lg text-[11px] font-bold text-white transition-all uppercase"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </PageHeader>

      <div className="flex items-center gap-3 bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-4 py-3">
        <label className="text-[10px] font-medium text-neutral-300 uppercase tracking-wider">
          Agent
        </label>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg px-3 py-1.5 text-xs text-zinc-700 dark:text-zinc-300 focus:outline-none focus:border-blue-400"
        >
          {agents.length === 0 && <option value="">No agents</option>}
          {agents.map((a) => (
            <option key={a.name} value={a.name}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-[10px] text-zinc-500">
            <span className="font-semibold">
              {enabledCount}/{skills.length} enabled
            </span>
            <span className="text-slate-600">·</span>
            <span>{categories.length} categories</span>
          </div>
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search skills..."
              className="w-48 bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 rounded-lg pl-7 pr-3 py-1.5 text-[11px] text-zinc-700 dark:text-zinc-300 placeholder-zinc-400 focus:outline-none focus:border-blue-400"
            />
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap mt-3">
          <button
            onClick={() => setActiveCategory(null)}
            className={`text-[10px] font-medium px-2.5 py-1 rounded-lg border transition-all ${
              !activeCategory
                ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30"
                : "text-zinc-500 border-zinc-200/60 dark:border-zinc-700/50 hover:text-zinc-700"
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() =>
                setActiveCategory(activeCategory === cat ? null : cat)
              }
              className={`text-[10px] font-medium px-2.5 py-1 rounded-lg border transition-all ${
                activeCategory === cat
                  ? "bg-blue-600/15 text-blue-500 dark:text-blue-400 border-blue-500/30"
                  : "text-zinc-500 border-zinc-200/60 dark:border-zinc-700/50 hover:text-zinc-700"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-500">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          <span className="text-sm">Loading skills for {selectedAgent}...</span>
        </div>
      ) : !selectedAgent ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50">
          <Code className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600 dark:text-neutral-300">
            Select an agent to view its skills
          </p>
        </div>
      ) : displaySkills.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-500 bg-stone-100/80 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200/60 dark:border-zinc-700/50">
          <BookOpen className="w-10 h-10 mb-3 opacity-30" />
          <p className="text-sm font-semibold text-zinc-600 dark:text-neutral-300">
            {search ? "No matching skills" : "No skills registered for this agent"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {search ? "Try a different search term" : "Skills are learned from experience during conversations"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {displaySkills.map((skill) => {
            const isActive = skill.state === "ACTIVE";
            return (
              <div
                key={skill.id}
                className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 p-4 flex items-start gap-4 hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                      {skill.title}
                    </span>
                    <span
                      className={`text-[9px] font-medium px-1.5 py-0.5 rounded border ${
                        isActive
                          ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                          : "text-zinc-500 bg-slate-500/10 border-slate-500/20"
                      }`}
                    >
                      {skill.state}
                    </span>
                    {skill.executable && (
                      <span className="text-[9px] font-medium px-1.5 py-0.5 rounded border text-purple-500 bg-purple-500/10 border-purple-500/20">
                        Executable
                      </span>
                    )}
                  </div>
                  {skill.description && (
                    <p className="text-[11px] text-neutral-300 mt-1 line-clamp-2">
                      {skill.description}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-[9px] text-zinc-500">
                    {skill.use_count > 0 && (
                      <span>Used {skill.use_count} times</span>
                    )}
                    {skill.last_used && (
                      <span>Last used: {new Date(skill.last_used).toLocaleDateString()}</span>
                    )}
                    <span>Importance: {skill.importance.toFixed(2)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => setDetailSkill(skill)}
                    className="p-1.5 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors"
                    title="View details"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleToggle(skill)}
                    disabled={toggling.has(skill.id)}
                    className="p-1.5 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
                    title={isActive ? "Disable" : "Enable"}
                  >
                    {isActive ? (
                      <ToggleRight className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <ToggleLeft className="w-4 h-4 text-zinc-500" />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {detailSkill && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDetailSkill(null);
          }}
        >
          <div className="bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-lg rounded-2xl p-6 shadow-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-100">
                  {detailSkill.title}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono">
                  {detailSkill.id}
                </span>
              </div>
              <button
                onClick={() => setDetailSkill(null)}
                className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-[11px]">
              {detailSkill.description && (
                <div>
                  <label className="text-[9px] font-medium text-neutral-300 block mb-1">Description</label>
                  <p className="text-zinc-600 dark:text-zinc-300">{detailSkill.description}</p>
                </div>
              )}
              {detailSkill.workflow && (
                <div>
                  <label className="text-[9px] font-medium text-neutral-300 block mb-1">Workflow</label>
                  <pre className="text-zinc-600 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-900 rounded-lg p-3 text-[10px] font-mono whitespace-pre-wrap">{detailSkill.workflow}</pre>
                </div>
              )}
              <div className="flex items-center gap-4 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/50">
                <span className="text-zinc-500">State: <strong>{detailSkill.state}</strong></span>
                <span className="text-zinc-500">Executable: <strong>{detailSkill.executable ? "Yes" : "No"}</strong></span>
                <span className="text-zinc-500">Uses: <strong>{detailSkill.use_count}</strong></span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillsPage;
