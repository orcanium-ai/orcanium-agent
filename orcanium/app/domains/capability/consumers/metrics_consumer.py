"""MetricsConsumer — collects event statistics for observability.

Currently a stub for future dashboard metrics aggregation.
"""

import logging
from typing import Dict, Any

from orcanium.app.domains.capability.events import OrcaniumEvent

logger = logging.getLogger(__name__)


class MetricsConsumer:
    """Collects event frequency and timing metrics.

    In future: expose via /api/v1/system/metrics endpoint.
    """

    def __init__(self):
        self._counts: Dict[str, int] = {}
        self._category_counts: Dict[str, int] = {}

    def handle_event(self, event: OrcaniumEvent) -> None:
        """Count events by type and category."""
        self._counts[event.event_type] = self._counts.get(event.event_type, 0) + 1
        self._category_counts[event.category] = self._category_counts.get(event.category, 0) + 1

    def get_counts(self) -> Dict[str, Any]:
        return {
            "total": sum(self._counts.values()),
            "by_type": dict(self._counts),
            "by_category": dict(self._category_counts),
        }


# Singleton
metrics_consumer = MetricsConsumer()
