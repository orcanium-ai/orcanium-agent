"""TurnContext — immutable runtime state for one conversation turn."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class AgentScope:
    """Identity carried across one runtime turn."""

    agent_id: str
    session_id: Optional[str] = None
    channel_id: Optional[str] = None
    source: str = "api"
    user_id: Optional[str] = None


@dataclass
class TurnContext:
    """Immutable runtime state for a single conversation turn.

    Created at the start of each pipeline execution and passed through
    every stage. Never mutated in place — stages return new context or
    add results to TurnResult.
    """

    scope: AgentScope
    user_content: str
    conversation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    # Cognitive state (populated by pipeline stages)
    intent: str = ""
    route: str = ""
    working_memory: Optional[Dict[str, Any]] = None
    prompt: str = ""

    # Provider state
    provider: str = ""
    model: str = ""

    # Callbacks (from CLI/TUI/Gateway)
    delta_callback: Optional[Callable] = None
    tool_callback: Optional[Callable] = None
    thinking_callback: Optional[Callable] = None
    clarify_callback: Optional[Callable] = None

    # Metadata
    user_metadata: Optional[Dict[str, Any]] = None

    @property
    def agent_name(self) -> str:
        """Compatibility alias for callers being migrated to ``scope``."""
        return self.scope.agent_id

    @property
    def session_id(self) -> Optional[str]:
        return self.scope.session_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.scope.agent_id,
            "session_id": self.scope.session_id,
            "conversation_id": self.conversation_id,
            "trace_id": self.trace_id,
            "intent": self.intent,
            "route": self.route,
            "provider": self.provider,
            "model": self.model,
        }
