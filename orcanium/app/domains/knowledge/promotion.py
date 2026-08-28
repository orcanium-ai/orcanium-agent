"""Knowledge Promotion — promotes validated candidates through the pipeline.

Curator only receives validated (APPROVED) candidates.
Never scans raw conversations.
"""

import logging
from typing import Optional

from orcanium.app.domains.knowledge.promotion_queue import (
    approve, list_pending, list_approved, promote, reject,
)
from orcanium.app.domains.knowledge.validator import validate, fetch_existing_contents

logger = logging.getLogger(__name__)


def curator_tick(agent_name: Optional[str] = None) -> int:
    """Process one round of candidate validation and promotion.

    1. Fetch PENDING candidates (optionally for one agent)
    2. Run each through the 4-gate validator
    3. APPROVED candidates move to APPROVED status
    4. REJECTED candidates are rejected with reason
    5. APPROVED candidates are promoted to KnowledgeEntry

    Returns: number of candidates promoted.
    """
    pending = list_pending(agent_name=agent_name)
    if not pending:
        return 0

    existing = fetch_existing_contents(agent_name or "")
    promoted_count = 0

    for cand in pending:
        result = validate(
            content=cand["content"],
            category=cand["category"],
            evidence_count=cand.get("evidence_count", 1),
            existing_entries=existing,
        )

        if result["status"] == "approved":
            approve(cand["id"], score=result["score"], reason=result["reason"])
            entry = promote(cand["id"])
            if entry:
                promoted_count += 1
                existing.append(cand["content"])
                logger.info("Curator promoted candidate %s for agent '%s'",
                            cand["id"], cand.get("agent_name", "?"))
        else:
            reject(cand["id"], reason=result["reason"])
            logger.info("Curator rejected candidate %s: %s",
                        cand["id"], result["reason"])

    return promoted_count


def validate_and_enqueue(agent_name: str, content: str, category: str = "FACT",
                         confidence: float = 0.5, evidence_count: int = 1) -> None:
    """Validate a candidate and enqueue it if it passes.

    Called by the Memory Distiller after distillation completes.
    """
    result = validate(
        content=content,
        category=category,
        evidence_count=evidence_count,
        existing_entries=fetch_existing_contents(agent_name),
    )

    if result["status"] == "approved":
        from orcanium.app.domains.knowledge.promotion_queue import enqueue
        cid = enqueue(agent_name, content, category, confidence, evidence_count)
        if cid:
            logger.info("Enqueued validated candidate %s for agent '%s' (score: %s)",
                        cid, agent_name, result["score"])
    else:
        logger.debug("Candidate rejected by validator for agent '%s': %s",
                     agent_name, result["reason"])
