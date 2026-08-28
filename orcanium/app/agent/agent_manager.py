import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from orcanium.app.core.config import AGENTS_DIR, ensure_orcanium_dirs

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

from orcanium.app.core.db import AgentState


class AgentManager:
    @staticmethod
    def get_agent_dir(name: str) -> Path:
        return AGENTS_DIR / name

    @classmethod
    def list_disk_agents(cls) -> List[str]:
        ensure_orcanium_dirs()
        if not AGENTS_DIR.exists():
            return []
        return [d.name for d in AGENTS_DIR.iterdir() if d.is_dir()]

    @classmethod
    def load_agent_config(cls, name: str) -> Dict[str, Any]:
        cfg_path = cls.get_agent_dir(name) / "CONFIG.yml"
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to parse CONFIG.yml for agent '{name}': {e}")
        return {}

    @classmethod
    def save_agent_config(cls, name: str, config: Dict[str, Any]):
        cls.get_agent_dir(name).mkdir(parents=True, exist_ok=True)
        cfg_path = cls.get_agent_dir(name) / "CONFIG.yml"
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

    @classmethod
    def create_agent(
        cls,
        db: Session,
        name: str,
        soul: str = "",
        skills: str = "",
        memory: str = "",
        user: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentState:
        """Creates a complete agent on disk and in the SQLite DB."""
        agent_dir = cls.get_agent_dir(name)
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Write Files
        with open(agent_dir / "SOUL.md", "w", encoding="utf-8") as f:
            f.write(soul or f"# {name} Soul\nYou are a helpful Orcanium agent.")

        with open(agent_dir / "SKILL.md", "w", encoding="utf-8") as f:
            f.write(skills or f"# {name} Skills\nNo additional skills configured yet.")

        with open(agent_dir / "MEMORY.md", "w", encoding="utf-8") as f:
            f.write(memory or f"# {name} Memory\nInitial learnings go here.")

        with open(agent_dir / "USER.md", "w", encoding="utf-8") as f:
            f.write(
                user or f"# {name} User\nUser profile and preferences for this agent."
            )

        # Default config
        default_cfg = {
            "name": name,
            "version": "1.0",
            "model_provider": "openai",
            "model_name": "gpt-4-turbo",
            "temperature": 0.7,
            "max_tokens": 2048,
            "auto_memory": True,
            "auto_skill": False,
        }
        if config:
            default_cfg.update(config)

        cls.save_agent_config(name, default_cfg)

        # Mirror metadata in SQLite
        db_agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not db_agent:
            db_agent = AgentState(
                name=name,
                status="stopped",
                active_sessions=0,
                health="healthy",
                model_provider=default_cfg["model_provider"],
                model_name=default_cfg["model_name"],
            )
            db.add(db_agent)
        else:
            db_agent.model_provider = default_cfg["model_provider"]
            db_agent.model_name = default_cfg["model_name"]

        db.commit()

        # Initialize per-agent runtime state
        from orcanium.app.domains.agent.runtime_state import agent_runtime_state

        agent_runtime_state.init_for_agent(name, db)

        db.refresh(db_agent)
        return db_agent

    @classmethod
    def sync_all_agents(cls, db: Session):
        """Scans the disk and updates the SQLite database with found/removed agents."""
        disk_agents = cls.list_disk_agents()
        db_agents = db.query(AgentState).all()
        db_agent_names = {a.name for a in db_agents}

        # Register missing agents in SQLite
        for name in disk_agents:
            if name not in db_agent_names:
                cfg = cls.load_agent_config(name)
                db_agent = AgentState(
                    name=name,
                    status="stopped",
                    active_sessions=0,
                    health="healthy",
                    model_provider=cfg.get("model_provider", "openai"),
                    model_name=cfg.get("model_name", "gpt-4-turbo"),
                )
                db.add(db_agent)

        # Remove deleted agents from database (or mark archived)
        for db_agent in db_agents:
            if db_agent.name not in disk_agents:
                db_agent.status = "archived"

        db.commit()

    @classmethod
    def get_agent_files(cls, name: str) -> Dict[str, str]:
        """Loads contents of markdown files for editing/viewing."""
        agent_dir = cls.get_agent_dir(name)
        files = ["SOUL.md", "SKILL.md", "MEMORY.md", "USER.md"]
        contents = {}
        for f_name in files:
            p = agent_dir / f_name
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    contents[f_name] = f.read()
            else:
                contents[f_name] = ""
        return contents

    @classmethod
    def delete_agent(cls, db: Session, name: str):
        """Deletes an agent completely from disk, DB, and runtime state."""
        agent_dir = cls.get_agent_dir(name)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

        # Delete runtime state (nudge counters, review timestamps)
        from orcanium.app.core.db import AgentRuntimeState

        db.query(AgentRuntimeState).filter(AgentRuntimeState.agent_id == name).delete()

        # Delete agent state row
        db_agent = db.query(AgentState).filter(AgentState.name == name).first()
        if db_agent:
            db.delete(db_agent)

        db.commit()
