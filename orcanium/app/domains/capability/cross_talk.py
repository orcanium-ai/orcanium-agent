"""Persistent, permission-gated communication between agent runtimes."""

from __future__ import annotations

import uuid
import datetime
from typing import Optional

from sqlalchemy.orm import Session

from orcanium.app.agent.agent_runtime import AgentRuntime
from orcanium.app.core.db import CrossTalkRequest
from orcanium.app.domains.capability.events import OrcaniumEvent, event_bus

MAX_HOPS = 3
MAX_CONTEXT_CHARS = 8_000
REQUEST_TTL = datetime.timedelta(minutes=10)
PENDING_PERMISSION = "pending_permission"
APPROVED = "approved"
QUEUED = "queued"
PROCESSING = "processing"
ANSWERED = "answered"
DELIVERED = "delivered"
FAILED = "failed"
EXPIRED = "expired"


def request_cross_talk(
    db: Session,
    source_agent_id: str,
    target_agent_id: str,
    request_text: str,
    *,
    source_session_id: Optional[str] = None,
    target_session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    context_summary: Optional[str] = None,
    hop: int = 0,
) -> CrossTalkRequest:
    if source_agent_id == target_agent_id:
        raise ValueError("An agent cannot send cross-talk to itself")
    if not request_text.strip():
        raise ValueError("request_text cannot be empty")
    if hop < 0 or hop >= MAX_HOPS:
        raise ValueError("cross-talk hop limit exceeded")
    bounded_context = (context_summary or "")[:MAX_CONTEXT_CHARS]
    request = CrossTalkRequest(
        id=uuid.uuid4().hex,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        source_session_id=source_session_id,
        target_session_id=target_session_id,
        turn_id=turn_id,
        request_text=request_text,
        context_summary=bounded_context or None,
        hop=hop,
        expires_at=datetime.datetime.utcnow() + REQUEST_TTL,
    )
    db.add(request)
    db.commit()
    event_bus.emit(OrcaniumEvent(
        category="APPROVAL", event_type="crosstalk_requested", agent_id=target_agent_id,
        session_id=target_session_id, payload={"request_id": request.id, "source_agent_id": source_agent_id,
                                                "approval_kind": "cross_talk"},
    ))
    return request


def resolve_cross_talk(db: Session, request_id: str, allowed: bool) -> CrossTalkRequest:
    request = db.query(CrossTalkRequest).filter(CrossTalkRequest.id == request_id).first()
    if request is None:
        raise ValueError(f"Cross-talk request not found: {request_id}")
    if request.status != PENDING_PERMISSION:
        raise ValueError(f"Cross-talk request is already {request.status}")
    if request.expires_at and request.expires_at < datetime.datetime.utcnow():
        request.status = "expired"
        db.commit()
        raise ValueError("Cross-talk request has expired")
    if not allowed:
        request.status = "denied"
        event_type = "crosstalk_denied"
    else:
        request.status = APPROVED
        event_type = "crosstalk_allowed"
    db.commit()
    event_bus.emit(OrcaniumEvent(category="APPROVAL", event_type=event_type,
                                 agent_id=request.target_agent_id,
                                 payload={"request_id": request.id}))
    return request


def queue_cross_talk(db: Session, request_id: str) -> CrossTalkRequest:
    request = db.get(CrossTalkRequest, request_id)
    if request is None:
        raise ValueError(f"Cross-talk request not found: {request_id}")
    if request.status != APPROVED:
        raise ValueError(f"Cross-talk request is not approved: {request.status}")
    request.status = QUEUED
    db.commit()
    return request


def execute_cross_talk(db: Session, request_id: str) -> CrossTalkRequest:
    request = db.query(CrossTalkRequest).filter(CrossTalkRequest.id == request_id).first()
    if request is None or request.status not in (APPROVED, QUEUED):
        raise ValueError("Cross-talk request must be approved or queued before execution")
    claimed = (db.query(CrossTalkRequest)
               .filter(CrossTalkRequest.id == request_id,
                       CrossTalkRequest.status.in_([APPROVED, QUEUED]))
               .update({CrossTalkRequest.status: PROCESSING}, synchronize_session=False))
    if claimed != 1:
        raise ValueError("Cross-talk request was already claimed")
    db.commit()
    request = db.get(CrossTalkRequest, request_id)
    db.commit()
    try:
        context = (request.context_summary or "")[:MAX_CONTEXT_CHARS]
        content = request.request_text
        if context:
            content = f"Context from {request.source_agent_id}:\n{context}\n\nRequest:\n{content}"
        response = AgentRuntime(request.target_agent_id, db).process_message(
            content, session_id=request.target_session_id,
            user_metadata={"cross_talk_request_id": request.id, "source_agent_id": request.source_agent_id},
        )
        request.result = response.get("final_response", str(response))
        request.status = ANSWERED
        event_type = "crosstalk_answered"
    except Exception as exc:
        request.error = str(exc)
        request.status = FAILED
        event_type = "crosstalk_failed"
    db.commit()
    event_bus.emit(OrcaniumEvent(
        category="AGENT", event_type=event_type, agent_id=request.source_agent_id,
        session_id=request.source_session_id,
        payload={"request_id": request.id, "target_agent_id": request.target_agent_id,
                 "result": request.result, "error": request.error},
    ))
    return request


def expire_cross_talk_requests(db: Session) -> int:
    """Expire unanswered requests; intended for the existing scheduler."""
    now = datetime.datetime.utcnow()
    count = (db.query(CrossTalkRequest)
             .filter(CrossTalkRequest.status.in_([PENDING_PERMISSION, "queued"]),
                     CrossTalkRequest.expires_at < now)
             .update({CrossTalkRequest.status: "expired"}, synchronize_session=False))
    db.commit()
    return count
