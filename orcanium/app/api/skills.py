"""Skills API — per-agent skill management and hub search.

Wraps ``skill_api.skill_manage()`` and ``skills_hub.unified_search()`` so both
the frontend and CLI can manage skills through the same HTTP interface.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _get_skill_api():
    from orcanium.app.domains.capability.skill_api import skill_manage
    return skill_manage


@router.get("/")
def list_skills(agent: str = Query(..., description="Agent name")):
    """List all skills for a given agent."""
    try:
        api = _get_skill_api()
        skills = api(action="search", agent_name=agent)
        return {"agent": agent, "skills": [s.to_dict() for s in skills]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_skill(agent: str = Query(...), title: str = Query(...), description: str = "", workflow: str = "", examples: str = "", executable: bool = False):
    """Create a new skill for an agent."""
    try:
        api = _get_skill_api()
        result = api(action="create", agent_name=agent, title=title, description=description, workflow=workflow, examples=examples, executable=executable)
        return {"status": "ok", "skill": result.to_dict() if hasattr(result, "to_dict") else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{skill_id}")
def update_skill(skill_id: str, agent: str = Query(...), title: str = "", description: str = "", workflow: str = "", examples: str = "", state: str = ""):
    """Update a skill."""
    try:
        api = _get_skill_api()
        updates = {}
        if title: updates["title"] = title
        if description: updates["description"] = description
        if workflow: updates["workflow"] = workflow
        if examples: updates["examples"] = examples
        if state: updates["state"] = state
        result = api(action="update", agent_name=agent, skill_id=skill_id, updates=updates)
        return {"status": "ok", "skill": result.to_dict() if hasattr(result, "to_dict") else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}")
def delete_skill(skill_id: str, agent: str = Query(...)):
    """Delete a skill."""
    try:
        api = _get_skill_api()
        api(action="delete", agent_name=agent, skill_id=skill_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle")
def toggle_skill(agent: str = Query(...), skill_id: str = Query(...), enabled: bool = True):
    """Enable or disable a skill by setting its state to ACTIVE or DORMANT."""
    try:
        api = _get_skill_api()
        new_state = "ACTIVE" if enabled else "DORMANT"
        result = api(action="set_state", agent_name=agent, skill_id=skill_id, state=new_state)
        return {"status": "ok", "state": new_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hub/search")
def search_hub(q: str = Query(..., description="Search query"), limit: int = 20):
    """Search skill registries (skills.sh, GitHub, ClawHub, etc.)."""
    try:
        from orcanium.app.tools.skills_hub import unified_search, SkillSource
        sources = list(SkillSource)
        results = unified_search(q, sources, limit=limit)
        return {"query": q, "results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hub/install")
def install_from_hub(identifier: str = Query(...), agent: str = Query(...)):
    """Install a skill from the hub and associate it with an agent."""
    try:
        from orcanium.app.tools.skills_hub import resolve_identifier, install_from_quarantine, quarantine_bundle, scan_skill
        bundle = quarantine_bundle(identifier)
        scan_result = scan_skill(bundle["path"])
        install_path = install_from_quarantine(bundle, agent_name=agent)
        return {"status": "ok", "path": str(install_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
