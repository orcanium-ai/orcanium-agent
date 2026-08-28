"""MemoryStore — atomic memory entries with locking, injection defense, and drift detection.

Entry format on disk:
    § [CATEGORY] content text here
    § [PREFERENCE] User prefers concise answers
    § [DECISION] Rejected gaming market

Categories: USER_FACT, PREFERENCE, CONTEXT, PROJECT, DECISION, LEARNING, SKILL_REFERENCE, OTHER
Origins: user, background_review, curator, distiller, migration
"""

import datetime
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from orcanium.app.core.config import AGENTS_DIR

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

ENTRY_DELIMITER = "\n§ "

CATEGORIES = {
    "USER_FACT",
    "PREFERENCE",
    "CONTEXT",
    "PROJECT",
    "DECISION",
    "LEARNING",
    "SKILL_REFERENCE",
    "OTHER",
}

ORIGINS = {"user", "background_review", "curator", "distiller", "migration"}

# Entry-level size protection (engineering limits, NOT cognitive limits)
MEMORY_ENTRY_MAX_CHARS = 8192  # 8KB for general memory entries
USER_FACT_MAX_CHARS = 1024  # 1KB for user facts
SKILL_MAX_CHARS = 65536  # 64KB for skills (future)
KNOWLEDGE_CHUNK_MAX_CHARS = 4096  # 4KB for knowledge chunks

# ── Data model ─────────────────────────────────────────────────


@dataclass
class MemoryEntry:
    content: str
    category: str = "OTHER"
    importance: float = 0.5  # 0.0-1.0 — default neutral
    confidence: float = 0.5  # 0.0-1.0 — how certain we are
    access_count: int = 0  # how many times retrieved
    last_accessed: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    origin: str = "user"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.category not in CATEGORIES:
            self.category = "OTHER"
        self.importance = max(0.0, min(1.0, self.importance))
        self.confidence = max(0.0, min(1.0, self.confidence))

    def serialize(self) -> str:
        """Serialize to disk format: § [CATEGORY] content"""
        return f"§ [{self.category}] {self.content}"

    @staticmethod
    def parse(line: str) -> Optional["MemoryEntry"]:
        """Parse a single line from disk format."""
        line = line.strip()
        if not line or not line.startswith("§"):
            return None
        rest = line[1:].strip()
        if not rest.startswith("["):
            return None
        close_bracket = rest.find("]")
        if close_bracket == -1:
            return None
        category = rest[1:close_bracket].strip()
        if category not in CATEGORIES:
            category = "OTHER"
        content = rest[close_bracket + 1 :].strip()
        if not content:
            return None
        return MemoryEntry(
            content=content,
            category=category,
            origin="migration",
        )

    def record_access(self) -> None:
        """Record a retrieval access — bumps access_count and last_accessed."""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed = datetime.datetime.utcnow()


# ── Threat patterns ────────────────────────────────────────────

_THREAT_PATTERNS_ALL: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|below)\s+instructions", re.I),
    re.compile(r"forget\s+(all\s+)?(previous|above|below)", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"<\s*(?:system|user|assistant)\s*>", re.I),
    re.compile(r"(?:DISREGARD|OVERRIDE|CANCEL)\s+(?:ALL\s+)?(?:PRIOR|ABOVE)", re.I),
]

_THREAT_PATTERNS_CONTEXT: List[re.Pattern] = _THREAT_PATTERNS_ALL + [
    re.compile(r"You\s+are\s+(now|not\s+an?\s+)", re.I),
    re.compile(r"ACT\s+AS\s+", re.I),
]

_THREAT_PATTERNS_STRICT: List[re.Pattern] = _THREAT_PATTERNS_CONTEXT + [
    re.compile(r"(?:EXECUTE|RUN|BASH|SHELL|TERMINAL|CMD)\s+(?:COMMAND|:|--)", re.I),
    re.compile(r"(?:SSH|TELNET|NETCAT|NMAP)\s", re.I),
    re.compile(r"(?:DOWNLOAD|UPLOAD|WGET|CURL)\s+(?:AND\s+)?(?:EXECUTE|RUN)", re.I),
    re.compile(
        r"(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)\s*[:=]\s*['\"]?[\w-]{20,}", re.I
    ),
]

_THREAT_SCOPES = {
    "all": _THREAT_PATTERNS_ALL,
    "context": _THREAT_PATTERNS_CONTEXT,
    "strict": _THREAT_PATTERNS_STRICT,
}

BLOCKED_PLACEHOLDER = "[BLOCKED: POTENTIAL PROMPT INJECTION]"


