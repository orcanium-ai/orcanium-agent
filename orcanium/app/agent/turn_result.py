"""TurnResult — single output of the conversation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TurnResult:
    """Single output of one pipeline execution.

    Returned by ConversationPipeline.execute().
    Contains everything produced during the turn.
    """

    session_id: str
    assistant_message: str = ""
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_elapsed_ms: float = 0.0
    error: Optional[str] = None
    reflection_status: str = "disabled"
    events: List[Dict[str, Any]] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)
    provider_info: Optional[Dict[str, str]] = None
    session_changes: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_response": self.assistant_message,
            "tools_executed": self.tool_results,
            "reflection_status": self.reflection_status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_elapsed_ms": self.total_elapsed_ms,
            "error": self.error,
        }
