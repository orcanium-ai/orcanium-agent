"""Per-agent/session LLM request scheduler.

The scheduler serializes chat-generation work for each agent session while
leaving non-LLM runtime work free to run normally.
"""

import itertools
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 180.0


class CancelledRequest(Exception):
    """Raised when a queued request is cancelled before execution."""


@dataclass
class CancellationToken:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _cancelled: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled


@dataclass(order=True)
class _ScheduledRequest:
    priority: int
    sequence: int
    fn: Callable[[], Any] = field(compare=False)
    token: CancellationToken = field(compare=False)
    done: threading.Event = field(default_factory=threading.Event, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[BaseException] = field(default=None, compare=False)


class _SessionQueue:
    def __init__(self, key: str):
        self.key = key
        self.queue: "queue.PriorityQueue[_ScheduledRequest]" = queue.PriorityQueue()
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name=f"agent-llm-scheduler-{key}",
        )
        self.thread.start()

    def submit(self, request: _ScheduledRequest) -> None:
        self.queue.put(request)

    def _worker(self) -> None:
        while True:
            request = self.queue.get()
            try:
                if request.token.cancelled:
                    request.error = CancelledRequest(
                        f"LLM request {request.token.request_id} was cancelled"
                    )
                    continue
                request.result = request.fn()
            except BaseException as e:
                request.error = e
            finally:
                request.done.set()
                self.queue.task_done()


class AgentRequestScheduler:
    """Serializes LLM generation per agent/session key."""

    def __init__(self):
        self._queues: Dict[str, _SessionQueue] = {}
        self._lock = threading.Lock()
        self._sequence = itertools.count()

    def run(
        self,
        agent_id: str,
        session_id: Optional[str],
        purpose: str,
        fn: Callable[[], Any],
        timeout: float = DEFAULT_LLM_TIMEOUT_SECONDS,
        token: Optional[CancellationToken] = None,
    ) -> Any:
        key = self._key(agent_id, session_id)
        request = _ScheduledRequest(
            priority=self._priority(purpose),
            sequence=next(self._sequence),
            fn=fn,
            token=token or CancellationToken(),
        )

        queue_ref = self._get_queue(key)
        queued_at = time.time()
        queue_ref.submit(request)

        if not request.done.wait(timeout=timeout):
            request.token.cancel()
            raise TimeoutError(
                f"LLM request timed out after {timeout:.0f}s "
                f"(agent={agent_id}, session={session_id or ''}, purpose={purpose})"
            )
        if request.error:
            raise request.error

        wait_ms = (time.time() - queued_at) * 1000
        if wait_ms > 1000:
            logger.info(
                "LLM request completed after queue wait/run %.0fms "
                "(agent=%s session=%s purpose=%s)",
                wait_ms,
                agent_id,
                session_id or "",
                purpose,
            )
        return request.result

    def cancel(self, token: CancellationToken) -> None:
        token.cancel()

    def _get_queue(self, key: str) -> _SessionQueue:
        with self._lock:
            queue_ref = self._queues.get(key)
            if queue_ref is None:
                queue_ref = _SessionQueue(key)
                self._queues[key] = queue_ref
            return queue_ref

    @staticmethod
    def _key(agent_id: str, session_id: Optional[str]) -> str:
        return agent_id

    @staticmethod
    def _priority(purpose: str) -> int:
        priorities = {
            "PRIMARY_RESPONSE": 10,
            "GATEWAY_DELIVERY": 20,
            "TIMELINE": 30,
            "MEMORY_REVIEW": 40,
            "SKILL_REVIEW": 40,
            "KNOWLEDGE_REVIEW": 40,
            "TITLE_GENERATION": 50,
            "CURATOR": 60,
            "DISTILLATION": 70,
        }
        return priorities.get(purpose, 90)


agent_request_scheduler = AgentRequestScheduler()
