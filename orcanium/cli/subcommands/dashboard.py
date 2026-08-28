"""``orcanium dashboard`` subcommand parser.

Extracted verbatim from ``orcanium.cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

import argparse
from typing import Callable


def build_dashboard_parser(subparsers, *, cmd_dashboard: Callable) -> None:
    """Attach the local dashboard command."""
    # =========================================================================
    # dashboard command
    # =========================================================================
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Start the web UI dashboard",
        description="Launch the orcanium Agent web dashboard for managing config, API keys, and sessions",
    )
    dashboard_parser.add_argument(
        "--port", type=int, default=9119, help="Port (default 9119, 0 for auto-assign by OS)"
    )
    dashboard_parser.add_argument(
        "--host", default="127.0.0.1", help="Host (default 127.0.0.1)"
    )
    dashboard_parser.add_argument(
        "--no-open", action="store_true", help="Don't open browser automatically"
    )
    dashboard_parser.add_argument(
        "--insecure",
        action="store_true",
        help="Allow binding to non-localhost (DANGEROUS: exposes API keys on the network)",
    )
    dashboard_parser.add_argument(
        "--skip-build",
        action="store_true",
        help=(
            "Skip the web UI build step and serve the existing dist directly. "
            "Useful for non-interactive contexts (Windows Scheduled Tasks, CI) "
            "where npm may not be available. Pre-build with: cd web && npm run build"
        ),
    )
    dashboard_parser.add_argument(
        "--isolated",
        action="store_true",
        help=(
            "When launched from a named profile (e.g. `worker dashboard`), run "
            "a dedicated dashboard server scoped to that profile instead of "
            "routing to the machine dashboard. Default behavior is unified: "
            "profile launches attach to (or start) ONE machine-level dashboard "
            "and preselect the profile in the UI's profile switcher."
        ),
    )
    # Internal flag set by the unified-launch re-exec (cmd_dashboard) to
    # preselect the launching profile in the SPA switcher. Hidden from
    # --help: users get this behavior automatically via `<profile> dashboard`.
    dashboard_parser.add_argument(
        "--open-profile",
        dest="open_profile",
        default="",
        help=argparse.SUPPRESS,
    )
    # Lifecycle flags — mutually exclusive with each other and with the
    # start-a-server flags above (if both are passed, --stop / --status win
    # because they exit before the server is started).  The dashboard has
    # no service manager and no PID file, so these scan the process table
    # for `orcanium dashboard` cmdlines and SIGTERM them directly — the same
    # path `orcanium update` uses to clean up stale dashboards.
    dashboard_parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop all running orcanium dashboard processes and exit",
    )
    dashboard_parser.add_argument(
        "--status",
        action="store_true",
        help="List running orcanium dashboard processes and exit",
    )
    # Backward-compat shim: older orcanium desktop app shells (<= 0.15.x) spawn the
    # backend as `orcanium dashboard --no-open --tui --host ... --port ...`. The
    # `--tui` flag was removed from this subcommand in cae6b5486 (embedded chat is
    # always on now). When a user's CLI updates past that commit but their desktop
    # app binary has not, argparse used to hard-error with "unrecognized arguments:
    # --tui" and exit(2) — the backend died before becoming ready and the GUI just
    # showed "orcanium couldn't start" with no actionable cause. Accept and silently
    # ignore the flag so an old app + new CLI degrades gracefully instead of
    # bricking. Hidden from --help; safe to delete once the floor app version is
    # well past 0.16.0.
    dashboard_parser.add_argument(
        "--tui",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)