def scan_threats(text: str, scope: str = "strict") -> Optional[str]:
    """Scan text for injection threats. Returns first matched pattern or None."""
    patterns = _THREAT_SCOPES.get(scope, _THREAT_PATTERNS_STRICT)
    for pattern in patterns:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


# ── File locking ───────────────────────────────────────────────


def _file_lock(path: Path):
    """Context manager for file-level locking. Cross-platform."""

    class _FileLock:
        def __init__(self, lock_path: Path):
            self._lock_path = lock_path
            self._fd = None

        def __enter__(self):
            lock_file = self._lock_path.with_suffix(self._lock_path.suffix + ".lock")
            try:
                self._fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
                try:
                    import fcntl

                    fcntl.flock(self._fd, fcntl.LOCK_EX)
                except (ImportError, OSError):
                    pass  # No flock on all platforms
            except OSError:
                pass
            return self

        def __exit__(self, *args):
            if self._fd is not None:
                try:
                    import fcntl

                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass
                os.close(self._fd)

    return _FileLock(path)


# ── MemoryStore ────────────────────────────────────────────────


class MemoryStore:
    """Atomic entry-based memory store with locking, injection defense, and drift detection."""

    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._agent_dir = AGENTS_DIR / agent_name

        # Live state
        self._entries: Dict[str, List[MemoryEntry]] = {
            "memory": [],
            "user": [],
        }

        # Frozen snapshot (built at load time, stable until invalidated)
        self._snapshot: Dict[str, Optional[str]] = {
            "memory": None,
            "user": None,
        }

        # File content hash for drift detection
        self._file_hash: Dict[str, Optional[str]] = {
            "memory": None,
            "user": None,
        }

    # ── File paths ──

    def _get_path(self, target: str) -> Path:
        return self._agent_dir / ("MEMORY.md" if target == "memory" else "USER.md")

    # ── Load / Save ──

    def load_from_disk(self) -> None:
        """Read entries from disk, deduplicate, sanitize snapshot, freeze."""
        for target in ("memory", "user"):
            path = self._get_path(target)
            if path.exists():
                try:
                    with _file_lock(path):
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                    self._file_hash[target] = content
                    self._entries[target] = self._parse_content(content)
                except Exception as e:
                    logger.warning(
                        f"Failed to load {target} for {self._agent_name}: {e}"
                    )
                    self._entries[target] = []
            else:
                self._entries[target] = []
                self._file_hash[target] = None

            # Build sanitized snapshot
            self._snapshot[target] = self._build_snapshot(target)

    def _parse_content(self, content: str) -> List[MemoryEntry]:
        """Parse disk content into MemoryEntry list. Deduplicates by content."""
        entries: List[MemoryEntry] = []
        seen: Set[str] = set()
        for line in content.split("\n"):
            entry = MemoryEntry.parse(line)
            if entry and entry.content not in seen:
                seen.add(entry.content)
                entries.append(entry)
        return entries

    def _serialize_entries(self, target: str) -> str:
        """Serialize entries back to disk format."""
        entries = self._entries.get(target, [])
        return "\n".join(e.serialize() for e in entries) + "\n"

    def save_to_disk(self, target: str) -> None:
        """Atomic write with file locking."""
        path = self._get_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._serialize_entries(target)

        with _file_lock(path):
            fd, tmp_path = tempfile.mkstemp(
                prefix=f".{path.name}.tmp.", dir=path.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                shutil.move(tmp_path, path)
                self._file_hash[target] = content
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    # ── Snapshot ──

    def _build_snapshot(self, target: str) -> Optional[str]:
        """Build a sanitized snapshot string. No budget limits — unlimited long-term memory.

        Applies injection filtering only. Engineering protection per-entry only.
        """
        entries = self._entries.get(target, [])
        if not entries:
            return None

        section_title = (
            "AGENT MEMORY & PAST KNOWLEDGE"
            if target == "memory"
            else "USER PROFILE & PREFERENCES"
        )

        parts = [f"## {section_title}"]

        for entry in entries:
            # Scan for threats at snapshot time only
            threat = scan_threats(
                entry.content, scope="strict" if target == "memory" else "all"
            )
            entry_text = BLOCKED_PLACEHOLDER if threat else entry.content
            parts.append(f"- [{entry.category}] {entry_text}")

        return "\n".join(parts)

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """Return the current snapshot for system prompt injection."""
        return self._snapshot.get(target)

    def invalidate_snapshot(self) -> None:
        """Rebuild snapshot from live entries."""
        for target in ("memory", "user"):
            self._snapshot[target] = self._build_snapshot(target)

    # ── Mutation API ──

    def add(
        self,
        target: str,
        content: str,
        category: str = "CONTEXT",
        origin: str = "user",
    ) -> str:
        """Add a memory entry. Returns status message."""
        if target not in ("memory", "user"):
            return f"Error: Unknown target '{target}'"

        if category not in CATEGORIES:
            category = "OTHER"
        if origin not in ORIGINS:
            origin = "user"

        # Write-time threat scan (strict scope)
        threat = scan_threats(content, scope="strict")
        if threat:
            return f"Error: Content rejected — matched threat pattern: {threat[:50]}"

        # Entry-level size protection (engineering safety, NOT cognitive limit)
        max_chars = (
            MEMORY_ENTRY_MAX_CHARS if target == "memory" else USER_FACT_MAX_CHARS
        )
        if len(content) > max_chars:
            return (
                f"Error: Entry exceeds {max_chars} chars ({len(content)}). "
                "Please split into multiple entries."
            )

        # Drift check
        drift_result = self._detect_drift(target)
        if drift_result:
            return drift_result

        entry = MemoryEntry(
            content=content,
            category=category,
            origin=origin,
        )

        path = self._get_path(target)
        with _file_lock(path):
            entries = self._entries[target]

            # Check for exact duplicate
            for existing in entries:
                if existing.content == content:
                    existing.updated_at = datetime.datetime.utcnow()
                    self.save_to_disk(target)
                    self.invalidate_snapshot()
                    return f"Updated timestamp for existing {target} entry"

            entries.append(entry)
            self.save_to_disk(target)

        self.invalidate_snapshot()
        return f"Added [{category}] to {target}"

    def remove(self, target: str, content_substring: str) -> str:
        """Remove entries matching a content substring."""
        if target not in ("memory", "user"):
            return f"Error: Unknown target '{target}'"

        path = self._get_path(target)
        with _file_lock(path):
            entries = self._entries[target]
            before = len(entries)
            self._entries[target] = [
                e for e in entries if content_substring not in e.content
            ]
            removed = before - len(self._entries[target])
            if removed > 0:
                self.save_to_disk(target)
                self.invalidate_snapshot()
                return f"Removed {removed} entry(ies) from {target}"
            return f"No matching entries found in {target}"

    def get_entries(
        self, target: str, category: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Get entries, optionally filtered by category."""
        entries = self._entries.get(target, [])
        if category:
            return [e for e in entries if e.category == category]
        return list(entries)

    def get_raw_content(self, target: str) -> str:
        """Return raw disk content (for frontend file editor)."""
        return self._serialize_entries(target)

    def summary(self) -> Dict[str, Any]:
        """Return summary of current memory state."""
        result = {}
        for target in ("memory", "user"):
            entries = self._entries.get(target, [])
            cat_counts: Dict[str, int] = {}
            for e in entries:
                cat_counts[e.category] = cat_counts.get(e.category, 0) + 1
            result[target] = {
                "entry_count": len(entries),
                "categories": cat_counts,
                "total_chars": sum(len(e.content) for e in entries),
                "snapshot_active": self._snapshot.get(target) is not None,
            }
        return result

    # ── Drift detection ──

    def _detect_drift(self, target: str) -> Optional[str]:
        """Check if the file on disk has drifted from our state.

        Drift triggers:
        1. Round-trip serialization mismatch
        2. Single entry exceeds ENTRY_SIZE_LIMIT

        Returns error message if drift detected, None otherwise.
        """
        path = self._get_path(target)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                current = f.read()
        except Exception:
            return None

        if current == self._file_hash.get(target):
            return None  # No change

        # Drift detected — check if it's safe
        # Parse current content
        entries = self._parse_content(current)

        # Check for oversized entries
        for entry in entries:
            if len(entry.content) > MEMORY_ENTRY_MAX_CHARS:
                # Create backup
                bak_path = path.with_suffix(
                    f".bak.{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                )
                try:
                    shutil.copy2(path, bak_path)
                except Exception:
                    pass
                return (
                    f"Error: External drift detected in {target}. "
                    f"Entry exceeds {MEMORY_ENTRY_MAX_CHARS} chars. "
                    f"Backup saved to {bak_path.name}. "
                    f"Reload to continue."
                )

        # Check round-trip
        serialized = "\n".join(e.serialize() for e in entries) + "\n"
        if serialized != current:
            bak_path = path.with_suffix(
                f".bak.{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            try:
                shutil.copy2(path, bak_path)
            except Exception:
                pass
            return (
                f"Error: External drift detected in {target}. "
                f"Content cannot round-trip through serializer. "
                f"Backup saved to {bak_path.name}. "
                f"Reload to continue."
            )

        return None


# ── Convenience ──


def open_memory_store(agent_name: str) -> MemoryStore:
    """Create and load a MemoryStore for the given agent."""
    store = MemoryStore(agent_name)
    store.load_from_disk()
    return store
