import datetime
import json
import uuid
from typing import Any, Dict, Optional

from croniter import croniter
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from orcanium.app.core.db import ScheduledTask, get_db
from orcanium.app.domains.scheduler.executor import get_task_logs

router = APIRouter()


@router.get("/")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(ScheduledTask).all()
    res = []
    for t in tasks:
        res.append(
            {
                "id": t.id,
                "agent_name": t.agent_name,
                "cron_expr": t.cron_expr,
                "job_type": t.job_type,
                "payload": json.loads(t.payload) if t.payload else {},
                "next_run": t.next_run,
                "status": t.status,
            }
        )
    return res


@router.post("/create")
def create_task(
    agent_name: str,
    cron_expr: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    job_type: str = "run_agent",
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
):
    from orcanium.app.core.db import AgentState

    # Validate agent exists
    agent = db.query(AgentState).filter(AgentState.name == agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        if cron_expr:
            # Recurring task
            if not croniter.is_valid(cron_expr):
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            iter_cron = croniter(cron_expr, datetime.datetime.utcnow())
            next_run = iter_cron.get_next(datetime.datetime)
        elif scheduled_at:
            # One-time task
            next_run = datetime.datetime.fromisoformat(scheduled_at)
        else:
            raise HTTPException(
                status_code=400, detail="Either cron_expr or scheduled_at is required"
            )

        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            id=task_id,
            agent_name=agent_name,
            cron_expr=cron_expr or "",
            job_type=job_type,
            payload=json.dumps(payload or {}),
            next_run=next_run,
            status="active",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {"status": "success", "task_id": task.id, "next_run": task.next_run}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/toggle")
def toggle_task(task_id: str, status: str, db: Session = Depends(get_db)):
    # status can be active, paused
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    task.status = status
    db.commit()
    return {"status": "success", "task_id": task.id, "task_status": task.status}


@router.get("/{task_id}/logs")
def list_task_logs(
    task_id: str,
    limit: int = Query(20, description="Max log entries"),
    db: Session = Depends(get_db),
):
    """Get execution logs for a scheduled task."""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return get_task_logs(db, task_id, limit)


@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    db.delete(task)
    db.commit()
    return {"status": "success", "detail": f"Scheduled task {task_id} deleted"}
