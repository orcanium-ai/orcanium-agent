"""Orcanium Event Bus — unified visibility layer for all agent activity.

Architecture (Phase 2):
    Producer → emit() → Queue → Dispatcher Thread → Consumers

    - Producers remain synchroorcanium (emit() returns immediately)
    - Consumers run in a dedicated dispatcher thread
    - Background workers safely emit without blocking

    When the dispatcher is not started, delivery is synchroorcanium (legacy mode).
"""

import datetime
import json
import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default queue capacity (backpressure limit)
_DEFAULT_QUEUE_CAPACITY = 500

# ── Event Categories ───────────────────────────────────────────

EVENT_CATEGORIES = {
    "SYSTEM",
    "TASK",
    "TOOL",
    "WORKFLOW",
    "MEMORY",
    "SKILL",
    "KNOWLEDGE",
    "STATE",
    "APPROVAL",
    "CHANNEL",
    "SESSION",
    "AGENT",
}

# ── Runtime Event Types ────────────────────────────────────────

MESSAGE_CHUNK      = "message_chunk"
TOOL_STARTED       = "tool_started"
TOOL_FINISHED      = "tool_finished"
TOOL_PROGRESS      = "tool_progress"
REASONING          = "reasoning"
WORKFLOW_STARTED   = "workflow_started"
WORKFLOW_FINISHED  = "workflow_finished"
MEMORY_UPDATED     = "memory_updated"
SKILL_UPDATED      = "skill_updated"
KNOWLEDGE_UPDATED  = "knowledge_updated"
STATE_UPDATED      = "state_updated"
APPROVAL_REQUESTED = "approval_requested"
CROSSTALK_REQUESTED = "crosstalk_requested"
CROSSTALK_ALLOWED = "crosstalk_allowed"
CROSSTALK_DENIED = "crosstalk_denied"
CROSSTALK_ANSWERED = "crosstalk_answered"
CROSSTALK_FAILED = "crosstalk_failed"
CHANNEL_STATUS     = "channel_status"
SESSION_CHANGED    = "session_changed"
SESSION_CREATED    = "session_created"
SESSION_LOADED     = "session_loaded"
SESSION_ACTIVE     = "session_active"
SESSION_UPDATED    = "session_updated"
SESSION_ARCHIVED   = "session_archived"
SESSION_CLOSED     = "session_closed"
AGENT_CHANGED      = "agent_changed"
STATUS_CHANGED     = "status_changed"

# ── Event Schema ───────────────────────────────────────────────


@dataclass
class OrcaniumEvent:
    """Base event with metadata for timeline reconstruction.

    All events include:
    event_id       Unique identifier (8-char hex)
    category       Event category (TOOL, MEMORY, WORKFLOW, etc.)
    event_type     Specific event name (tool_started, memory_added, etc.)
    agent_id       Originating agent
    session_id     Session context
    request_id     Request correlation id
    workflow_id    Workflow context (optional, for parent-child grouping)
    parent_event_id Parent event (optional, for hierarchy reconstruction)
    timestamp      ISO-8601 timestamp
    payload        Platform-neutral event data (dict, backward-compatible)
    """

    category: str
    event_type: str
    agent_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    workflow_id: Optional[str] = None
    parent_event_id: Optional[str] = None

    def __post_init__(self):
        import uuid

        if self.timestamp is None:
            self.timestamp = datetime.datetime.utcnow().isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())[:8]
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict.  Fields not in the original schema are only
        included when set, preserving backward compatibility for consumers
        that destructure against the original 5-field shape."""
        d: Dict[str, Any] = {
            "event_id": self.event_id,
            "category": self.category,
            "event_type": self.event_type,
            "type": self.event_type,
            "agent_id": self.agent_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }
        d["session_id"] = self.session_id or ""
        if self.workflow_id:
            d["workflow_id"] = self.workflow_id
        if self.parent_event_id:
            d["parent_event_id"] = self.parent_event_id
        return d


# ── Typed Events (Phase 5, backward-compatible) ─────────────

# These typed event constructors extend OrcaniumEvent with semantic
# payload builders.  They return standard OrcaniumEvent instances,
# keeping external serialization unchanged.


def make_tool_event(
    event_type: str,
    tool_name: str,
    toolset: str = "",
    duration_ms: float = 0.0,
    success: bool = True,
    error: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed tool event (tool_started / tool_completed / tool_failed)."""
    payload: Dict[str, Any] = {
        "tool_name": tool_name,
        "toolset": toolset,
    }
    if duration_ms:
        payload["duration_ms"] = round(duration_ms, 0)
    payload["success"] = success
    if error:
        payload["error"] = error
    return OrcaniumEvent(
        category="TOOL",
        event_type=event_type,
        agent_id=agent_id,
        payload=payload,
        session_id=session_id,
        request_id=request_id,
        workflow_id=workflow_id,
        parent_event_id=parent_event_id,
    )


