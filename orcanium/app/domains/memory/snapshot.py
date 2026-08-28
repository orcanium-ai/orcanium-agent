"""Snapshot Stability — freeze agent context at startup, reuse across turns.

Current problem:
    Every turn reads SOUL.md, USER.md, MEMORY.md, SKILL.md from disk → builds prompt.

Target:
    Agent Startup → Load Files → Build Snapshot → Freeze → Reuse across turns.

Invalidation triggers:
    memory_manage(), skill_manage(), user_manage(), distiller(), curator(), agent reload

Events:
    snapshot_created, snapshot_invalidated, snapshot_rebuilt
"""

import datetime
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import OrcaniumEvent, event_bus
from orcanium.app.domains.memory.store import MemoryStore

logger = logging.getLogger(__name__)


# ── AgentSnapshot ─────────────────────────────────────────────


@dataclass
class AgentSnapshot:
    """Frozen snapshot of all agent context files at a point in time.

    Contents:
        soul: SOUL.md content
        user: USER.md formatted snapshot
        memory: MEMORY.md formatted snapshot
        skills: SKILL.md content
        state: STATE.md content (Phase 2)

    Built once at startup/first access. Reused across turns until invalidated.
    """

    soul: str = ""
    user: Optional[str] = None
    memory: Optional[str] = None
    skills: str = ""
    state: str = ""

    created_at: Optional[datetime.datetime] = None
    version: int = 0
    content_hash: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.utcnow()
        self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        raw = f"{self.soul}|{self.user}|{self.memory}|{self.skills}|{self.state}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def is_empty(self) -> bool:
        return not any([self.soul, self.user, self.memory, self.skills, self.state])


# ── SnapshotManager ───────────────────────────────────────────


class SnapshotManager:
    """Manages snapshot lifecycle for a single agent.

    Usage:
        mgr = SnapshotManager(agent_name)
        snapshot = mgr.get_snapshot()  # Builds on first call, caches thereafter
        mgr.invalidate()               # On capability change
        snapshot = mgr.get_snapshot()  # Rebuilds on next call
    """

    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._snapshot: Optional[AgentSnapshot] = None
        self._version = 0

    def get_snapshot(self) -> AgentSnapshot:
        """Get current snapshot. Builds if not cached or invalidated."""
        if self._snapshot is None:
            self._snapshot = self._build()
        return self._snapshot

    def invalidate(self) -> None:
        """Invalidate current snapshot. Next get_snapshot() rebuilds."""
        if self._snapshot is not None:
            old_hash = self._snapshot.content_hash
            self._snapshot = None
            event_bus.emit_simple(
                "STATE",
                "snapshot_invalidated",
                self._agent_name,
                {"old_hash": old_hash, "version": self._version},
            )
            logger.debug(f"Snapshot invalidated for {self._agent_name}")

    def refresh(self) -> AgentSnapshot:
        """Invalidate and rebuild immediately. Returns new snapshot."""
        self.invalidate()
        return self.get_snapshot()

    def _build(self) -> AgentSnapshot:
        """Build a fresh snapshot from disk files."""
        from orcanium.app.agent.agent_manager import AgentManager

        files = AgentManager.get_agent_files(self._agent_name)
        store = MemoryStore(self._agent_name)
        store.load_from_disk()

        self._version += 1

        snapshot = AgentSnapshot(
            soul=files.get("SOUL.md", ""),
            user=store.format_for_system_prompt("user"),
            memory=store.format_for_system_prompt("memory"),
            skills=files.get("SKILL.md", ""),
            version=self._version,
        )

        event_bus.emit_simple(
            "STATE",
            "snapshot_created",
            self._agent_name,
            {
                "version": self._version,
                "has_soul": bool(snapshot.soul),
                "has_user": snapshot.user is not None,
                "has_memory": snapshot.memory is not None,
                "has_skills": bool(snapshot.skills),
                "content_hash": snapshot.content_hash,
            },
        )

        logger.info(f"Snapshot built for {self._agent_name} (v{self._version})")
        return snapshot


# ── Global registry ───────────────────────────────────────────

_snapshot_managers: Dict[str, SnapshotManager] = {}


def get_snapshot_manager(agent_name: str) -> SnapshotManager:
    """Get or create a SnapshotManager for an agent."""
    if agent_name not in _snapshot_managers:
        _snapshot_managers[agent_name] = SnapshotManager(agent_name)
    return _snapshot_managers[agent_name]


def invalidate_agent_snapshot(agent_name: str) -> None:
    """Invalidate snapshot for an agent (called by capability APIs on mutation)."""
    mgr = _snapshot_managers.get(agent_name)
    if mgr:
        mgr.invalidate()


def get_agent_snapshot(agent_name: str) -> AgentSnapshot:
    """Get current snapshot for an agent (builds if needed)."""
    return get_snapshot_manager(agent_name).get_snapshot()
