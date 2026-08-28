"""Background Lane — async, interruptible execution for non-urgent cognitive work.

All background tasks yield to foreground conversation. If a new user request
arrives, the background lane pauses until the foreground completes.

Background tasks:
    - Review Agent (memory, user, skills)
    - Title Generation
    - Knowledge Promotion
    - Memory Distiller
    - Curator
    - Analytics
"""

import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# How often background checks whether it should yield to foreground
_YIELD_CHECK_INTERVAL = 0.25  # seconds


class BackgroundLane:
    """Background execution lane.

    Runs non-urgent cognitive work on a managed thread pool.
    All tasks are interruptible — they yield to foreground when notified.

    Usage:
        lane = BackgroundLane()
        lane.enqueue("review", agent_name, fn)
        lane.notify_foreground_start()   # background pauses
        lane.notify_foreground_end()     # background resumes
    """

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="bg-lane",
        )
        self._tasks: Dict[str, Future] = {}
        self._tasks_lock = threading.Lock()
        # Event: when set, background tasks yield
        self._foreground_active = threading.Event()
        self._stopped = threading.Event()

    # ── Public API ──────────────────────────────────────────────

    def enqueue(
        self,
        task_type: str,
        agent_name: str,
        fn: Callable[[], Any],
        task_id: Optional[str] = None,
    ) -> str:
        """Enqueue a background task. Returns immediately with task_id.

        Args:
            task_type: One of "review", "title", "knowledge", "distill", "curate", "analytics"
            agent_name: Agent this task belongs to
            fn: Callable to execute in background
            task_id: Optional explicit task ID

        Returns:
            task_id for tracking/cancellation
        """
        tid = task_id or f"{task_type}-{agent_name}-{uuid.uuid4().hex[:8]}"

        future = self._executor.submit(self._run, tid, task_type, agent_name, fn)
        with self._tasks_lock:
            self._tasks[tid] = future

        logger.debug(f"BackgroundLane: enqueued {task_type} for {agent_name} (task={tid})")
        return tid

    def cancel(self, task_id: str) -> bool:
        """Cancel a running background task. Returns True if cancelled."""
        with self._tasks_lock:
            future = self._tasks.pop(task_id, None)
        if future and not future.done():
            cancelled = future.cancel()
            if cancelled:
                logger.debug(f"BackgroundLane: cancelled task {task_id}")
            return cancelled
        return False

    def cancel_all(self) -> int:
        """Cancel all running background tasks. Returns count cancelled."""
        count = 0
        with self._tasks_lock:
            for tid, future in list(self._tasks.items()):
                if not future.done():
                    future.cancel()
                    count += 1
            self._tasks.clear()
        if count:
            logger.debug(f"BackgroundLane: cancelled {count} tasks")
        return count

    def active_count(self) -> int:
        """Number of currently active background tasks."""
        with self._tasks_lock:
            return len(self._tasks)

    # ── Foreground coordination ────────────────────────────────

    def notify_foreground_start(self) -> None:
        """Signal background tasks to yield — foreground conversation is active.

        Called BEFORE processing a new user request.
        Background tasks check this flag and pause between operations.
        """
        self._foreground_active.set()
        logger.debug("BackgroundLane: foreground START")

    def notify_foreground_end(self) -> None:
        """Signal that foreground conversation has completed.

        Called AFTER the response has been delivered.
        Background tasks resume on their next yield check.
        """
        self._foreground_active.clear()
        logger.debug("BackgroundLane: foreground END")

    @property
    def is_foreground_active(self) -> bool:
        """Check if foreground conversation is currently active."""
        return self._foreground_active.is_set()

    # ── Lifecycle ───────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the background lane. Blocks until running tasks finish."""
        self._stopped.set()
        self._executor.shutdown(wait=wait)
        logger.info("BackgroundLane: shut down")

    # ── Internal ────────────────────────────────────────────────

    def _run(self, task_id: str, task_type: str, agent_name: str, fn: Callable) -> None:
        """Run a background task with foreground-yield support."""
        try:
            # Yield if foreground is active before starting
            self._yield_if_needed()

            if self._stopped.is_set():
                return

            result = fn()

            logger.debug(
                f"BackgroundLane: completed {task_type} for {agent_name} (task={task_id})"
            )
            return result

        except Exception as e:
            logger.warning(
                f"BackgroundLane: {task_type} failed for {agent_name}: {e}"
            )
        finally:
            with self._tasks_lock:
                self._tasks.pop(task_id, None)

    def _yield_if_needed(self) -> None:
        """Yield execution to foreground if foreground is active.

        Polls the foreground_active event at intervals, sleeping between checks.
        Returns when foreground clears or the lane is stopped.
        """
        run_count = 0
        while self._foreground_active.is_set() and not self._stopped.is_set():
            run_count += 1
            if run_count == 1:
                logger.debug("BackgroundLane: yielding to foreground...")
            time.sleep(_YIELD_CHECK_INTERVAL)

        if run_count > 0:
            logger.debug(f"BackgroundLane: resuming after {run_count * _YIELD_CHECK_INTERVAL:.1f}s foreground pause")
