"""user_manage — capability API for user profile operations.

The ONLY supported write path for user profile.
"""

import logging
from typing import Any, Dict, List, Optional

from orcanium.app.domains.capability.events import event_bus

from orcanium.app.domains.memory.store import MemoryStore

logger = logging.getLogger(__name__)


def user_manage(
    action: str,
    agent_id: str,
    content: Optional[str] = None,
    category: str = "USER_FACT",
    origin: str = "background_review",
    search_query: Optional[str] = None,
    fact_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Capability API for user profile operations.

    Supported actions: add_fact, update_fact, remove_fact, retrieve, search
    """
    store = MemoryStore(agent_id)
    store.load_from_disk()

    if action == "add_fact":
        if not content:
            return {"success": False, "error": "content required"}
        result = store.add(
            target="user", content=content, category="USER_FACT", origin=origin
        )
        success = "Error" not in result
        if success:
            event_bus.emit_simple(
                "MEMORY",
                "user_preference_learned",
                agent_id,
                {"content_preview": content[:100]},
            )
        return {"success": success, "message": result}

    elif action == "update_fact":
        if not content:
            return {"success": False, "error": "content required"}
        if fact_id:
            entries = store.get_entries("user")
            import hashlib

            for e in entries:
                eid = hashlib.md5(f"{e.category}:{e.content}".encode()).hexdigest()[:12]
                if eid == fact_id:
                    store.remove("user", e.content[:50])
                    store.add("user", content, category="USER_FACT", origin=origin)
                    event_bus.emit_simple("MEMORY", "user_updated", agent_id)
                    return {"success": True, "message": "Fact updated"}
            return {"success": False, "error": "fact not found"}
        return {"success": False, "error": "fact_id required"}

    elif action == "remove_fact":
        if not content and not fact_id:
            return {"success": False, "error": "content or fact_id required"}
        if fact_id:
            entries = store.get_entries("user")
            import hashlib

            for e in entries:
                eid = hashlib.md5(f"{e.category}:{e.content}".encode()).hexdigest()[:12]
                if eid == fact_id:
                    store.remove("user", e.content[:50])
                    event_bus.emit_simple("MEMORY", "user_updated", agent_id)
                    return {"success": True, "message": "Fact removed"}
            return {"success": False, "error": "fact not found"}
        store.remove("user", content)
        event_bus.emit_simple("MEMORY", "user_updated", agent_id)
        return {"success": True, "message": "Fact removed"}

    elif action == "retrieve":
        entries = store.get_entries("user")
        return {
            "success": True,
            "entries": [_entry_dict(e) for e in entries],
            "count": len(entries),
        }

    elif action == "search":
        if not search_query:
            return {"success": False, "error": "search_query required"}
        entries = store.get_entries("user")
        query_lower = search_query.lower()
        matches = [e for e in entries if query_lower in e.content.lower()]
        return {
            "success": True,
            "entries": [_entry_dict(e) for e in matches],
            "count": len(matches),
        }

    return {"success": False, "error": f"Unknown action: {action}"}


def _entry_dict(entry) -> dict:
    import hashlib

    return {
        "id": hashlib.md5(f"{entry.category}:{entry.content}".encode()).hexdigest()[
            :12
        ],
        "category": entry.category,
        "content": entry.content,
        "origin": entry.origin,
    }
