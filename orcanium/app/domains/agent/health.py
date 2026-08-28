"""Agent health monitoring and status tracking.

Provides real runtime health status instead of hardcoded "healthy".
"""

import datetime
import logging
import threading
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from orcanium.app.core.db import AgentState, SessionLocal

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL_S = 30


class AgentHealthStatus:
    """Tracks agent runtime health with timestamps and error counts."""

    def __init__(self):
        self._lock = threading.Lock()
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def record_activity(self, agent_name: str):
        """Record that an agent performed an activity."""
        with self._lock:
            now = datetime.datetime.utcnow()
            if agent_name not in self._statuses:
                self._statuses[agent_name] = {
                    "status": "online",
                    "last_seen": now,
                    "last_activity": now,
                    "last_task": None,
                    "error_count": 0,
                    "created_at": now,
                }
            else:
                self._statuses[agent_name]["last_activity"] = now
                self._statuses[agent_name]["last_seen"] = now
                self._statuses[agent_name]["status"] = "busy"

    def record_error(self, agent_name: str, error: str = ""):
        """Record an error for an agent."""
        with self._lock:
            now = datetime.datetime.utcnow()
            if agent_name not in self._statuses:
                self._statuses[agent_name] = {
                    "status": "error",
                    "last_seen": now,
                    "last_activity": now,
                    "last_task": None,
                    "error_count": 1,
                    "last_error": error,
                    "created_at": now,
                }
            else:
                self._statuses[agent_name]["error_count"] += 1
                self._statuses[agent_name]["last_error"] = error
                self._statuses[agent_name]["status"] = "error"
                self._statuses[agent_name]["last_seen"] = now

    def get_health(self, agent_name: str) -> Dict[str, Any]:
        """Return the current health status for an agent."""
        with self._lock:
            entry = self._statuses.get(agent_name)
            if not entry:
                db = SessionLocal()
                try:
                    agent = (
                        db.query(AgentState)
                        .filter(AgentState.name == agent_name)
                        .first()
                    )
                    if agent:
                        return {
                            "status": "unknown",
                            "last_seen": None,
                            "last_activity": None,
                            "error_count": 0,
                            "db_status": agent.status,
                        }
                finally:
                    db.close()
                return {
                    "status": "offline",
                    "last_seen": None,
                    "last_activity": None,
                    "error_count": 0,
                }

            return dict(entry)

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Return health status for all tracked agents."""
        with self._lock:
            return {k: dict(v) for k, v in self._statuses.items()}

    def mark_offline(self, agent_name: str):
        """Mark an agent as offline."""
        with self._lock:
            if agent_name in self._statuses:
                self._statuses[agent_name]["status"] = "offline"
                self._statuses[agent_name]["last_seen"] = datetime.datetime.utcnow()

    def start_heartbeat(self):
        """Start background heartbeat checker."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="agent-heartbeat"
        )
        self._thread.start()

    def stop_heartbeat(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _heartbeat_loop(self):
        """Periodically check agent status and mark stale agents as offline."""
        while not self._stop_event.is_set():
            try:
                self._check_stale_agents()
            except Exception as e:
                logger.error(f"Heartbeat check failed: {e}")
            self._stop_event.wait(_HEARTBEAT_INTERVAL_S)

    def _check_stale_agents(self):
        """Mark agents as offline if they haven't been seen recently."""
        now = datetime.datetime.utcnow()
        stale_threshold = datetime.timedelta(minutes=5)
        with self._lock:
            for agent_name, entry in self._statuses.items():
                if entry.get("last_seen"):
                    elapsed = now - entry["last_seen"]
                    if elapsed > stale_threshold and entry["status"] not in (
                        "offline",
                        "error",
                    ):
                        entry["status"] = "idle"
                if entry.get("last_activity"):
                    elapsed = now - entry["last_activity"]
                    if elapsed > stale_threshold * 2:
                        entry["status"] = "offline"


# Global singleton
agent_health = AgentHealthStatus()
