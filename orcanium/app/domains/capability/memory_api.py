"""memory_manage — capability API for memory operations.

The ONLY supported write path for memory.
All mutations go through this API.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import OrcaniumEvent, event_bus

from orcanium.app.domains.memory.store import (
    CATEGORIES,
    ORIGINS,
    MemoryEntry,
    MemoryStore,
)

logger = logging.getLogger(__name__)


def memory_manage(
    action: str,
    agent_id: str,
    content: Optional[str] = None,
    category: str = "CONTEXT",
    origin: str = "user",
    search_query: Optional[str] = None,
    content_substring: Optional[str] = None,
    entry_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Capability API for memory operations.

    Supported actions: add, update, delete, archive, retrieve, search

    All actions go through MemoryStore. No direct file access.
    """
    store = MemoryStore(agent_id)
    store.load_from_disk()

    if action == "add":
        if not content:
            return {"success": False, "error": "content required"}
        result = store.add(
            target="memory", content=content, category=category, origin=origin
        )
        success = "Error" not in result

        if success:
            event_bus.emit_simple(
                category="MEMORY",
                event_type="memory_added",
                agent_id=agent_id,
                payload={"category": category, "content_preview": content[:100]},
            )

        return {"success": success, "message": result}

    elif action == "delete":
        if not content_substring and not entry_id:
            return {"success": False, "error": "content_substring or entry_id required"}
        if entry_id:
            # Find entry by ID hash
            entries = store.get_entries("memory")
            import hashlib

            for e in entries:
                eid = hashlib.md5(f"{e.category}:{e.content}".encode()).hexdigest()[:12]
                if eid == entry_id:
                    result = store.remove("memory", e.content[:50])
                    success = "Error" not in result
                    if success:
                        event_bus.emit_simple("MEMORY", "memory_deleted", agent_id)
                    return {"success": success, "message": result}
            return {"success": False, "error": "entry not found"}
        result = store.remove("memory", content_substring or "")
        success = "Error" not in result
        if success:
            event_bus.emit_simple("MEMORY", "memory_deleted", agent_id)
        return {"success": success, "message": result}

    elif action == "retrieve":
        entries = store.get_entries(
            "memory", category=category if category != "ALL" else None
        )
        return {
            "success": True,
            "entries": [
                {"id": _eid(e), "category": e.category, "content": e.content}
                for e in entries
            ],
            "count": len(entries),
        }

    elif action == "search":
        if not search_query:
            return {"success": False, "error": "search_query required"}
        entries = store.get_entries("memory")
        query_lower = search_query.lower()
        matches = [e for e in entries if query_lower in e.content.lower()]
        return {
            "success": True,
            "entries": [
                {"id": _eid(e), "category": e.category, "content": e.content}
                for e in matches
            ],
            "count": len(matches),
        }

    elif action == "archive":
        return {
            "success": True,
            "message": "Archive via delete + backup (not implemented in v1)",
        }

    return {"success": False, "error": f"Unknown action: {action}"}


def _eid(entry: MemoryEntry) -> str:
    import hashlib

    return hashlib.md5(f"{entry.category}:{entry.content}".encode()).hexdigest()[:12]
