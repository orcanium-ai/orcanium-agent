"""Optional local administration UI command."""

from __future__ import annotations

from typing import Any, Callable


def build_admin_parser(subparsers, *, cmd_admin: Callable[[Any], None]) -> None:
    """Attach the local admin UI command without making it an agent surface."""
    parser = subparsers.add_parser(
        "admin",
        help="Start the optional local administration UI",
        description="Launch local configuration and session administration in a browser.",
    )
    parser.add_argument("--port", type=int, default=9119, help="Port (default: 9119; 0 chooses one)")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser")
    parser.add_argument("--insecure", action="store_true", help="Allow a non-localhost bind")
    parser.add_argument("--skip-build", action="store_true", help="Serve an existing local UI build")
    parser.set_defaults(func=cmd_admin)
