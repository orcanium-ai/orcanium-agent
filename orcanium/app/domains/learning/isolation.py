"""Reviewer isolation — thread-local tool whitelist for background review threads.

Ensures background review agents operate only through approved interfaces
(memory_manage, skill_manage) and cannot access filesystem, network, or arbitrary tools.
"""

import logging
import threading
from contextvars import ContextVar
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Thread-local tool whitelist
_tool_whitelist: ContextVar[Optional[Set[str]]] = ContextVar(
    "_tool_whitelist", default=None
)


def set_thread_tool_whitelist(allowed_tools: Set[str]) -> None:
    """Set the allowed tool set for the current thread."""
    _tool_whitelist.set(allowed_tools)


def clear_thread_tool_whitelist() -> None:
    """Clear the tool whitelist for the current thread."""
    _tool_whitelist.set(None)


def is_tool_allowed(tool_name: str) -> bool:
    """Check if a tool is allowed in the current thread context."""
    whitelist = _tool_whitelist.get()
    if whitelist is None:
        return True  # No whitelist = all tools allowed (main thread)
    return tool_name in whitelist


def get_allowed_tools() -> Optional[Set[str]]:
    """Get the current thread's allowed tools, or None if unrestricted."""
    return _tool_whitelist.get()


# Allowed toolsets for background review
REVIEW_ALLOWED_TOOLS: Set[str] = {
    "memory_add",
    "memory_remove",
    "memory_replace",
    "memory_read",
    "skill_manage",
}


class ReviewIsolation:
    """Context manager for review thread isolation."""

    def __enter__(self):
        set_thread_tool_whitelist(REVIEW_ALLOWED_TOOLS)
        return self

    def __exit__(self, *args):
        clear_thread_tool_whitelist()
