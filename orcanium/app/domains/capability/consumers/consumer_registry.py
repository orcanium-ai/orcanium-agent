"""ConsumerRegistry — lifecycle management for event bus consumers."""

import logging
from typing import Any, Callable, Dict, List, Optional

from orcanium.app.domains.capability.events import OrcaniumEvent, event_bus

logger = logging.getLogger(__name__)


class ConsumerRegistry:
    """Manages registration and lifecycle of event bus consumers.

    At startup, ``start()`` must be called to subscribe all registered
    consumers to the event bus via ``event_bus.subscribe_all(...)``.
    """

    def __init__(self):
        self._consumers: List[Callable[[OrcaniumEvent], None]] = []
        self._started = False

    def register(self, consumer: Callable[[OrcaniumEvent], None]) -> None:
        """Register a consumer callback. Safe to call before or after start()."""
        if consumer not in self._consumers:
            self._consumers.append(consumer)
            # If already started, subscribe immediately
            if self._started:
                event_bus.subscribe_all(consumer)
                logger.debug("Consumer registered (already started, subscribed immediately)")

    def unregister(self, consumer: Callable[[OrcaniumEvent], None]) -> None:
        """Unregister a consumer. Note: event_bus does not support unsubscribe natively."""
        if consumer in self._consumers:
            self._consumers.remove(consumer)

    def start(self) -> None:
        """Subscribe all registered consumers to the event bus.

        Must be called once at application startup (main.py startup_event).
        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._started:
            logger.warning("ConsumerRegistry already started — skipping duplicate start")
            return

        for consumer in self._consumers:
            event_bus.subscribe_all(consumer)

        self._started = True
        logger.info(
            f"ConsumerRegistry started — {len(self._consumers)} consumer(s) subscribed"
        )

    def stop(self) -> None:
        """Mark as stopped. event_bus does not support unsubscribe natively."""
        self._started = False
        logger.info("ConsumerRegistry stopped")

    @property
    def consumer_count(self) -> int:
        return len(self._consumers)

    @property
    def is_started(self) -> bool:
        return self._started


# Singleton
consumer_registry = ConsumerRegistry()
