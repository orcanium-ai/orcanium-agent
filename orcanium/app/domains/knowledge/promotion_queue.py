"""Promotion Queue — SQLite-backed queue for knowledge candidate lifecycle.

Curator processes: PENDING → APPROVED → PROMOTED
Invalid entries are REJECTED.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from orcanium.app.core.db import SessionLocal
from orcanium.app.core.db import KnowledgeCandidate as KCModel

logger = logging.getLogger(__name__)


def enqueue(agent_name: str, content: str, category: str = "FACT",
            confidence: float = 0.5, evidence_count: int = 1) -> Optional[str]:
    """Add a candidate to the promotion queue."""
    from orcanium.app.domains.knowledge.knowledge_candidate import add_candidate
    result = add_candidate(agent_name, content, category, confidence, evidence_count)
    return result.get("id")


def approve(candidate_id: str, score: float = 0.0, reason: Optional[str] = None) -> bool:
    """Approve a candidate (moves to APPROVED status)."""
    from orcanium.app.domains.knowledge.knowledge_candidate import update_status
    return update_status(candidate_id, "APPROVED", reason=reason, score=score)


def reject(candidate_id: str, reason: str = "Rejected by validator") -> bool:
    """Reject a candidate."""
    from orcanium.app.domains.knowledge.knowledge_candidate import update_status
    return update_status(candidate_id, "REJECTED", reason=reason)


def promote(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Promote an APPROVED candidate to KnowledgeEntry."""
    from orcanium.app.domains.knowledge.knowledge_candidate import promote_to_knowledge
    return promote_to_knowledge(candidate_id)


def list_pending(agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all PENDING candidates."""
    from orcanium.app.domains.knowledge.knowledge_candidate import get_candidates
    return get_candidates(agent_name=agent_name, status="PENDING")


def list_approved(agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all APPROVED candidates waiting for promotion."""
    from orcanium.app.domains.knowledge.knowledge_candidate import get_candidates
    return get_candidates(agent_name=agent_name, status="APPROVED")


def health() -> Dict[str, int]:
    """Return counts per status across all agents."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        rows = db.query(KCModel.status, func.count(KCModel.id)).group_by(KCModel.status).all()
        counts = {row[0]: row[1] for row in rows}
        for s in ("PENDING", "APPROVED", "REJECTED", "PROMOTED", "REVIEWING"):
            counts.setdefault(s, 0)
        return counts
    finally:
        db.close()
