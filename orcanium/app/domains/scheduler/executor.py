"""Task execution with logging and result delivery.

Provides the execution layer for scheduled tasks — runs the job,
logs the result, and optionally delivers output via channel.
"""

import datetime
import json
import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from orcanium.app.agent.agent_runtime import AgentRuntime
from orcanium.app.core.db import (
    AgentState,
    ScheduledTask,
    SessionLocal,
    TaskExecutionLog,
)

logger = logging.getLogger(__name__)


def execute_task(task: ScheduledTask, db: Session) -> Dict[str, Any]:
    """Execute a scheduled task and log the result.

    Returns dict with {status, output, error}.
    """
    log_entry = TaskExecutionLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        started_at=datetime.datetime.utcnow(),
        status="running",
    )
    db.add(log_entry)
    db.commit()

    output = ""
    error = ""

    try:
        agent = db.query(AgentState).filter(AgentState.name == task.agent_name).first()
        if not agent:
            raise ValueError(f"Agent '{task.agent_name}' not found")

        payload = {}
        if task.payload:
            try:
                payload = json.loads(task.payload)
            except Exception:
                pass

        if task.job_type == "run_agent":
            runtime = AgentRuntime(agent.name, db)
            prompt = payload.get(
                "prompt", "Hello! This is an automated scheduled task running."
            )
            session_id = payload.get("session_id")
            res = runtime.process_message(user_content=prompt, session_id=session_id)
            output = res.get("agent_response", "")[:500]

        elif task.job_type == "sync_knowledge":
            from orcanium.app.domains.knowledge.promotion import curator_tick
            count = curator_tick(agent_name=task.agent_name)
            output = f"Knowledge curator tick: {count} candidates promoted."
            logger.info("Knowledge sync for %s: %d promoted", task.agent_name, count)

        elif task.job_type == "script":
            # Run a shell script from the payload
            script = payload.get("script", "")
            if script:
                import subprocess

                result = subprocess.run(
                    script, shell=True, capture_output=True, text=True, timeout=60
                )
                output = result.stdout[:500]
                if result.returncode != 0:
                    error = result.stderr[:500]

        else:
            error = f"Unknown job type: {task.job_type}"

        status = "failed" if error else "success"

    except Exception as e:
        error = str(e)
        status = "failed"
        logger.error(f"Task {task.id} execution failed: {e}")

    # Update log entry
    log_entry.finished_at = datetime.datetime.utcnow()
    log_entry.status = status
    log_entry.output = output[:1000] if output else None
    log_entry.error = error[:1000] if error else None
    db.commit()

    # Deliver result if delivery is configured
    _deliver_result(task, output, error, status)

    return {"status": status, "output": output, "error": error}


def _deliver_result(task: ScheduledTask, output: str, error: str, status: str):
    """Deliver task result via gateway if configured."""
    payload = {}
    if task.payload:
        try:
            payload = json.loads(task.payload)
        except Exception:
            pass

    deliver_to = payload.get("deliver_to")
    if not deliver_to:
        return

    try:
        from orcanium.app.domains.channel.manager import channel_runner

        message = (
            f"📋 Task '{task.id[:8]}...' completed\n"
            f"Status: {status}\n"
            f"Agent: {task.agent_name}\n"
        )
        if output:
            message += f"\nOutput: {output[:200]}"
        if error:
            message += f"\nError: {error[:200]}"

        # Deliver to each configured target
        for target in deliver_to if isinstance(deliver_to, list) else [deliver_to]:
            if isinstance(target, dict):
                channel_id = target.get("channel_id")
                chat_id = target.get("chat_id")
                if channel_id and chat_id:
                    adapter = channel_runner._adapters.get(channel_id)
                    if adapter:
                        adapter.send_message(chat_id, message)
    except Exception as e:
        logger.warning(f"Task result delivery failed: {e}")


def get_task_logs(db: Session, task_id: str, limit: int = 20) -> list:
    """Return execution logs for a task."""
    logs = (
        db.query(TaskExecutionLog)
        .filter(TaskExecutionLog.task_id == task_id)
        .order_by(TaskExecutionLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "task_id": log.task_id,
            "started_at": str(log.started_at) if log.started_at else None,
            "finished_at": str(log.finished_at) if log.finished_at else None,
            "status": log.status,
            "output": log.output,
            "error": log.error,
        }
        for log in logs
    ]
