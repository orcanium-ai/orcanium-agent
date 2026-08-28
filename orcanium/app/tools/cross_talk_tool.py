"""Agent-facing entry point for persistent cross-talk requests."""

from orcanium.app.core.db import SessionLocal
from orcanium.app.domains.capability.cross_talk import request_cross_talk
from orcanium.app.tools.registry import registry

SCHEMA = {
    "type": "object",
    "properties": {
        "target_agent_id": {"type": "string", "description": "Agent to ask"},
        "request": {"type": "string", "description": "Bounded question or task"},
        "context_summary": {"type": "string", "description": "Optional relevant context"},
    },
    "required": ["target_agent_id", "request"],
}


def cross_talk(args, **kwargs):
    source_agent_id = kwargs.get("agent_name") or kwargs.get("parent_agent")
    if not source_agent_id:
        return {"error": "cross_talk requires an agent runtime context"}
    db = SessionLocal()
    try:
        item = request_cross_talk(
            db, source_agent_id, args["target_agent_id"], args["request"],
            source_session_id=kwargs.get("session_id"),
            context_summary=args.get("context_summary"),
        )
        return {"request_id": item.id, "status": item.status,
                "message": "Request submitted for target-agent approval."}
    finally:
        db.close()


registry.register(
    name="cross_talk", toolset="agent_communication", schema=SCHEMA,
    handler=cross_talk, emoji="↔️",
)
