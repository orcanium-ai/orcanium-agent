"""skill_manage — capability API for skill operations.

The ONLY supported write path for skills.
"""

import datetime
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.domains.capability.events import event_bus

logger = logging.getLogger(__name__)

# ── Skill Model ────────────────────────────────────────────────

SKILL_STATES = {"ACTIVE", "DORMANT"}


@dataclass
class Skill:
    id: str
    title: str
    description: str = ""
    workflow: str = ""
    examples: str = ""
    state: str = "ACTIVE"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_used: Optional[str] = None
    use_count: int = 0
    importance: float = 0.5
    executable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "workflow": self.workflow,
            "examples": self.examples,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "importance": self.importance,
            "executable": self.executable,
        }


# ── Internal helpers ───────────────────────────────────────────


def _parse_skills(content: str) -> List[Skill]:
    """Parse SKILL.md into Skill objects."""
    import re
    import uuid

    skills = []
    current: Optional[Dict] = None
    current_field = None

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            if current:
                skills.append(Skill(**current))
            current_id = str(uuid.uuid4())[:8]
            title = stripped.lstrip("# ").strip()
            current = {
                "id": current_id,
                "title": title,
                "state": "ACTIVE",
                "created_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat(),
                "use_count": 0,
            }
            current_field = None
        elif current:
            if stripped.startswith("## description"):
                current_field = "description"
            elif stripped.startswith("## workflow"):
                current_field = "workflow"
            elif stripped.startswith("## examples"):
                current_field = "examples"
            elif stripped.startswith("## state:"):
                state = stripped.replace("## state:", "").strip().upper()
                if state in SKILL_STATES:
                    current["state"] = state
                current_field = None
            elif current_field and stripped and not stripped.startswith("#"):
                current[current_field] = (
                    current.get(current_field, "") + stripped + "\n"
                )

    if current:
        skills.append(Skill(**current))

    return skills


def _skills_to_markdown(skills: List[Skill]) -> str:
    """Serialize Skill objects back to SKILL.md format."""
    parts = []
    for s in skills:
        parts.append(f"# {s.title}")
        if s.description:
            parts.append(f"## description\n{s.description.strip()}")
        if s.workflow:
            parts.append(f"## workflow\n{s.workflow.strip()}")
        if s.examples:
            parts.append(f"## examples\n{s.examples.strip()}")
        parts.append(f"## state: {s.state}")
    return "\n\n".join(parts)


# ── Capability API ─────────────────────────────────────────────


def skill_manage(
    action: str,
    agent_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    workflow: Optional[str] = None,
    examples: Optional[str] = None,
    state: Optional[str] = None,
    skill_id: Optional[str] = None,
    search_query: Optional[str] = None,
    origin: str = "background_review",
    executable: bool = False,
) -> Dict[str, Any]:
    """Capability API for skill operations.

    Supported actions: create, update, retrieve, search, set_state
    """
    files = AgentManager.get_agent_files(agent_id)
    content = files.get("SKILL.md", "")
    skills = _parse_skills(content)

    if action == "create":
        if not title:
            return {"success": False, "error": "title required"}
        import uuid

        new_skill = Skill(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description or "",
            workflow=workflow or "",
            examples=examples or "",
            state="ACTIVE",
            executable=executable,
        )
        skills.append(new_skill)
        _write_skills(agent_id, skills)

        # Auto-register in ToolRegistry
        try:
            from orcanium.app.tools.skill_bridge import register_skill_tools

            register_skill_tools(agent_id)
        except Exception as reg_err:
            logger.warning(f"Skill tool registration failed: {reg_err}")

        event_bus.emit_simple(
            "SKILL",
            "skill_created",
            agent_id,
            {"title": title, "skill_id": new_skill.id},
        )
        return {"success": True, "skill": new_skill.to_dict()}

    elif action == "update":
        if not skill_id and not title:
            return {"success": False, "error": "skill_id or title required"}
        target = _find_skill(skills, skill_id, title)
        if not target:
            return {"success": False, "error": "skill not found"}
        if description is not None:
            target.description = description
        if workflow is not None:
            target.workflow = workflow
        if examples is not None:
            target.examples = examples
        if state is not None and state in SKILL_STATES:
            target.state = state
        target.updated_at = datetime.datetime.utcnow().isoformat()
        _write_skills(agent_id, skills)
        event_bus.emit_simple(
            "SKILL", "skill_updated", agent_id, {"title": target.title}
        )
        return {"success": True, "skill": target.to_dict()}

    elif action == "set_state":
        if not skill_id and not title:
            return {"success": False, "error": "skill_id or title required"}
        if not state or state not in SKILL_STATES:
            return {"success": False, "error": f"state must be one of {SKILL_STATES}"}
        target = _find_skill(skills, skill_id, title)
        if not target:
            return {"success": False, "error": "skill not found"}
        old_state = target.state
        target.state = state
        target.updated_at = datetime.datetime.utcnow().isoformat()
        _write_skills(agent_id, skills)
        event_type = "skill_reactivated" if state == "ACTIVE" else "skill_dormant"
        event_bus.emit_simple(
            "SKILL",
            event_type,
            agent_id,
            {
                "title": target.title,
                "old_state": old_state,
                "new_state": state,
            },
        )
        return {"success": True, "skill": target.to_dict()}

    elif action == "retrieve":
        return {
            "success": True,
            "skills": [s.to_dict() for s in skills],
            "count": len(skills),
            "active": len([s for s in skills if s.state == "ACTIVE"]),
            "dormant": len([s for s in skills if s.state == "DORMANT"]),
        }

    elif action == "search":
        if not search_query:
            return {"success": False, "error": "search_query required"}
        q = search_query.lower()
        matches = [
            s for s in skills if q in s.title.lower() or q in s.description.lower()
        ]
        return {
            "success": True,
            "skills": [s.to_dict() for s in matches],
            "count": len(matches),
        }

    return {"success": False, "error": f"Unknown action: {action}"}


def _find_skill(
    skills: List[Skill], skill_id: Optional[str], title: Optional[str]
) -> Optional[Skill]:
    for s in skills:
        if skill_id and s.id == skill_id:
            return s
        if title and s.title.lower() == title.lower():
            return s
    return None


def _write_skills(agent_id: str, skills: List[Skill]) -> None:
    """Write skills back to SKILL.md on disk."""
    content = _skills_to_markdown(skills)
    skill_path = AgentManager.get_agent_dir(agent_id) / "SKILL.md"
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(content)
