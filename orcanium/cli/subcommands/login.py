"""``orcanium login`` subcommand parser.

Extracted verbatim from ``orcanium.cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_login_parser(subparsers, *, cmd_login: Callable) -> None:
    """Attach the ``login`` subcommand to ``subparsers``."""
    # =========================================================================
    # login command
    # =========================================================================
    login_parser = subparsers.add_parser(
        "login",
        help="Authenticate with an inference provider",
        description="Run OAuth device authorization flow for orcanium CLI",
    )
    login_parser.add_argument(
        "--provider",
        choices=["openai-codex", "xai-oauth"],
        default="openai-codex",
        help="Provider to authenticate with (managed Orcanium Gateway uses ORCANIUM_API_KEY)",
    )
    login_parser.add_argument(
        "--client-id", default=None, help="OAuth client id to use (default: orcanium-cli)"
    )
    login_parser.add_argument("--scope", default=None, help="OAuth scope to request")
    login_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not attempt to open the browser automatically",
    )
    login_parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP request timeout in seconds (default: 15)",
    )
    login_parser.add_argument(
        "--ca-bundle", help="Path to CA bundle PEM file for TLS verification"
    )
    login_parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification (testing only)",
    )
    login_parser.set_defaults(func=cmd_login)
