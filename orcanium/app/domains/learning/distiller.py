"""Memory Distiller — increases information density, NOT size reduction.

New concept (replaces deprecated "compression" focus):
    Increase Information Density

Responsibilities:
    - merge duplicates
    - consolidate related facts
    - improve retrieval quality
    - promote durable knowledge
    - reduce noise

Never invents information.
Preserves user facts, decisions, project context, preferences.

Architecture:
    Background Review → Memory Store → Memory Distiller → Knowledge Candidates → Future Retrieval

BOUNDARY (enforced):
    ✓ Consolidate memories
    ✓ Merge duplicates
    ✓ Create knowledge candidates
    ✓ Improve information density
    ✗ NEVER summarize chat history
    ✗ NEVER modify conversation buffers
    ✗ NEVER perform context compression

This is DISTINCT from ContextCompressor:
    MemoryDistiller = long-term memory optimization
    ContextCompressor = short-term conversation management

    They MUST NOT overlap.
"""

import datetime
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from orcanium.app.domains.memory.store import MemoryEntry, MemoryStore
from orcanium.app.model.model_gateway import (
    clear_llm_context,
    set_llm_context,
    set_llm_purpose,
)

logger = logging.getLogger(__name__)

# ── Protected categories (never touched by distiller) ─────────

PROTECTED_CATEGORIES: Set[str] = {"USER_FACT", "PREFERENCE"}

# ── Distillable categories ────────────────────────────────────

DISTILLABLE_CATEGORIES: Set[str] = {"CONTEXT", "PROJECT", "DECISION", "LEARNING"}

# ── Distillation thresholds ───────────────────────────────────

TRIGGER_ENTRY_COUNT = 50
TRIGGER_SIZE_BYTES = 8192  # 8KB

# ── LLM Distillation prompts ──────────────────────────────────

DISTILLATION_SYSTEM_PROMPT = (
    "You are the Orcanium Memory Distiller, a cognitive compression engine.\n\n"
    "Your task is to transform accumulated memories into fewer, higher-value memories.\n\n"
    "Rules:\n"
    "1. Preserve ALL important facts — never remove information that could be useful.\n"
    "2. Merge duplicate and closely related entries into single, denser entries.\n"
    "3. Compress episodic/temporal details into durable knowledge.\n"
    "4. Never invent information — synthesize only what the source entries contain.\n"
    "5. Never remove project context, user facts, decisions, or preferences.\n"
    "6. Return entries in the format: § [CATEGORY] Content\n\n"
    "Output ONLY the distilled entries, one per line. No explanations."
)

DISTILL_GROUP_PROMPT = (
    "Consolidate these related memory entries into FEWER, HIGHER-VALUE entries.\n\n"
    "Entries to consolidate:\n{entries}\n\n"
    "Requirements:\n"
    "- Merge duplicates into one entry.\n"
    "- Merge closely related information.\n"
    "- Compress episodic details into durable facts.\n"
    "- Keep information density high.\n"
    "- Use the same category for each output entry.\n"
    "- Output one entry per line in format: § [CATEGORY] Content\n"
    "- If nothing meaningful to consolidate, return the entries as-is."
)

PROJECT_DISTILL_PROMPT = (
    "Distill these project-related memory entries into a single high-density project memory.\n\n"
    "Project entries:\n{entries}\n\n"
    "Requirements:\n"
    "- Combine all project facts into ONE entry with category [PROJECT].\n"
    "- Capture: project purpose, current status, decisions made, direction.\n"
    "- Be comprehensive but concise — one dense paragraph.\n"
    "- Output format: § [PROJECT] <one dense paragraph>\n"
    "- Never invent information not present in the source entries."
)


# ── Data models ───────────────────────────────────────────────


@dataclass
class DistilledMemory:
    """A distilled memory entry with provenance tracking."""

    content: str
    category: str
    source_ids: List[str] = field(default_factory=list)
    source_count: int = 0
    distilled_at: Optional[datetime.datetime] = None

    def __post_init__(self):
        if self.distilled_at is None:
            self.distilled_at = datetime.datetime.utcnow()
        self.source_count = len(self.source_ids)


