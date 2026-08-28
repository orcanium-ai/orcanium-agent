"""Shared pipeline types — enums, dataclasses, state-machine constants, and
exception hierarchy used across all Orcanium pipelines.

This module is the single source of truth for:

- Pipeline stage enums (``PipelineStage``)
- Pipeline status enums (``PipelineStatus``)
- Active / terminal state sets for state-machine transitions
- Retryable exception hierarchy (``PipelineError`` → ``PipelineRetryableError``)
- Deduplication helpers (``build_notification_receipt_key``)
- Stage and pipeline result dataclasses
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# State-machine constants
# ---------------------------------------------------------------------------

TERMINAL_PIPELINE_STATES: Set[str] = {
    "completed",
    "failed",
    "retry_scheduled",
    "cancelled",
}

DEFAULT_ACTIVE_PIPELINE_STATES: Set[str] = {
    "pending",
    "running",
    "received",
}

ACTIVE_PIPELINE_STATES: Set[str] = {
    "received",
    "pending",
    "running",
    "resolving_meeting",
    "fetching_transcript",
    "downloading_recording",
    "transcribing_audio",
    "summarizing",
    "sending_sinks",
}


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class PipelineError(RuntimeError):
    """Base class for all pipeline failures."""


class PipelineRetryableError(PipelineError):
    """Raised when the pipeline should be retried later.

    Pipelines that catch this exception transition to ``retry_scheduled``
    status instead of ``failed``.
    """


class PipelineSinkError(PipelineError):
    """Raised when an output sink fails (non-retryable by default)."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStage(str, enum.Enum):
    """Every stage in the conversation pipeline."""
    INTENT_CLASSIFY = "intent_classify"
    COGNITIVE_ROUTE = "cognitive_route"
    RETRIEVAL_PLAN = "retrieval_plan"
    ATTENTION = "attention"
    WORKING_MEMORY = "working_memory"
    PROMPT_ASSEMBLY = "prompt_assembly"
    MODEL_GENERATE = "model_generate"
    TOOL_EXECUTE = "tool_execute"
    CAPABILITY = "capability"
    RESPONSE_BUILD = "response_build"
    MEMORY_COMMIT = "memory_commit"
    SESSION_UPDATE = "session_update"
    TIMELINE = "timeline"
    BACKGROUND_REVIEW = "background_review"


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


class ExecutionMode(str, enum.Enum):
    SYNCHROORCANIUM = "synchroorcanium"
    BACKGROUND = "background"
    FOREGROUND = "foreground"


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: PipelineStage
    status: PipelineStatus = PipelineStatus.PENDING
    elapsed_ms: float = 0.0
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


@dataclass
class PipelineResult:
    """Complete result of a conversation pipeline execution."""
    session_id: str
    assistant_message: str = ""
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    stages: List[StageResult] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_elapsed_ms: float = 0.0
    error: Optional[str] = None
    status: PipelineStatus = PipelineStatus.PENDING
    reflection_status: str = "disabled"
    events: List[Dict[str, Any]] = field(default_factory=list)


__all__ = [
    # State constants
    "TERMINAL_PIPELINE_STATES",
    "ACTIVE_PIPELINE_STATES",
    "DEFAULT_ACTIVE_PIPELINE_STATES",
    # Exception hierarchy
    "PipelineError",
    "PipelineRetryableError",
    "PipelineSinkError",
    # Enums
    "PipelineStage",
    "PipelineStatus",
    "ExecutionMode",
    "PipelineStageResult",
    # Dataclasses
    "StageResult",
    "PipelineResult",
]
