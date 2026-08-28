"""KnowledgeCandidate — SQLite-backed candidate store.

Created by the Memory Distiller or Review Worker. Persisted across restarts.
Must pass the Knowledge Validator (4 gates) before promotion to KnowledgeEntry.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

from orcanium.app.core.db import KnowledgeCandidate as KCModel, SessionLocal

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"FACT", "RULE", "REFERENCE", "CONCEPT"}
VALID_STATUSES = {"PENDING", "APPROVED", "REJECTED", "PROMOTED", "REVIEWING"}


def add_candidate(
    agent_name: str,
    content: str,
    category: str = "FACT",
    confidence: float = 0.5,
    evidence_count: int = 1,
    source: str = "distiller",
) -> Dict[str, Any]:
    """Create a new knowledge candidate (persisted in SQLite)."""
    if category not in VALID_CATEGORIES:
        category = "FACT"
    now = datetime.datetime.utcnow().isoformat()
    db = SessionLocal()
    try:
        cand = KCModel(
            id=uuid.uuid4().hex[:12],
            agent_name=agent_name,
            content=content,
            category=category,
            confidence=confidence,
            evidence_count=evidence_count,
            status="PENDING",
            score=0.0,
            created_at=now,
            updated_at=now,
        )
        db.add(cand)
        db.commit()
        logger.info("Knowledge candidate added for agent '%s': %s", agent_name, content[:60])
        return {"id": cand.id, "status": "PENDING"}
    finally:
        db.close()


def get_candidates(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List candidates, optionally filtered by agent and/or status."""
    db = SessionLocal()
    try:
        q = db.query(KCModel)
        if agent_name:
            q = q.filter(KCModel.agent_name == agent_name)
        if status:
            q = q.filter(KCModel.status == status)
        q = q.order_by(KCModel.created_at.desc()).limit(limit)
        return [{
            "id": c.id,
            "agent_name": c.agent_name,
            "content": c.content,
            "category": c.category,
            "confidence": c.confidence,
            "evidence_count": c.evidence_count,
            "status": c.status,
            "score": c.score,
            "validation_reason": c.validation_reason,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        } for c in q.all()]
    finally:
        db.close()


def update_status(
    candidate_id: str,
    status: str,
    reason: Optional[str] = None,
    score: Optional[float] = None,
) -> bool:
    """Update a candidate's status (approve/reject/promote)."""
    if status not in VALID_STATUSES:
        return False
    db = SessionLocal()
    try:
        cand = db.query(KCModel).filter(KCModel.id == candidate_id).first()
        if not cand:
            return False
        cand.status = status
        cand.updated_at = datetime.datetime.utcnow().isoformat()
        if reason is not None:
            cand.validation_reason = reason
        if score is not None:
            cand.score = score
        db.commit()
        return True
    finally:
        db.close()


def promote_to_knowledge(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Promote an approved candidate to KnowledgeEntry.

    Creates a KnowledgeEntry row and marks the candidate as PROMOTED.
    """
    from orcanium.app.core.db import KnowledgeEntry

    db = SessionLocal()
    try:
        cand = db.query(KCModel).filter(KCModel.id == candidate_id).first()
        if not cand or cand.status != "APPROVED":
            return None

        now = datetime.datetime.utcnow().isoformat()
        entry = KnowledgeEntry(
            id=uuid.uuid4().hex[:12],
            agent_name=cand.agent_name,
            content=cand.content,
            category=cand.category,
            source="promotion",
            knowledge_score=cand.score,
            frequency=1,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
        cand.status = "PROMOTED"
        cand.updated_at = now
        db.commit()

        logger.info("Candidate %s promoted to KnowledgeEntry for agent '%s'", candidate_id, cand.agent_name)
        return {"id": entry.id, "content": entry.content, "category": entry.category}
    finally:
        db.close()
