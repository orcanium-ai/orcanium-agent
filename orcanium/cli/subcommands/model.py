"""``orcanium model`` subcommand parser.

Extracted verbatim from ``orcanium.cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_model_parser(subparsers, *, cmd_model: Callable) -> None:
    """Attach the ``model`` subcommand to ``subparsers``."""
    # =========================================================================
    # model command
    # =========================================================================
    model_parser = subparsers.add_parser(
        "model",
        help="Select default model and provider",
        description="Interactively select your inference provider and default model",
    )
    model_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Wipe the model picker disk cache and re-fetch every provider's live /v1/models list.",
    )
    model_parser.add_argument(
        "--client-id",
        default=None,
        help="OAuth client id to use for orcanium login (default: orcanium-cli)",
    )
    model_parser.add_argument(
        "--scope", default=None, help="OAuth scope to request for orcanium login"
    )
    model_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not attempt to open the browser automatically during orcanium login",
    )
    model_parser.add_argument(
        "--manual-paste",
        action="store_true",
        help=(
            "For loopback OAuth providers (xai-oauth, ...): skip the local "
            "callback listener and paste the failed callback URL from your "
            "browser instead. Use on browser-only remotes (Cloud Shell, "
            "Codespaces, EC2 Instance Connect, ...). See #26923."
        ),
    )
    model_parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP request timeout in seconds for orcanium login (default: 15)",
    )
    model_parser.add_argument(
        "--ca-bundle", help="Path to CA bundle PEM file for orcanium TLS verification"
    )
    model_parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification for orcanium login (testing only)",
    )
    model_parser.set_defaults(func=cmd_model)