def make_memory_event(
    event_type: str,
    content: str = "",
    category: str = "OTHER",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed memory event (memory_added / memory_deleted / memory_learned)."""
    return OrcaniumEvent(
        category="MEMORY",
        event_type=event_type,
        agent_id=agent_id,
        payload={"content_preview": content[:100], "category": category},
        session_id=session_id,
        request_id=request_id,
        workflow_id=workflow_id,
    )


def make_skill_event(
    event_type: str,
    skill_name: str = "",
    skill_id: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed skill event (skill_created / skill_updated / etc.)."""
    return OrcaniumEvent(
        category="SKILL",
        event_type=event_type,
        agent_id=agent_id,
        payload={"skill_name": skill_name, "skill_id": skill_id},
        session_id=session_id,
        request_id=request_id,
    )


def make_knowledge_event(
    event_type: str,
    content: str = "",
    score: float = 0.0,
    candidate_id: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed knowledge event (knowledge_candidate_*)."""
    return OrcaniumEvent(
        category="KNOWLEDGE",
        event_type=event_type,
        agent_id=agent_id,
        payload={
            "content_preview": content[:100],
            "score": round(score, 3),
            "candidate_id": candidate_id,
        },
        session_id=session_id,
        request_id=request_id,
        workflow_id=workflow_id,
    )


def make_state_event(
    event_type: str,
    status: str = "",
    goal: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed state event (state_updated / state_completed / state_blocked)."""
    return OrcaniumEvent(
        category="STATE",
        event_type=event_type,
        agent_id=agent_id,
        payload={"current_status": status, "current_goal": goal[:100]},
        session_id=session_id,
        request_id=request_id,
        parent_event_id=parent_event_id,
    )


def make_workflow_event(
    event_type: str,
    path: str = "",
    elapsed_ms: float = 0.0,
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed workflow event (execution_*, reasoning_*, retrieval_*)."""
    return OrcaniumEvent(
        category="WORKFLOW",
        event_type=event_type,
        agent_id=agent_id,
        payload={"path": path, "elapsed_ms": round(elapsed_ms, 0)},
        session_id=session_id,
        request_id=request_id,
        workflow_id=workflow_id,
        parent_event_id=parent_event_id,
    )


def make_gateway_event(
    event_type: str,
    channel_id: str = "",
    platform: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed channel event (channel_online / channel_offline)."""
    return OrcaniumEvent(
        category="CHANNEL",
        event_type=event_type,
        agent_id=agent_id,
        payload={"channel_id": channel_id, "platform": platform},
        session_id=session_id,
        request_id=request_id,
    )


def make_message_chunk_event(
    delta: str,
    agent_id: str = "system",
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build an ephemeral MessageChunk event for LLM token streaming.

    Consumed by: Gateway (progressive message editing), SSE (live UI).
    NOT persisted to Timeline — Timeline stores final execution evidence only.
    """
    return OrcaniumEvent(
        category="WORKFLOW",
        event_type="message_chunk",
        agent_id=agent_id,
        payload={"delta": delta},
        session_id=session_id,
        request_id=request_id,
        workflow_id=workflow_id,
    )


def make_approval_event(
    event_type: str,
    request_id: str = "",
    requested_by: str = "",
    agent_id: str = "system",
    session_id: Optional[str] = None,
) -> OrcaniumEvent:
    """Build a typed approval event (approval_requested / granted / denied)."""
    return OrcaniumEvent(
        category="APPROVAL",
        event_type=event_type,
        agent_id=agent_id,
        payload={"request_id": request_id, "requested_by": requested_by},
        session_id=session_id,
        request_id=request_id or None,
    )


class OrcaniumEventBus:
    """Unified event bus — single stream for all agent activity.

    Two delivery modes:
        Synchroorcanium (default, legacy):
            emit() → direct subscriber callbacks

        Asynchroorcanium (Phase 2, enable via start_async_dispatcher()):
            emit() → Queue → Dispatcher Thread → subscriber callbacks

    Background workers should always use async mode to avoid blocking.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[OrcaniumEvent] = []
        self._max_history = 1000

        # Async dispatch (Phase 2)
        self._async_enabled = False
        self._queue: Optional["queue.Queue"] = None
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ── Async Dispatch (Phase 2) ─────────────────────────────────

    def start_async_dispatcher(self, capacity: int = _DEFAULT_QUEUE_CAPACITY) -> None:
        """Start the async dispatcher thread.

        When active, ``emit()`` enqueues events and returns immediately.
        A background thread delivers them to subscribers asynchroorcaniumly.
        """
        if self._async_enabled:
            logger.warning("Async dispatcher already running")
            return

        self._queue = queue.Queue(maxsize=capacity)
        self._stop_event.clear()
        self._async_enabled = True
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_loop,
            name="eventbus-dispatcher",
            daemon=True,
        )
        self._dispatcher_thread.start()
        logger.info(
            f"EventBus async dispatcher started (queue capacity={capacity})"
        )

    def stop_async_dispatcher(self, timeout: float = 5.0) -> None:
        """Gracefully stop the async dispatcher thread.

        Drains remaining events before stopping.
        Falls back to synchroorcanium delivery after stop.
        """
        if not self._async_enabled:
            return

        self._stop_event.set()
        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=timeout)
        self._async_enabled = False
        self._queue = None
        self._dispatcher_thread = None
        logger.info("EventBus async dispatcher stopped (falling back to sync)")

    @property
    def is_async(self) -> bool:
        """Whether the async dispatcher is currently active."""
        return self._async_enabled

    # ── Subscription ────────────────────────────────────────────

    def subscribe(
        self, category: str, callback: Callable[[OrcaniumEvent], None]
    ) -> None:
        """Subscribe to all events in a category."""
        if category not in self._subscribers:
            self._subscribers[category] = []
        self._subscribers[category].append(callback)

    def subscribe_all(self, callback: Callable[[OrcaniumEvent], None]) -> None:
        """Subscribe to ALL events."""
        self.subscribe("__all__", callback)

    # ── Emission ────────────────────────────────────────────────

    def emit(self, event: OrcaniumEvent) -> None:
        """Emit an event.

        In async mode: enqueues and returns immediately (non-blocking).
        In sync mode (default): delivers to subscribers inline.

        History is always updated synchroorcaniumly before dispatch.
        """
        # Always store in history synchroorcaniumly
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        if self._async_enabled and self._queue is not None:
            # Async: enqueue with bounded backpressure
            try:
                self._queue.put_nowait(event)
            except queue.Full:
                try:
                    self._queue.put(event, timeout=0.5)
                except queue.Full:
                    logger.warning(
                        f"EventBus queue full after retry — dropping event "
                        f"{event.event_type} (category={event.category})"
                    )
        else:
            # Sync: deliver inline (legacy mode)
            self._deliver(event)

    def emit_simple(
        self,
        category: str,
        event_type: str,
        agent_id: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> OrcaniumEvent:
        """Create and emit an event in one call."""
        event = OrcaniumEvent(
            category=category,
            event_type=event_type,
            agent_id=agent_id,
            payload=payload or {},
            session_id=session_id,
            request_id=request_id,
        )
        self.emit(event)
        return event

    # ── Dispatch ────────────────────────────────────────────────

    def _deliver(self, event: OrcaniumEvent) -> None:
        """Deliver an event to all matching subscribers.

        Error isolation: a failing subscriber never blocks other subscribers.
        """
        # Category subscribers
        for cb in self._subscribers.get(event.category, []):
            try:
                cb(event)
            except Exception as e:
                logger.warning(
                    f"Subscriber failed for {event.event_type}: {e}"
                )

        # All-catch subscribers
        for cb in self._subscribers.get("__all__", []):
            try:
                cb(event)
            except Exception as e:
                logger.warning(
                    f"Global subscriber failed for {event.event_type}: {e}"
                )

        logger.debug(
            f"Event: [{event.category}] {event.event_type} ({event.agent_id})"
        )

    def _dispatch_loop(self) -> None:
        """Background loop: drain queue and deliver events asynchroorcaniumly."""
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.5)
                self._deliver(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Dispatcher thread error: {e}")

    # ── History ─────────────────────────────────────────────────

    def get_history(
        self,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent events, optionally filtered."""
        events = self._history
        if category:
            events = [e for e in events if e.category == category]
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        return [e.to_dict() for e in events[-limit:]]

    def clear(self) -> None:
        """Clear event history."""
        self._history = []


# Singleton
event_bus = OrcaniumEventBus()
