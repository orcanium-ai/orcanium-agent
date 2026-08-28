"""Orcanium State Layer — separates active state from memory.

Memory = What happened
Knowledge = What is true
State = What I am currently doing

Per-agent STATE.md file with current goals, plans, tasks, blockers, status.

APIs:
    state_manage(action, agent_id, ...)
    get_state(agent_id)
    update_state(agent_id, ...)
    clear_state(agent_id)

Events:
    state_created, state_updated, state_completed, state_blocked
"""

import datetime
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from orcanium.app.core.config import AGENTS_DIR
from orcanium.app.domains.capability.events import event_bus

logger = logging.getLogger(__name__)


# ── State Schema ──────────────────────────────────────────────


@dataclass
class AgentState:
    """Current state of an agent — what it's currently doing.

    Stored in STATE.md per agent, separate from MEMORY.md (what happened)
    and KNOWLEDGE (what is true).
    """

    current_goal: str = ""
    current_plan: str = ""
    current_tasks: List[str] = field(default_factory=list)
    current_blockers: List[str] = field(default_factory=list)
    current_status: str = "idle"  # idle, active, blocked, completed
    last_updated: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_goal": self.current_goal,
            "current_plan": self.current_plan,
            "current_tasks": self.current_tasks,
            "current_blockers": self.current_blockers,
            "current_status": self.current_status,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Serialize to STATE.md format."""
        lines = ["# Agent State"]
        lines.append(f"## Status: {self.current_status}")
        if self.current_goal:
            lines.append(f"\n## Current Goal\n{self.current_goal}")
        if self.current_plan:
            lines.append(f"\n## Current Plan\n{self.current_plan}")
        if self.current_tasks:
            lines.append("\n## Current Tasks")
            for t in self.current_tasks:
                lines.append(f"- {t}")
        if self.current_blockers:
            lines.append("\n## Current Blockers")
            for b in self.current_blockers:
                lines.append(f"- {b}")
        lines.append(
            f"\n## Last Updated\n{self.last_updated or datetime.datetime.utcnow().isoformat()}"
        )
        return "\n".join(lines)

    @staticmethod
    def from_markdown(content: str) -> "AgentState":
        """Parse STATE.md content back into AgentState."""
        state = AgentState()
        state.last_updated = datetime.datetime.utcnow().isoformat()

        current_section = None
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## Status:"):
                state.current_status = stripped.replace("## Status:", "").strip()
            elif stripped.startswith("## Current Goal"):
                current_section = "goal"
            elif stripped.startswith("## Current Plan"):
                current_section = "plan"
            elif stripped.startswith("## Current Tasks"):
                current_section = "tasks"
            elif stripped.startswith("## Current Blockers"):
                current_section = "blockers"
            elif stripped.startswith("## Last Updated"):
                current_section = None
            elif (
                current_section == "goal" and stripped and not stripped.startswith("#")
            ):
                state.current_goal += stripped + "\n"
            elif (
                current_section == "plan" and stripped and not stripped.startswith("#")
            ):
                state.current_plan += stripped + "\n"
            elif current_section == "tasks" and stripped.startswith("- "):
                state.current_tasks.append(stripped[2:])
            elif current_section == "blockers" and stripped.startswith("- "):
                state.current_blockers.append(stripped[2:])

        state.current_goal = state.current_goal.strip()
        state.current_plan = state.current_plan.strip()
        return state


# ── State Manager ─────────────────────────────────────────────

_STATE_FILE = "STATE.md"


def _get_state_path(agent_id: str) -> Path:
    return AGENTS_DIR / agent_id / _STATE_FILE


def get_state(agent_id: str) -> AgentState:
    """Retrieve current state for an agent."""
    path = _get_state_path(agent_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return AgentState.from_markdown(f.read())
        except Exception as e:
            logger.warning(f"Failed to read state for {agent_id}: {e}")
    return AgentState()


def update_state(agent_id: str, **kwargs) -> AgentState:
    """Update specific state fields. Returns updated state."""
    state = get_state(agent_id)
    for key, value in kwargs.items():
        if hasattr(state, key):
            setattr(state, key, value)
    state.last_updated = datetime.datetime.utcnow().isoformat()
    _save_state(agent_id, state)

    # Emit events
    if kwargs.get("current_status") == "completed":
        event_bus.emit_simple("STATE", "state_completed", agent_id, state.to_dict())
    elif kwargs.get("current_blockers"):
        event_bus.emit_simple(
            "STATE", "state_blocked", agent_id, {"blockers": kwargs["current_blockers"]}
        )
    else:
        event_bus.emit_simple(
            "STATE", "state_updated", agent_id, {"fields": list(kwargs.keys())}
        )

    return state


def clear_state(agent_id: str) -> AgentState:
    """Reset state to idle defaults."""
    state = AgentState(
        current_status="idle", last_updated=datetime.datetime.utcnow().isoformat()
    )
    _save_state(agent_id, state)
    event_bus.emit_simple("STATE", "state_updated", agent_id, {"cleared": True})
    return state


def _save_state(agent_id: str, state: AgentState) -> None:
    """Write state to STATE.md atomically."""
    path = _get_state_path(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = state.to_markdown()
    import shutil
    import tempfile

    fd, tmp = tempfile.mkstemp(prefix=f".{_STATE_FILE}.tmp.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        shutil.move(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Capability API ────────────────────────────────────────────


def state_manage(
    action: str,
    agent_id: str,
    goal: Optional[str] = None,
    plan: Optional[str] = None,
    tasks: Optional[List[str]] = None,
    blockers: Optional[List[str]] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Capability API for state operations.

    Actions: get, update, clear
    """
    if action == "get":
        state = get_state(agent_id)
        return {"success": True, "state": state.to_dict()}

    elif action == "update":
        kwargs = {}
        if goal is not None:
            kwargs["current_goal"] = goal
        if plan is not None:
            kwargs["current_plan"] = plan
        if tasks is not None:
            kwargs["current_tasks"] = tasks
        if blockers is not None:
            kwargs["current_blockers"] = blockers
        if status is not None:
            kwargs["current_status"] = status
        state = update_state(agent_id, **kwargs)
        return {"success": True, "state": state.to_dict()}

    elif action == "clear":
        state = clear_state(agent_id)
        return {"success": True, "state": state.to_dict()}

    return {"success": False, "error": f"Unknown action: {action}"}
