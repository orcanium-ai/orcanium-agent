"""Per-agent runtime state — persistent nudge counters for memory/skill reflection.

Each agent maintains its own learning state independently in SQLite.
State survives process restarts, daemon restarts, and system reboots.
"""

import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from orcanium.app.core.db import AgentRuntimeState

logger = logging.getLogger(__name__)


class AgentRuntimeStateService:
    """Thread-safe service for managing per-agent learning state."""

    def get_state(self, agent_id: str, db: Session) -> Optional[AgentRuntimeState]:
        """Retrieve the runtime state for an agent, or None if not initialized."""
        return (
            db.query(AgentRuntimeState)
            .filter(AgentRuntimeState.agent_id == agent_id)
            .first()
        )

    def get_or_create_state(self, agent_id: str, db: Session) -> AgentRuntimeState:
        """Get existing state or create a new one with defaults."""
        state = self.get_state(agent_id, db)
        if not state:
            state = AgentRuntimeState(
                agent_id=agent_id,
                turns_since_memory=0,
                turns_since_skill=0,
                turns_since_user=0,
                updated_at=datetime.datetime.utcnow(),
            )
            db.add(state)
            db.commit()
            db.refresh(state)
        return state

    def increment_memory_counter(self, agent_id: str, db: Session) -> int:
        """Atomically increment turns_since_memory. Returns new value."""
        from sqlalchemy import text as sa_text

        # Ensure row exists
        self.get_or_create_state(agent_id, db)

        # Atomic SQL increment — no read-modify-write race
        db.execute(
            sa_text(
                "UPDATE agent_runtime_state SET turns_since_memory = turns_since_memory + 1, "
                "updated_at = :now WHERE agent_id = :id"
            ),
            {"now": datetime.datetime.utcnow(), "id": agent_id},
        )
        db.commit()

        # Read back the new value
        state = self.get_state(agent_id, db)
        return state.turns_since_memory if state else 0

    def increment_skill_counter(self, agent_id: str, db: Session) -> int:
        """Atomically increment turns_since_skill. Returns new value."""
        from sqlalchemy import text as sa_text

        self.get_or_create_state(agent_id, db)

        db.execute(
            sa_text(
                "UPDATE agent_runtime_state SET turns_since_skill = turns_since_skill + 1, "
                "updated_at = :now WHERE agent_id = :id"
            ),
            {"now": datetime.datetime.utcnow(), "id": agent_id},
        )
        db.commit()

        state = self.get_state(agent_id, db)
        return state.turns_since_skill if state else 0

    def reset_memory_counter(self, agent_id: str, db: Session) -> None:
        """Reset turns_since_memory to 0 and update last_memory_review timestamp."""
        state = self.get_or_create_state(agent_id, db)
        state.turns_since_memory = 0
        state.last_memory_review = datetime.datetime.utcnow()
        state.updated_at = datetime.datetime.utcnow()
        db.commit()

    def increment_user_counter(self, agent_id: str, db: Session) -> int:
        """Atomically increment turns_since_user. Returns new value."""
        from sqlalchemy import text as sa_text

        self.get_or_create_state(agent_id, db)

        db.execute(
            sa_text(
                "UPDATE agent_runtime_state SET turns_since_user = turns_since_user + 1, "
                "updated_at = :now WHERE agent_id = :id"
            ),
            {"now": datetime.datetime.utcnow(), "id": agent_id},
        )
        db.commit()

        state = self.get_state(agent_id, db)
        return state.turns_since_user if state else 0

    def reset_skill_counter(self, agent_id: str, db: Session) -> None:
        """Reset turns_since_skill to 0 and update last_skill_review timestamp."""
        state = self.get_or_create_state(agent_id, db)
        state.turns_since_skill = 0
        state.last_skill_review = datetime.datetime.utcnow()
        state.updated_at = datetime.datetime.utcnow()
        db.commit()

    def reset_user_counter(self, agent_id: str, db: Session) -> None:
        """Reset turns_since_user to 0 and update last_user_review timestamp."""
        state = self.get_or_create_state(agent_id, db)
        state.turns_since_user = 0
        state.last_user_review = datetime.datetime.utcnow()
        state.updated_at = datetime.datetime.utcnow()
        db.commit()

    def init_for_agent(self, agent_id: str, db: Session) -> AgentRuntimeState:
        """Initialize runtime state for a newly created agent."""
        return self.get_or_create_state(agent_id, db)

    def init_for_all_agents(self, db: Session) -> int:
        """Initialize runtime state for all existing agents that lack it. Returns count."""
        from orcanium.app.core.db import AgentState

        agents = db.query(AgentState).all()
        count = 0
        for agent in agents:
            existing = self.get_state(agent.name, db)
            if not existing:
                self.init_for_agent(agent.name, db)
                count += 1
        if count:
            logger.info(f"Initialized runtime state for {count} existing agent(s).")
        return count

    def format_state(self, agent_id: str, db: Session) -> Optional[dict]:
        """Return a dict representation for API exposure."""
        state = self.get_or_create_state(agent_id, db)
        from orcanium.app.agent.agent_manager import AgentManager

        config = AgentManager.load_agent_config(agent_id)
        return {
            "agent_id": agent_id,
            "turns_since_memory": state.turns_since_memory or 0,
            "turns_since_skill": state.turns_since_skill or 0,
            "turns_since_user": state.turns_since_user or 0,
            "last_memory_review": (
                state.last_memory_review.isoformat()
                if state.last_memory_review
                else None
            ),
            "last_skill_review": (
                state.last_skill_review.isoformat() if state.last_skill_review else None
            ),
            "last_user_review": (
                state.last_user_review.isoformat() if state.last_user_review else None
            ),
            "memory_interval": config.get("memory_nudge_interval", 10),
            "skill_interval": config.get("skill_nudge_interval", 10),
            "user_interval": config.get("user_nudge_interval", 10),
        }


# Singleton
agent_runtime_state = AgentRuntimeStateService()
