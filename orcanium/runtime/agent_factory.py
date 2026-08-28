"""Single construction boundary for local Orcanium agent instances."""

from __future__ import annotations

from typing import Any, Type


def create_agent(*, agent_class: Type[Any] | None = None, **options: Any) -> Any:
    """Construct one local agent with the caller's resolved runtime options.

    Interface adapters resolve their own presentation callbacks and session
    policies, but construction goes through this boundary. The optional class
    injection keeps the boundary unit-testable without importing the full
    provider/tool stack.
    """
    if agent_class is None:
        from run_agent import AIAgent

        agent_class = AIAgent
    return agent_class(**options)
