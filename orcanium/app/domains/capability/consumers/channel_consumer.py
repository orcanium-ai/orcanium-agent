"""ChannelConsumer — translates EventBus events into channel operations.

Transport-only adapters remain responsible for platform API calls. This
consumer decides what is visible, formats human-facing progress text, and
delivers it to running adapters.
"""

import logging
from typing import TYPE_CHECKING, Optional

from orcanium.app.domains.capability.events import OrcaniumEvent

if TYPE_CHECKING:
    from orcanium.app.domains.channel.manager import ChannelRunner

logger = logging.getLogger(__name__)

_channel_runner: Optional["ChannelRunner"] = None

PROGRESS_EVENTS = {
    "tool_started",
    "reasoning_started",
    "execution_started",
    "retrieval_started",
}


def bind_channel(runner: "ChannelRunner") -> None:
    global _channel_runner
    _channel_runner = runner
    logger.info("ChannelConsumer bound to ChannelRunner")


def _event_name(event: OrcaniumEvent) -> str:
    return event.event_type


def _format_message(event: OrcaniumEvent) -> Optional[str]:
    payload = event.payload or {}
    name = _event_name(event)
    if name not in PROGRESS_EVENTS:
        return None
    if name == "tool_started":
        tool_name = payload.get("tool_name", "tool")
        return f"Using {tool_name}..."
    if name == "reasoning_started":
        return "Analyzing..."
    if name == "execution_started":
        path = payload.get("path", "")
        if path == "L1_TOOL":
            return "Preparing tools..."
        if path == "L2_RETRIEVAL":
            return "Searching memory..."
        if path == "L3_COGNITIVE":
            return "Thinking..."
        return "Writing response..."
    if name == "retrieval_started":
        return "Reading documentation..."
    return None


def _resolve_chat_id(event: OrcaniumEvent, adapter_channel_id: str) -> str:
    payload = event.payload or {}
    if payload.get("chat_id"):
        return payload["chat_id"]
    session_id = event.session_id or ""
    if session_id.startswith("telegram_"):
        return session_id.rsplit("_", 1)[-1]
    return payload.get("channel_id") or adapter_channel_id


def handle_event(event: OrcaniumEvent) -> None:
    runner = _channel_runner
    if runner is None:
        return

    text = _format_message(event)
    if text is None:
        return

    for adapter in runner.get_running_adapters():
        try:
            chat_id = _resolve_chat_id(event, adapter.channel_id)
            adapter.send_message(chat_id, text)
        except Exception as e:
            logger.warning(
                f"ChannelConsumer: adapter {adapter.channel_id} failed "
                f"to handle event {_event_name(event)}: {e}"
            )
