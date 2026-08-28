import asyncio
import datetime
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from orcanium.app.agent.agent_runtime import AgentRuntime
from orcanium.app.core.db import AgentState, Message, get_db
from orcanium.app.core.db import Session as DbSession
from orcanium.app.domains.session.search import search_messages, search_sessions

router = APIRouter()


@router.get("/")
def list_sessions(
    agent_name: Optional[str] = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    """List sessions, excluding archived by default."""
    from sqlalchemy.orm import joinedload

    query = db.query(DbSession).options(joinedload(DbSession.messages))
    if agent_name:
        query = query.filter(DbSession.agent_name == agent_name)
    if not include_archived:
        query = query.filter(DbSession.archived_at.is_(None))
    sessions = query.order_by(DbSession.updated_at.desc()).all()

    result = []
    for s in sessions:
        message_count = len(s.messages) if s.messages else 0
        result.append(
            {
                "id": s.id,
                "agent_name": s.agent_name,
                "title": s.title,
                "source": s.source,
                "message_count": message_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "archived_at": s.archived_at.isoformat() if s.archived_at else None,
            }
        )
    return result


@router.get("/{session_id}")
def get_session_details(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    return messages


@router.post("/{session_id}/chat")
async def chat_with_agent(
    session_id: str, agent_name: str, message: str, db: Session = Depends(get_db)
):
    runtime = AgentRuntime(agent_name, db)

    async def event_generator():
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def on_delta(text):
            if text is None:
                queue.put_nowait({"type": "segment_break"})
            else:
                queue.put_nowait({"type": "delta", "text": text})

        def on_tool(name, action, **kw):
            event = {"type": "tool", "name": name, "action": action}
            event.update(kw)
            queue.put_nowait(event)

        future = loop.run_in_executor(
            None,
            lambda: runtime.process_message(
                user_content=message, session_id=session_id,
                delta_callback=on_delta, tool_callback=on_tool,
            ),
        )

        while True:
            if future.done() and queue.empty():
                try:
                    result = future.result()
                    yield json.dumps({"type": "done", **result}) + "\n"
                except Exception as e:
                    yield json.dumps({"type": "error", "detail": str(e)}) + "\n"
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield json.dumps(event) + "\n"
            except asyncio.TimeoutError:
                continue

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/archive")
def archive_session(session_id: str, db: Session = Depends(get_db)):
    """Soft-delete a session — hides it from default list queries."""
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    sess.archived_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "success", "detail": "Session archived"}


@router.post("/{session_id}/restore")
def restore_session(session_id: str, db: Session = Depends(get_db)):
    """Restore a previously archived session."""
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    sess.archived_at = None
    db.commit()
    return {"status": "success", "detail": "Session restored"}


@router.get("/search/messages")
def search_session_messages(
    q: str = Query(..., description="Search query"),
    agent_name: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(50, description="Max results"),
    db: Session = Depends(get_db),
):
    """Search messages across all sessions using full-text search."""
    return search_messages(db, query=q, agent_name=agent_name, limit=limit)


@router.get("/search/sessions")
def search_session_titles(
    q: str = Query(..., description="Search query"),
    agent_name: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(20, description="Max results"),
    db: Session = Depends(get_db),
):
    """Search sessions by title using full-text search."""
    return search_sessions(db, query=q, agent_name=agent_name, limit=limit)


@router.post("/create")
def create_session(
    agent_name: str,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new chat session for an agent."""
    # Validate agent exists
    agent = db.query(AgentState).filter(AgentState.name == agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    session_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    sess = DbSession(
        id=session_id,
        agent_name=agent_name,
        title=title or f"Chat with {agent_name}",
        created_at=now,
        updated_at=now,
        source="chat",
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return {
        "status": "success",
        "session": {
            "id": sess.id,
            "agent_name": sess.agent_name,
            "title": sess.title,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
            "source": sess.source,
        },
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(sess)
    db.commit()
    return {"status": "success", "detail": "Session deleted completely"}
