import datetime
import json
import logging
import threading
import time

from croniter import croniter
from orcanium.app.core.db import ScheduledTask, SessionLocal
from orcanium.app.domains.scheduler.executor import execute_task
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Starts background scheduling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="orcanium-scheduler"
        )
        self._thread.start()
        logger.info("Background Scheduler started successfully.")

    def stop(self):
        """Stops background scheduling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Background Scheduler stopped.")

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_and_run_tasks()
            except Exception as e:
                logger.error(f"Error in scheduler job check cycle: {e}")
            # Wait 10 seconds before next check
            self._stop_event.wait(10.0)

    def check_and_run_tasks(self):
        db: Session = SessionLocal()
        try:
            now = datetime.datetime.utcnow()
            # Fetch active tasks whose next_run is due
            tasks = (
                db.query(ScheduledTask)
                .filter(ScheduledTask.status == "active", ScheduledTask.next_run <= now)
                .all()
            )

            for task in tasks:
                logger.info(
                    f"Triggering scheduled task {task.id} for agent {task.agent_name} ({task.job_type})"
                )

                try:
                    execute_task(task, db)

                    if task.cron_expr:
                        # Recurring — compute next run
                        iter_cron = croniter(task.cron_expr, now)
                        task.next_run = iter_cron.get_next(datetime.datetime)
                    else:
                        # One-time — mark as completed
                        task.status = "completed"

                except Exception as ex:
                    logger.error(f"Failed executing scheduled task {task.id}: {ex}")
                    task.status = "failed"

            db.commit()
        finally:
            db.close()


scheduler_service = BackgroundScheduler()
