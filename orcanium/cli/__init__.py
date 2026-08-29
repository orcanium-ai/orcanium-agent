"""Orcanium CLI — Unified command-line interface for the Orcanium agent.

Provides subcommands for:
- orcanium chat           - Interactive chat with the agent
- orcanium gateway        - Manage gateway channels
- orcanium setup          - Interactive setup wizard
- orcanium status         - Show status of all components
- orcanium config         - Manage agent configuration
- orcanium cron           - Manage scheduled tasks
- orcanium model          - Manage models and providers
"""

import os
import sys

# Patch reference-agent imports BEFORE any other CLI module loads
from orcanium.cli.compat import *  # noqa: F401

__version__ = "0.1.1"
__release_date__ = "2026.8.01"


def _ensure_utf8():
    """Force UTF-8 stdout/stderr."""
    repaired = False
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
            if encoding == "utf8":
                continue
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                reconfigure(encoding="utf-8", errors="replace")
                repaired = True
                continue
            new_stream = open(
                stream.fileno(), "w", encoding="utf-8",
                errors="replace", buffering=1, closefd=False,
            )
            setattr(sys, stream_name, new_stream)
            repaired = True
        except (AttributeError, OSError, ValueError):
            pass
    if repaired:
        os.environ.setdefault("PYTHONUTF8", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


_ensure_utf8()
