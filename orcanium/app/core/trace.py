"""Runtime trace instrumentation — temporary DEBUG logging for hang investigation.

Usage:
    from orcanium.app.core.trace import trace, trace_id

    # At start of function:
    _trace_id = trace_id()
    trace("ENTER", "function_name", request_id=_trace_id)
    try:
        ...
    finally:
        trace("EXIT", "function_name", request_id=_trace_id)

Output format:
    [TRACE] [request_id] [thread_name] [purpose] ENTER function_name
    [TRACE] [request_id] [thread_name] [purpose] EXIT function_name elapsed=1234ms
"""

import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)

# Enable trace logging by setting log level to DEBUG on this logger
# The root logger must be at DEBUG level for traces to appear


def trace_id() -> str:
    """Generate a short unique request ID."""
    return str(uuid.uuid4())[:8]


def _thread_name() -> str:
    """Get current thread name."""
    return threading.current_thread().name or "unknown"


def trace(
    event: str,
    function: str,
    request_id: str = "",
    purpose: str = "",
    elapsed_ms: float = 0.0,
    extra: str = "",
) -> None:
    """Emit a structured trace log line at DEBUG level.

    Args:
        event: "ENTER" or "EXIT"
        function: Function or operation name
        request_id: Correlation ID
        purpose: PRIMARY_RESPONSE, TITLE_GENERATION, MEMORY_REVIEW, etc.
        elapsed_ms: Duration since ENTER (for EXIT events)
        extra: Additional context (HTTP status, etc.)
    """
    tid = request_id or trace_id()
    thread = _thread_name()
    parts = [f"[TRACE] [{tid}] [{thread}]"]
    if purpose:
        parts.append(f"[{purpose}]")
    parts.append(event)
    parts.append(function)
    if elapsed_ms:
        parts.append(f"elapsed={int(elapsed_ms)}ms")
    if extra:
        parts.append(extra)
    logger.debug(" ".join(parts))
