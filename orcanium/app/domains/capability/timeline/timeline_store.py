"""TimelineStore — SQLite-backed persistent store for recent event evidence.

This is NOT a permanent audit log.
TimelineStore holds recent operational evidence (default 5000 events).

Schema:
    timeline_events table in the main SQLite database (``state.db``).
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from orcanium.app.core.db import SessionLocal, TimelineEvent
from orcanium.app.domains.capability.events import OrcaniumEvent

logger = logging.getLogger(__name__)

_DEFAULT_MAX_EVENTS = 5000


class TimelineStore:
    """Persistent, SQLite-backed store for timeline events.

    Usage:
        store = TimelineStore()
        store.append(event)         # Called by TimelineConsumer
        events = store.query(...)   # Called by Event History API
    """

    def __init__(self, max_events: int = _DEFAULT_MAX_EVENTS):
        self._max_events = max_events

    def append(self, event: OrcaniumEvent) -> None:
        """Persist a single event bus emission to the timeline table."""
        db = SessionLocal()
        try:
            row = TimelineEvent(
                timestamp=event.timestamp or "",
                category=event.category,
                event_name=event.event_type,
                agent_id=event.agent_id,
                session_id=event.session_id or (event.payload.get("session_id") if isinstance(event.payload, dict) else None),
                workflow_id=event.workflow_id,
                parent_event_id=event.parent_event_id,
                payload_json=json.dumps(event.payload) if event.payload else "{}",
            )
            db.add(row)
            db.commit()

            # Enforce retention cap — remove oldest if exceeded
            count = db.query(TimelineEvent).count()
            if count > self._max_events:
                excess = count - self._max_events
                oldest = (
                    db.query(TimelineEvent)
                    .order_by(TimelineEvent.id.asc())
                    .limit(excess)
                    .all()
                )
                for old in oldest:
                    db.delete(old)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"TimelineStore append failed: {e}")
        finally:
            db.close()

    def query(
        self,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query timeline events with optional filters.

        Used by the Event History API (``GET /api/events/history``).
        """
        db = SessionLocal()
        try:
            q = db.query(TimelineEvent)
            if category:
                q = q.filter(TimelineEvent.category == category)
            if agent_id:
                q = q.filter(TimelineEvent.agent_id == agent_id)
            if session_id:
                q = q.filter(TimelineEvent.session_id == session_id)
            if workflow_id:
                q = q.filter(TimelineEvent.workflow_id == workflow_id)

            rows = (
                q.order_by(desc(TimelineEvent.id))
                .limit(limit)
                .offset(offset)
                .all()
            )

            results = []
            for row in rows:
                payload = {}
                if row.payload_json:
                    try:
                        payload = json.loads(row.payload_json)
                    except (json.JSONDecodeError, TypeError):
                        payload = {"raw": row.payload_json}

                results.append({
                    "id": row.id,
                    "timestamp": row.timestamp,
                    "category": row.category,
                    "event_name": row.event_name,
                    "agent_id": row.agent_id,
                    "session_id": row.session_id,
                    "workflow_id": row.workflow_id,
                    "parent_event_id": row.parent_event_id,
                    "payload": payload,
                })
            return results
        finally:
            db.close()

    def count(self) -> int:
        """Total events in the timeline."""
        db = SessionLocal()
        try:
            return db.query(TimelineEvent).count()
        finally:
            db.close()

    def clear(self) -> None:
        """Clear all events (admin operation)."""
        db = SessionLocal()
        try:
            db.query(TimelineEvent).delete()
            db.commit()
        finally:
            db.close()
