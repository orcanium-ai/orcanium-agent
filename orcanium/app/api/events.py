"""Events API — Event History + SSE streaming.

Provides:
    GET  /events/history  — Paginated event history from TimelineStore
    GET  /events/stream   — Real-time SSE stream of new events
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.capability.timeline.timeline_store import TimelineStore

logger = logging.getLogger(__name__)

router = APIRouter()
store = TimelineStore()


@router.get("/events/history")
def get_event_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    agent: Optional[str] = Query(None, alias="agent_id"),
    session: Optional[str] = Query(None, alias="session_id"),
    workflow: Optional[str] = Query(None, alias="workflow_id"),
):
    """Get paginated event history from the timeline store."""
    results = store.query(
        category=category,
        agent_id=agent,
        session_id=session,
        workflow_id=workflow,
        limit=limit,
        offset=offset,
    )
    total = store.count()
    return {
        "events": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/events/stream")
async def stream_events(request: Request):
    """SSE endpoint — streams new events in real-time.

    Uses Server-Sent Events (text/event-stream).
    No WebSocket needed for Orcanium's server→client event delivery.
    """

    async def event_generator():
        last_index = len(event_bus._history)
        while True:
            if await request.is_disconnected():
                break

            # Check for new events since last check
            current_len = len(event_bus._history)
            if current_len > last_index:
                new_events = event_bus._history[last_index:]
                for event in new_events:
                    data = json.dumps(event.to_dict())
                    yield f"data: {data}\n\n"
                last_index = current_len

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