@dataclass
class DistillationReport:
    """Report generated after each distillation run."""

    target: str = ""
    timestamp: str = ""
    status: str = ""
    original_entry_count: int = 0
    distilled_entry_count: int = 0
    compression_ratio: float = 0.0
    merged_groups: int = 0
    removed_duplicates: int = 0
    preserved_entries: int = 0
    backup_path: str = ""
    errors: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "timestamp": self.timestamp,
            "status": self.status,
            "original_entry_count": self.original_entry_count,
            "distilled_entry_count": self.distilled_entry_count,
            "compression_ratio": self.compression_ratio,
            "merged_groups": self.merged_groups,
            "removed_duplicates": self.removed_duplicates,
            "preserved_entries": self.preserved_entries,
            "backup_path": self.backup_path,
            "errors": self.errors,
            "details": self.details,
        }


# ── Helper — content-based entry ID ───────────────────────────


def _entry_id(entry: MemoryEntry) -> str:
    """Generate a stable pseudo-ID for an entry based on content."""
    import hashlib

    raw = f"{entry.category}:{entry.content}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Memory Distiller ──────────────────────────────────────────


class MemoryDistiller:
    """Cognitive compression system for memory entries.

    Transforms accumulated entries into higher-quality, denser memory
    through rule-based deduplication and LLM-powered consolidation.
    """

    def __init__(self, store: MemoryStore, model_gateway=None):
        self._store = store
        self._model_gateway = model_gateway
        self._agent_name = getattr(store, "_agent_name", "system")
        self._report = DistillationReport()

    def _generate_distillation(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        config: Dict[str, Any],
    ) -> str:
        set_llm_context(self._agent_name)
        set_llm_purpose("DISTILLATION")
        try:
            return self._model_gateway.generate(
                messages=messages,
                provider=provider,
                model=model,
                config=config,
            )
        finally:
            clear_llm_context()

    # ── Entry source tracking ──

    def _build_entry_map(self, entries: List[MemoryEntry]) -> Dict[str, MemoryEntry]:
        """Build {entry_id: entry} map for provenance tracking."""
        return {_entry_id(e): e for e in entries}

    def _source_ids_from_entries(self, entries: List[MemoryEntry]) -> List[str]:
        """Get source IDs for a list of entries."""
        return [_entry_id(e) for e in entries]

    # ── Level 1: Duplicate Consolidation ──

    def _deduplicate(self, entries: List[MemoryEntry]) -> Tuple[List[MemoryEntry], int]:
        """Remove exact content duplicates. Returns (deduped, removed_count)."""
        seen: Dict[str, MemoryEntry] = {}
        result: List[MemoryEntry] = []
        removed = 0

        for entry in entries:
            key = entry.content.strip().lower()
            if key not in seen:
                seen[key] = entry
                result.append(entry)
            else:
                removed += 1

        return result, removed

    # ── Level 2: Related Fact Consolidation ──

    def _consolidate_related(self, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        """Merge entries in the same category that share significant word overlap."""
        from collections import defaultdict

        result: List[MemoryEntry] = []
        # Group by category
        by_category: Dict[str, List[MemoryEntry]] = defaultdict(list)
        for e in entries:
            by_category[e.category].append(e)

        for cat, group in by_category.items():
            if cat in PROTECTED_CATEGORIES:
                result.extend(group)
                continue

            if len(group) <= 2:
                result.extend(group)
                continue

            # Try to merge entries that share key nouns
            merged: List[MemoryEntry] = []
            used = set()

            for i, a in enumerate(group):
                if i in used:
                    continue
                a_words = set(a.content.lower().split())
                a_nouns = {w for w in a_words if len(w) > 4}

                related: List[int] = []
                for j, b in enumerate(group):
                    if j <= i or j in used:
                        continue
                    b_words = set(b.content.lower().split())
                    b_nouns = {w for w in b_words if len(w) > 4}
                    overlap = a_nouns & b_nouns
                    if len(overlap) >= 2:
                        related.append(j)

                if related:
                    self._report.details.append(
                        f"Level 2: Merged {len(related) + 1} related '{cat}' entries"
                    )
                    self._report.merged_groups += 1

                    # Combine all related entries
                    combined_entries = [a] + [group[j] for j in related]
                    combined_text = " | ".join(e.content for e in combined_entries)
                    merged.append(
                        MemoryEntry(
                            content=combined_text,
                            category=cat,
                            origin="distiller",
                        )
                    )
                    used.add(i)
                    used.update(related)
                else:
                    merged.append(a)

            result.extend(merged)

        return result

    # ── Level 3: Episodic Compression (LLM-powered) ──

    def _compress_episodic(
        self, entries: List[MemoryEntry], provider: str, model: str
    ) -> List[MemoryEntry]:
        """Use LLM to compress episodic entries into durable knowledge."""
        if not self._model_gateway:
            return entries

        result: List[MemoryEntry] = []
        by_category: Dict[str, List[MemoryEntry]] = {}
        for e in entries:
            if e.category not in by_category:
                by_category[e.category] = []
            by_category[e.category].append(e)

        for cat, group in by_category.items():
            if cat in PROTECTED_CATEGORIES or len(group) < 4:
                result.extend(group)
                continue

            # Format entries for the prompt
            entries_text = "\n".join(f"- [{e.category}] {e.content}" for e in group)

            try:
                prompt = DISTILL_GROUP_PROMPT.format(entries=entries_text)
                response = self._generate_distillation(
                    messages=[
                        {"role": "system", "content": DISTILLATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    provider=provider,
                    model=model,
                    config={"temperature": 0.2, "max_tokens": 2000},
                )

                distilled = self._parse_llm_response(response, default_category=cat)
                if distilled:
                    self._report.details.append(
                        f"Level 3: Compressed {len(group)} '{cat}' episodes into {len(distilled)} entries"
                    )
                    self._report.merged_groups += 1
                    result.extend(distilled)
                else:
                    result.extend(group)
            except Exception as e:
                logger.warning(f"Level 3 distillation failed for '{cat}': {e}")
                self._report.errors.append(f"Level 3 failed for {cat}: {e}")
                result.extend(group)

        return result

    # ── Level 4: Project Distillation (LLM-powered) ──

    def _distill_project(
        self, entries: List[MemoryEntry], provider: str, model: str
    ) -> List[MemoryEntry]:
        """Use LLM to distill project entries into a single high-density entry."""
        if not self._model_gateway:
            return entries

        project_entries = [e for e in entries if e.category == "PROJECT"]
        if len(project_entries) < 3:
            return entries

        other_entries = [e for e in entries if e.category != "PROJECT"]

        entries_text = "\n".join(f"- {e.content}" for e in project_entries)

        try:
            prompt = PROJECT_DISTILL_PROMPT.format(entries=entries_text)
            response = self._generate_distillation(
                messages=[
                    {"role": "system", "content": DISTILLATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                provider=provider,
                model=model,
                config={"temperature": 0.2, "max_tokens": 1000},
            )

            parsed = self._parse_llm_response(response, default_category="PROJECT")
            if parsed:
                self._report.details.append(
                    f"Level 4: Distilled {len(project_entries)} project entries into {len(parsed)}"
                )
                self._report.merged_groups += 1
                return other_entries + parsed
        except Exception as e:
            logger.warning(f"Level 4 project distillation failed: {e}")
            self._report.errors.append(f"Level 4 project distillation failed: {e}")

        return entries

    # ── LLM Response Parsing ──

    def _parse_llm_response(
        self, response: str, default_category: str = "CONTEXT"
    ) -> List[MemoryEntry]:
        """Parse LLM response into MemoryEntry list."""
        entries: List[MemoryEntry] = []
        for line in response.strip().split("\n"):
            line = line.strip()
            entry = MemoryEntry.parse(line)
            if entry:
                entry.origin = "distiller"
                entries.append(entry)
        return entries

    # ── Main Distillation Pipeline ──

    def run(
        self,
        target: str = "memory",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> DistillationReport:
        """Run the full distillation pipeline on the target store.

        Args:
            target: "memory" or "user"
            provider: LLM provider for Level 3-4 (e.g. "openai")
            model: LLM model for Level 3-4 (e.g. "gpt-4")

        Returns:
            DistillationReport with results
        """
        self._report = DistillationReport(
            target=target,
            timestamp=datetime.datetime.utcnow().isoformat(),
        )

        entries = self._store.get_entries(target)
        if not entries:
            self._report.status = "skipped"
            self._report.details.append("No entries to distill")
            return self._report

        self._report.original_entry_count = len(entries)
        original_size = sum(len(e.content) for e in entries)

        # Separate protected entries
        protected = [e for e in entries if e.category in PROTECTED_CATEGORIES]
        distillable = [e for e in entries if e.category in DISTILLABLE_CATEGORIES]
        other = [
            e
            for e in entries
            if e.category not in PROTECTED_CATEGORIES
            and e.category not in DISTILLABLE_CATEGORIES
        ]

        if not distillable:
            self._report.status = "skipped"
            self._report.details.append("No distillable entries found")
            return self._report

        # Create backup before any modification
        path = self._store._get_path(target)
        if path.exists():
            bak_name = f"{path.name}.bak.distill.{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            bak_path = path.with_name(bak_name)
            try:
                shutil.copy2(path, bak_path)
                self._report.backup_path = str(bak_path)
                self._report.details.append(f"Backup: {bak_name}")
            except Exception as e:
                self._report.errors.append(f"Backup failed: {e}")
                self._report.status = "failed"
                return self._report

        try:
            # Level 1: Deduplicate
            deduped, removed = self._deduplicate(distillable)
            self._report.removed_duplicates = removed
            if removed > 0:
                self._report.details.append(f"Level 1: Removed {removed} duplicates")

            # Level 2: Consolidate related facts
            consolidated = self._consolidate_related(deduped)

            # Level 3: Episodic compression (LLM)
            if provider and model and self._model_gateway:
                compressed = self._compress_episodic(consolidated, provider, model)
            else:
                compressed = consolidated

            # Level 4: Project distillation (LLM)
            if provider and model and self._model_gateway:
                final_distillable = self._distill_project(compressed, provider, model)
            else:
                final_distillable = compressed

            # Combine: protected + distilled + other
            final_entries = protected + final_distillable + other

            self._report.distilled_entry_count = len(final_distillable)
            self._report.preserved_entries = len(protected)

            # Calculate compression ratio
            if self._report.original_entry_count > 0:
                compressed_count = len(protected) + len(final_distillable) + len(other)
                self._report.compression_ratio = round(
                    (1 - compressed_count / self._report.original_entry_count) * 100, 1
                )

            # Apply changes
            self._store._entries[target] = final_entries
            self._store.save_to_disk(target)
            self._store.invalidate_snapshot()

            self._report.status = "completed"
            after_size = sum(len(e.content) for e in final_entries)
            self._report.details.append(f"Size: {original_size} → {after_size} chars")
            logger.info(
                f"Distilled {target}: {self._report.original_entry_count} → "
                f"{compressed_count} entries ({self._report.compression_ratio}%)"
            )

        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            self._report.errors.append(str(e))
            self._report.status = "failed"

            # Restore from backup
            if self._report.backup_path:
                try:
                    shutil.copy2(Path(self._report.backup_path), path)
                    self._report.details.append("Restored from backup")
                except Exception as restore_err:
                    self._report.errors.append(f"Restore failed: {restore_err}")

        return self._report

    def should_run(self, target: str = "memory") -> bool:
        """Check if distillation should be triggered for the given target."""
        entries = self._store.get_entries(target)
        if not entries:
            return False
        entry_count = len(entries)
        total_chars = sum(len(e.content) for e in entries)
        return entry_count > TRIGGER_ENTRY_COUNT or total_chars > TRIGGER_SIZE_BYTES


# ── Convenience ──


def run_distiller(
    store: MemoryStore,
    target: str = "memory",
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> DistillationReport:
    """Run the distiller on a store with optional LLM for Levels 3-4."""
    distiller = MemoryDistiller(store)
    return distiller.run(target=target, provider=provider, model=model)
