"""Memory API — per-agent memory CRUD and health.

Wraps ``memory_manage()`` + ``MemoryStore`` so both the frontend and CLI
can read/write agent memory through the same HTTP interface.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _get_memory_api():
    from orcanium.app.domains.capability.memory_api import memory_manage
    return memory_manage


def _get_memory_store(agent_name: str):
    from orcanium.app.domains.memory.store import MemoryStore
    return MemoryStore(agent_name)


@router.get("/")
def list_memory(agent: str = Query(..., description="Agent name")):
    """List all memory entries for an agent."""
    try:
        store = _get_memory_store(agent)
        store.load_from_disk()
        entries = store.get_entries("memory")
        return {
            "agent": agent,
            "entries": [e.to_dict() if hasattr(e, "to_dict") else {
                "id": _entry_id(e),
                "category": getattr(e, "category", "OTHER"),
                "content": getattr(e, "content", ""),
                "importance": getattr(e, "importance", 0.5),
                "confidence": getattr(e, "confidence", 0.5),
                "access_count": getattr(e, "access_count", 0),
                "created_at": _fmt_dt(getattr(e, "created_at", None)),
                "updated_at": _fmt_dt(getattr(e, "updated_at", None)),
            } for e in entries],
            "total": len(entries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user")
def list_user_profile(agent: str = Query(..., description="Agent name")):
    """List user profile entries for an agent."""
    try:
        store = _get_memory_store(agent)
        store.load_from_disk()
        entries = store.get_entries("user")
        return {
            "agent": agent,
            "entries": [{
                "id": _entry_id(e),
                "category": getattr(e, "category", "OTHER"),
                "content": getattr(e, "content", ""),
            } for e in entries],
            "total": len(entries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def add_memory(
    agent: str = Query(...),
    content: str = Query(...),
    category: str = "CONTEXT",
    origin: str = "user",
):
    """Add a memory entry for an agent."""
    try:
        api = _get_memory_api()
        result = api(action="add", agent_id=agent, content=content, category=category, origin=origin)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
def delete_memory(entry_id: str, agent: str = Query(...)):
    """Delete a memory entry by its ID."""
    try:
        api = _get_memory_api()
        result = api(action="delete", agent_id=agent, entry_id=entry_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def memory_health(agent: str = Query(..., description="Agent name")):
    """Return memory health diagnostics for an agent."""
    try:
        from orcanium.app.domains.memory.memory_health import evaluate_memory_health
        health = evaluate_memory_health(agent)
        return {"agent": agent, "health": health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Helpers ────────────────────────────────────────────────────

def _entry_id(entry) -> str:
    import hashlib
    content = getattr(entry, "content", "")
    category = getattr(entry, "category", "OTHER")
    return hashlib.md5(f"{category}:{content}".encode()).hexdigest()[:12]


def _fmt_dt(dt) -> Optional[str]:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)
