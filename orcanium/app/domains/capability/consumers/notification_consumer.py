"""NotificationConsumer — delivers events to external channels via SinkManager.

Delivers notifiable events (review completed, skill changes, approval requests,
etc.) to registered sinks (Telegram, Discord, Slack, …) through the pluggable
SinkManager from the pipeline package.

Notifications are disabled by default. Enable with ``enable_notifications()``
or set ``ORCANIUM_NOTIFICATIONS_ENABLED=1``.

Architecture
============

1. ``handle_event`` is registered as an ``OrcaniumEventBus`` subscriber via
   ``consumer_registry`` in ``main.py``.
2. Each notifiable event is delivered to all enabled sinks via
   ``SinkManager.deliver_all()``.
3. Sinks write the notification to external channels (Telegram chat, Slack
   channel, Discord webhook, …).
4. The ``SinkManager`` provides idempotency so the same event is never
   delivered twice.

To register a new sink:

    from orcanium.app.pipeline import SinkManager, log_sink

    sink_mgr.register("my_sink", my_sink_fn, enabled=True, config={...})
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from orcanium.app.domains.capability.events import OrcaniumEvent
from orcanium.app.pipeline import PipelineStore, SinkManager, log_sink

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

_notifications_enabled = False


def enable_notifications() -> None:
    """Enable notification delivery (opt-in).

    Also controllable via ``ORCANIUM_NOTIFICATIONS_ENABLED=1`` environment
    variable at import time.
    """
    global _notifications_enabled
    _notifications_enabled = True
    logger.info("Notification delivery enabled")


def disable_notifications() -> None:
    """Disable notification delivery (default)."""
    global _notifications_enabled
    _notifications_enabled = False
    logger.info("Notification delivery disabled")


# Auto-enable from env var
if os.getenv("ORCANIUM_NOTIFICATIONS_ENABLED", "").strip() in ("1", "true", "yes"):
    _notifications_enabled = True

# ---------------------------------------------------------------------------
# Sink manager (lazy-initialised singleton)
# ---------------------------------------------------------------------------

_sink_manager: Optional[SinkManager] = None


def get_sink_manager() -> SinkManager:
    """Return the singleton SinkManager, creating it on first call."""
    global _sink_manager
    if _sink_manager is None:
        store = PipelineStore(
            os.getenv(
                "ORCANIUM_PIPELINE_STORE_PATH",
                os.path.expanduser("~/.orcanium/pipeline_store.json"),
            )
        )
        _sink_manager = SinkManager(store)

        # Register the built-in log sink for debugging
        _sink_manager.register("log", log_sink, enabled=True, order=-1)
        logger.debug("NotificationConsumer: SinkManager initialised")
    return _sink_manager


def reset_sink_manager() -> None:
    """Reset the sink manager singleton (for testing)."""
    global _sink_manager
    _sink_manager = None


# ---------------------------------------------------------------------------
# Notifiable event types
# ---------------------------------------------------------------------------

NOTIFIABLE_TYPES = frozenset({
    "review_completed",
    "skill_created",
    "skill_updated",
    "knowledge_candidate_promoted",
    "gateway_offline",
    "gateway_online",
    "approval_requested",
    "approval_granted",
    "approval_denied",
    "tool_failed",
    "memory_learned",
    "session_created",
    "agent_changed",
    "status_changed",
})


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------


def handle_event(event: OrcaniumEvent) -> None:
    """Consume an event and deliver it to all enabled notification sinks.

    This function is registered as an ``OrcaniumEventBus`` subscriber.  It
    filters for notifiable event types, builds a summary payload, and
    delivers via the ``SinkManager``.

    Idempotent: each unique ``event.event_id`` is delivered exactly once.
    """
    if not _notifications_enabled:
        return

    if event.event_type not in NOTIFIABLE_TYPES:
        return

    sink_mgr = get_sink_manager()

    # Build a notification payload
    payload = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "category": event.category,
        "agent_id": event.agent_id,
        "session_id": event.session_id or "",
        "timestamp": event.timestamp or "",
        "summary": _build_summary(event),
    }

    # Derive a unique sink key from the event_id for idempotency
    sink_key = f"event:{event.event_id}"

    try:
        import asyncio

        # Safely run the async delivery: use the running loop if available,
        # otherwise create a new one. This works in both sync dispatch
        # threads and async contexts.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to create one
            result = asyncio.run(sink_mgr.deliver_all(sink_key=sink_key, payload=payload))
        else:
            # Already in an event loop — create a task and run until done
            # (this blocks the caller but ensures delivery completes)
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    sink_mgr.deliver_all(sink_key=sink_key, payload=payload),
                    loop,
                ).result(timeout=30)
            else:
                result = loop.run_until_complete(
                    sink_mgr.deliver_all(sink_key=sink_key, payload=payload)
                )

        if not result.get("success"):
            logger.warning(
                "Notification delivery had failures for event %s: %s",
                event.event_id,
                result.get("results"),
            )
    except Exception as exc:
        logger.error(
            "Notification delivery failed for event %s: %s",
            event.event_id,
            exc,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_summary(event: OrcaniumEvent) -> str:
    """Build a human-readable summary of an event for notification text."""
    event_type = event.event_type.replace("_", " ").title()
    category = event.category.title()
    agent = event.agent_id
    return f"[{category}] {event_type} — {agent}"


# ---------------------------------------------------------------------------
# Gateway delivery helpers
# ---------------------------------------------------------------------------


async def send_to_gateway_channel(
    payload: dict,
    config: dict,
    existing: Optional[dict] = None,
) -> dict:
    """Sink function: deliver a notification via a gateway channel.

    Uses the ``GatewayRunner`` to send a message to the configured channel.

    Configuration expects:
        ``{"channel_id": "...", "platform": "telegram", "agent_name": "..."}``
    """
    if existing:
        logger.debug("send_to_gateway_channel: already delivered, skipping")
        return {"success": True, "skipped": True}

    channel_id = config.get("channel_id", "")
    platform = config.get("platform", "")
    agent_name = config.get("agent_name", payload.get("agent_id", ""))

    if not channel_id or not platform:
        logger.warning("send_to_gateway_channel: missing channel_id or platform")
        return {"success": False, "error": "missing channel_id or platform"}

    try:
        from orcanium.app.domains.gateway.manager import gateway_runner

        adapter = gateway_runner.get_adapter(channel_id)
        if adapter is None:
            return {"success": False, "error": f"no adapter for channel {channel_id}"}

        text = _build_summary(payload)
        if hasattr(adapter, "send_message"):
            adapter.send_message(channel_id, text)
            return {"success": True, "channel": channel_id, "platform": platform}

        return {"success": False, "error": "adapter has no send_message"}
    except Exception as exc:
        logger.error("send_to_gateway_channel failed: %s", exc)
        return {"success": False, "error": str(exc)}


__all__ = [
    "enable_notifications",
    "disable_notifications",
    "handle_event",
    "send_to_gateway_channel",
    "get_sink_manager",
    "reset_sink_manager",
]
