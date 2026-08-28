"""KnowledgeEngine — retrieves promoted knowledge from KnowledgeEntry table.

SQLite is the canonical store. Markdown is a human-editable mirror.
Runtime always reads SQLite — never parses Markdown during inference.

V2 will replace the keyword matcher with hybrid keyword + embedding retrieval.
The ``retrieve()`` interface remains identical.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from orcanium.app.core.db import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """Retrieves promoted knowledge by keyword matching on KnowledgeEntry.

    Single entry point for the Cognitive Engine. V2 only changes the
    internals of ``retrieve()`` — the interface stays the same.
    """

    @staticmethod
    def retrieve(
        db: Session,
        query: str,
        agent_name: Optional[str] = None,
        top_n: int = 5,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Retrieve promoted knowledge entries by keyword containment.

        Args:
            db: SQLAlchemy session.
            query: Search query string.
            agent_name: If provided, scope search to a single agent.
            top_n: Maximum results to return.

        Returns:
            List of dicts with keys: id, agent_name, content, category, score.
        """
        q = db.query(KnowledgeEntry)
        if agent_name:
            q = q.filter(KnowledgeEntry.agent_name == agent_name)

        entries = q.all()
        if not entries:
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for entry in entries:
            content_lower = entry.content.lower()
            matches = sum(1 for w in query_words if w in content_lower)
            if matches > 0:
                scored.append((matches, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [e for _, e in scored[:top_n]]

        results = []
        for e in top:
            results.append({
                "id": e.id,
                "agent_name": e.agent_name,
                "content": e.content,
                "category": e.category,
                "score": e.knowledge_score,
                "source": e.source,
                "created_at": e.created_at,
            })

        return results
