"""Deliver completed cross-talk answers into the source session."""

from orcanium.app.core.db import Message, SessionLocal
from orcanium.app.domains.capability.events import CROSSTALK_ANSWERED, OrcaniumEvent


def handle_event(event: OrcaniumEvent) -> None:
    if event.event_type != CROSSTALK_ANSWERED or not event.session_id:
        return
    db = SessionLocal()
    try:
        request_id = event.payload.get("request_id", "")
        content = event.payload.get("result") or event.payload.get("error") or "Cross-talk request failed."
        db.add(Message(id=f"crosstalk-{request_id}", session_id=event.session_id,
                       sender="agent", content=f"[Cross-talk {request_id}]\n{content}"))
        db.commit()
        from orcanium.app.domains.capability.cross_talk import DELIVERED
        from orcanium.app.core.db import CrossTalkRequest
        request = db.get(CrossTalkRequest, request_id)
        if request and request.status == "answered":
            request.status = DELIVERED
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
