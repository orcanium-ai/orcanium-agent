"""SnapshotManager — snapshot lifecycle with injection defense and drift detection.

Build → Freeze → Capability Change → Invalidate → Next Request → Rebuild
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import event_bus

from orcanium.app.domains.memory.store import (
    BLOCKED_PLACEHOLDER,
    MEMORY_INJECTION_BUDGET,
    USER_INJECTION_BUDGET,
    MemoryEntry,
    MemoryStore,
    scan_threats,
)

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages snapshot lifecycle for the PromptBuilder.

    Build → Freeze → (capability change) → Invalidate → (next request) → Rebuild
    """

    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._store: Optional[MemoryStore] = None
        self._frozen_snapshot: Dict[str, Optional[str]] = {
            "memory": None,
            "user": None,
        }
        self._is_frozen = False

    def build(self) -> None:
        """Build snapshots from current MemoryStore state."""
        self._store = MemoryStore(self._agent_name)
        self._store.load_from_disk()
        self._frozen_snapshot["memory"] = self._store.format_for_system_prompt("memory")
        self._frozen_snapshot["user"] = self._store.format_for_system_prompt("user")
        self._is_frozen = True

    def invalidate(self) -> None:
        """Invalidate current snapshot. Next build() will reload from disk."""
        self._is_frozen = False
        self._frozen_snapshot["memory"] = None
        self._frozen_snapshot["user"] = None

    def get_snapshot(self, target: str) -> Optional[str]:
        """Get frozen snapshot for a target. Returns None if not built or empty."""
        if not self._is_frozen:
            self.build()
        return self._frozen_snapshot.get(target)

    def refresh(self) -> None:
        """Invalidate then rebuild (for use after capability changes)."""
        self.invalidate()
        self.build()
        logger.debug(f"Snapshot refreshed for {self._agent_name}")

    def check_drift(self, target: str) -> Optional[str]:
        """Check for external drift. Returns error message or None."""
        if not self._store:
            return None
        import shutil
        from pathlib import Path

        path = self._store._get_path(target)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                current = f.read()
            entries = []
            for line in current.split("\n"):
                entry = MemoryEntry.parse(line)
                if entry:
                    entries.append(entry)
            # Check entry size
            for entry in entries:
                if len(entry.content) > 2000:
                    bak_path = path.with_suffix(
                        f".bak.{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    shutil.copy2(path, bak_path)
                    event_bus.emit_simple(
                        "SYSTEM",
                        "drift_detected",
                        self._agent_name,
                        {
                            "target": target,
                            "reason": "entry_size_exceeded",
                            "backup": str(bak_path),
                        },
                    )
                    return f"Drift detected: entry exceeds 2000 chars. Backup at {bak_path.name}"
        except Exception as e:
            return str(e)
        return None
