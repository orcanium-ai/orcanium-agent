from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.core.db import AgentState, get_db
from orcanium.app.domains.agent.health import agent_health

router = APIRouter()


@router.get("/")
def list_agents(db: Session = Depends(get_db)):
    AgentManager.sync_all_agents(db)
    agents = db.query(AgentState).all()
    return agents


@router.post("/create")
def create_agent(
    name: str,
    soul: Optional[str] = None,
    skills: Optional[str] = None,
    memory: Optional[str] = None,
    user: Optional[str] = None,
    config: Optional[str] = None,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new agent.

    Accepts config as a JSON string (for frontend query-param compatibility)
    OR individual model_provider / model_name params.
    """
    import json as _json

    parsed_config: Dict[str, Any] = {}
    if config:
        try:
            parsed_config = _json.loads(config)
        except (_json.JSONDecodeError, TypeError):
            pass
    if model_provider:
        parsed_config["model_provider"] = model_provider
    if model_name:
        parsed_config["model_name"] = model_name

    try:
        agent = AgentManager.create_agent(
            db, name, soul, skills, memory, user, parsed_config or None
        )
        return {"status": "success", "agent": agent}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}/files")
def get_agent_files(name: str, db: Session = Depends(get_db)):
    agent = db.query(AgentState).filter(AgentState.name == name).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_dir = AgentManager.get_agent_dir(name)
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found on disk")
    files = AgentManager.get_agent_files(name)
    return files


@router.put("/{name}/files")
def update_agent_files(
    name: str, payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)
):
    agent_dir = AgentManager.get_agent_dir(name)
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found")

    for file_name in ["SOUL.md", "SKILL.md", "MEMORY.md", "USER.md"]:
        if file_name in payload:
            with open(agent_dir / file_name, "w", encoding="utf-8") as f:
                f.write(payload[file_name])

    return {"status": "success", "detail": "Agent files updated successfully"}


@router.get("/{name}/config")
def get_agent_config(name: str):
    cfg = AgentManager.load_agent_config(name)
    if not cfg:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return cfg


@router.put("/{name}/config")
def update_agent_config(
    name: str, config: Dict[str, Any] = Body(...), db: Session = Depends(get_db)
):
    # Load current, merge, save
    current = AgentManager.load_agent_config(name)
    current.update(config)
    AgentManager.save_agent_config(name, current)

    # Sync DB
    db_agent = db.query(AgentState).filter(AgentState.name == name).first()
    if db_agent:
        db_agent.model_provider = current.get("model_provider", db_agent.model_provider)
        db_agent.model_name = current.get("model_name", db_agent.model_name)
        db.commit()

    return {"status": "success", "config": current}


@router.post("/{name}/start")
def start_agent(name: str, db: Session = Depends(get_db)):
    db_agent = db.query(AgentState).filter(AgentState.name == name).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db_agent.status = "running"
    db.commit()
    return {"status": "success", "agent_status": db_agent.status}


@router.post("/{name}/stop")
def stop_agent(name: str, db: Session = Depends(get_db)):
    db_agent = db.query(AgentState).filter(AgentState.name == name).first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db_agent.status = "stopped"
    db.commit()
    return {"status": "success", "agent_status": db_agent.status}


@router.get("/{name}/health")
def get_agent_health(name: str, db: Session = Depends(get_db)):
    """Return real runtime health status for an agent."""
    agent = db.query(AgentState).filter(AgentState.name == name).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    health = agent_health.get_health(name)
    health["db_status"] = agent.status
    health["agent_name"] = agent.name
    return health


@router.delete("/{name}")
def delete_agent(name: str, db: Session = Depends(get_db)):
    try:
        AgentManager.delete_agent(db, name)
        return {"status": "success", "detail": f"Agent {name} deleted completely"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/runtime-state")
def get_agent_runtime_state(agent_id: str, db: Session = Depends(get_db)):
    """Get per-agent learning state (nudge counters, last review timestamps)."""
    from orcanium.app.domains.agent.runtime_state import agent_runtime_state

    # Verify agent exists
    agent = db.query(AgentState).filter(AgentState.name == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    return agent_runtime_state.format_state(agent_id, db)


@router.post("/{name}/switch")
def switch_agent(name: str, db: Session = Depends(get_db)):
    """Switch the active runtime context to a different agent.

    Emits an AGENT_CHANGED event so all consumers (UI, gateway, timeline)
    can react. Does NOT restart the backend — agents share the same runtime.
    """
    agent = db.query(AgentState).filter(AgentState.name == name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    from orcanium.app.domains.capability.events import (
        AGENT_CHANGED, OrcaniumEvent, event_bus,
    )

    event = OrcaniumEvent(
        category="AGENT",
        event_type=AGENT_CHANGED,
        agent_id=name,
        payload={
            "agent_name": name,
            "model_provider": agent.model_provider or "",
            "model_name": agent.model_name or "",
            "status": agent.status or "stopped",
        },
    )
    event_bus.emit(event)

    return {
        "status": "ok",
        "agent": {
            "name": name,
            "provider": agent.model_provider,
            "model": agent.model_name,
        },
    }
