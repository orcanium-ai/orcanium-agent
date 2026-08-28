"""TimelineConsumer — persists meaningful events to the TimelineStore.

Timeline stores durable execution evidence, NOT ephemeral events.

Persisted:
    Memory Updated, Knowledge Promoted, Workflow Completed,
    Approval Requested, Skill Learned, State Changed,
    Review Finished, Gateway Offline

NOT persisted:
    Heartbeat, Token delta (message_chunk), Progress spam, Internal polling
"""

import logging
from typing import Optional

from orcanium.app.domains.capability.events import OrcaniumEvent
from orcanium.app.domains.capability.timeline.timeline_store import TimelineStore

logger = logging.getLogger(__name__)

# Ephemeral event types that are NOT persisted to the Timeline
_EPHEMERAL_EVENTS = {
    "message_chunk",       # LLM token streaming
    "tool_started",        # Progress — final result is what matters
    "retrieval_started",   # Progress
    "attention_ranked",    # Internal processing
    "working_memory_created",  # Internal state
    "reasoning_started",   # Progress
    "execution_started",   # Progress
}

# Shared store instance (lazy-init, one per process)
_store: Optional[TimelineStore] = None


def _get_store() -> TimelineStore:
    """Get or create the shared TimelineStore."""
    global _store
    if _store is None:
        _store = TimelineStore()
    return _store


def _is_meaningful(event: OrcaniumEvent) -> bool:
    """Filter: only meaningful/terminal events should be persisted."""
    if event.event_type in _EPHEMERAL_EVENTS:
        return False
    # Always persist gateway, approval, and system events
    if event.category in ("CHANNEL", "APPROVAL", "SYSTEM"):
        return True
    # Terminal workflow events
    if event.event_type in (
        "execution_completed", "execution_failed",
        "reasoning_completed", "retrieval_completed",
        "tool_completed", "tool_failed",
        "knowledge_candidate_promoted", "knowledge_candidate_rejected",
    ):
        return True
    # All memory, skill, state, knowledge events are meaningful
    if event.category in ("MEMORY", "SKILL", "KNOWLEDGE", "STATE"):
        return True
    return True  # Default: persist


def handle_event(event: OrcaniumEvent) -> None:
    """Receive an event bus emission and persist meaningful events.

    Ephemeral events (message_chunk, progress indicators) are filtered out.
    Timeline stores durable execution evidence only.
    """
    if not _is_meaningful(event):
        return

    try:
        store = _get_store()
        store.append(event)
    except Exception as e:
        logger.warning(f"TimelineConsumer failed to persist event {event.event_type}: {e}")
