"""Agent selection primitives shared by every Orcanium interface."""

from __future__ import annotations

from dataclasses import dataclass


class AgentSelectionError(ValueError):
    """Raised when an invocation cannot resolve a unique local agent."""


@dataclass(frozen=True)
class AgentSelection:
    name: str | None
    available: tuple[str, ...]


def resolve_agent_name(
    requested: str | None = None,
    *,
    require_explicit_when_multiple: bool = False,
) -> AgentSelection:
    """Resolve an agent from the durable local multi-agent registry.

    A requested name is always validated. With no request, a single configured
    agent is selected automatically; a multi-agent noninteractive invocation
    must select one explicitly. An empty registry returns ``None`` so the
    interactive setup flow can create the first agent.
    """
    from orcanium.app.agent.agent_manager import AgentManager
    from orcanium.app.core.db import AgentState, SessionLocal

    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        rows = (
            db.query(AgentState)
            .filter(AgentState.status != "archived")
            .order_by(AgentState.name)
            .all()
        )
        available = tuple(row.name for row in rows)
    finally:
        db.close()

    if requested:
        name = requested.strip()
        if name not in available:
            raise AgentSelectionError(
                f"Agent '{name}' is not configured. Available agents: "
                f"{', '.join(available) if available else 'none'}"
            )
        return AgentSelection(name=name, available=available)

    if len(available) == 1:
        return AgentSelection(name=available[0], available=available)
    if len(available) > 1 and require_explicit_when_multiple:
        raise AgentSelectionError(
            "Multiple agents are configured; pass --agent NAME. "
            f"Available agents: {', '.join(available)}"
        )
    return AgentSelection(name=None, available=available)
