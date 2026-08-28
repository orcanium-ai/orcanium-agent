"""AttentionEngine — ranks retrieved items by weighted scoring.

Relevance * 0.4 + Importance * 0.3 + Confidence * 0.2 + Recency * 0.1

Canonical implementation. No duplicates.
"""

import logging
import time
from typing import List

from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.cognition.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class AttentionEngine:
    """Rank retrieved items by relevance, importance, confidence, and recency."""

    def rank(
        self,
        items: List[RetrievalResult],
        top_k: int = 7,
        relevance_weight: float = 0.4,
        importance_weight: float = 0.3,
        confidence_weight: float = 0.2,
        recency_weight: float = 0.1,
    ) -> List[RetrievalResult]:
        """Rank items using weighted scoring."""
        if not items:
            return []

        start = time.time()

        scored: List[tuple] = []
        for item in items:
            importance = item.metadata.get("importance", 0.5)
            confidence = item.metadata.get("confidence", 0.5)

            score = (
                relevance_weight * item.relevance_score
                + importance_weight * importance
                + confidence_weight * confidence
                + recency_weight * 0.5
            )
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        elapsed = (time.time() - start) * 1000
        event_bus.emit_simple(
            "WORKFLOW",
            "attention_ranked",
            "system",
            {
                "items_in": len(items),
                "items_out": min(len(items), top_k),
                "elapsed_ms": round(elapsed, 0),
            },
        )

        return [item for _, item in scored[:top_k]]
