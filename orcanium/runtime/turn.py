"""Interface-neutral execution of a single agent turn.

TUI, non-interactive CLI, and messaging channels own their own rendering and
session policies. They all invoke an ``AIAgent`` turn through this module so
the execution contract has one home.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Mapping, Sequence


def run_agent_turn(
    agent: Any,
    user_message: Any,
    *,
    conversation_history: Sequence[Mapping[str, Any]] | None = None,
    task_id: str | None = None,
    stream_callback: Callable[[str], None] | None = None,
    persist_user_message: Any = None,
) -> dict[str, Any]:
    """Run one agent turn with only supported optional arguments.

    The compatibility check keeps this boundary usable by agent-like runtime
    implementations while the project completes the move to a single core.
    ``persist_user_message`` is intentionally omitted when ``None`` because
    it changes the agent's default persistence behavior.
    """
    kwargs: dict[str, Any] = {}
    candidates = {
        "conversation_history": conversation_history,
        "task_id": task_id,
        "stream_callback": stream_callback,
    }
    if persist_user_message is not None:
        candidates["persist_user_message"] = persist_user_message

    try:
        supported = inspect.signature(agent.run_conversation).parameters
    except (TypeError, ValueError):
        supported = {}

    for name, value in candidates.items():
        if value is not None and (not supported or name in supported):
            kwargs[name] = value

    result = agent.run_conversation(user_message, **kwargs)
    if not isinstance(result, dict):
        raise TypeError("Agent runtime returned a non-mapping turn result")
    return result
