"""LaneManager — singleton that coordinates foreground and background execution lanes.

Usage:
    from orcanium.app.domains.execution import LaneManager

    mgr = LaneManager.get_instance()

    # Foreground: wraps user request processing
    with mgr.foreground():
        response = conversation_loop.execute(...)

    # Background: enqueue async work after response delivered
    mgr.background.enqueue("review", agent_name, review_fn)
"""

import logging
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional

from orcanium.app.domains.execution.background_lane import BackgroundLane

logger = logging.getLogger(__name__)


class LaneManager:
    """Singleton that manages foreground/background execution lanes.

    - Foreground lane: Conversation Loop, tools, streaming (always wins)
    - Background lane: Review, Title, Distiller, Curator, Analytics (never blocks user)

    Background tasks are automatically paused when foreground is active
    and resumed after the response is delivered.
    """

    _instance: Optional["LaneManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        if LaneManager._instance is not None:
            raise RuntimeError("Use LaneManager.get_instance() instead")
        self.background = BackgroundLane(max_workers=2)
        self._foreground_depth = 0
        self._depth_lock = threading.Lock()
        logger.info("LaneManager: initialized (foreground + background lanes)")

    @classmethod
    def get_instance(cls) -> "LaneManager":
        """Get or create the singleton LaneManager."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Foreground context ──────────────────────────────────────

    @contextmanager
    def foreground(self) -> Generator[None, None, None]:
        """Context manager for foreground execution.

        - Signals background to yield before foreground starts
        - Blocks ALL background activity during foreground execution
        - Resumes background after foreground completes

        Usage:
            with LaneManager.get_instance().foreground():
                response = process_user_message(...)
        """
        self._enter_foreground()
        try:
            yield
        finally:
            self._exit_foreground()

    def _enter_foreground(self) -> None:
        """Enter foreground mode — background yields."""
        with self._depth_lock:
            was_idle = self._foreground_depth == 0
            self._foreground_depth += 1
        if was_idle:
            self.background.notify_foreground_start()
        logger.debug(
            f"LaneManager: foreground depth={self._foreground_depth}"
        )

    def _exit_foreground(self) -> None:
        """Exit foreground mode — background may resume."""
        with self._depth_lock:
            self._foreground_depth -= 1
            now_idle = self._foreground_depth == 0
        if now_idle:
            self.background.notify_foreground_end()
        logger.debug(
            f"LaneManager: foreground depth={self._foreground_depth}"
        )

    @property
    def is_foreground_active(self) -> bool:
        """Check if any foreground conversation is running."""
        with self._depth_lock:
            return self._foreground_depth > 0

    # ── Background convenience ──────────────────────────────────

    def enqueue(
        self,
        task_type: str,
        agent_name: str,
        fn: Callable[[], Any],
        task_id: Optional[str] = None,
    ) -> str:
        """Enqueue a background task. Returns immediately.

        If foreground is active, the task waits until foreground completes
        before starting (the yield-check in BackgroundLane handles this).
        """
        return self.background.enqueue(
            task_type=task_type,
            agent_name=agent_name,
            fn=fn,
            task_id=task_id,
        )

    # ── Lifecycle ───────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        """Shut down both lanes."""
        self.background.shutdown(wait=wait)
        logger.info("LaneManager: shut down")

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.shutdown(wait=False)
                cls._instance = None
