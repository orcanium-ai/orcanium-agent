"""``orcanium channel`` and ``orcanium proxy`` subcommand parsers.

Extracted verbatim from ``orcanium.cli/main.py:main()`` (god-file Phase 2).
Both parsers are built together because they shared one inline block (the
``channel`` section also defined ``proxy``). Handlers injected to avoid
importing ``main``.
"""

from __future__ import annotations

import argparse
from typing import Callable

from orcanium.cli.subcommands._shared import add_accept_hooks_flag


def _add_compat_platform_flag(parser: argparse.ArgumentParser) -> None:
    """Accept stale `channel <verb> --platform X` docs without advertising it.

    Gateway service lifecycle commands operate on the channel process, not a
    single messaging adapter.  Photon briefly printed a per-platform start
    command during setup; keep that command parseable so users following the
    old hint don't get blocked by argparse before the channel can start.
    """
    parser.add_argument(
        "--platform",
        dest="platform",
        help=argparse.SUPPRESS,
    )


def build_channel_parser(
    subparsers,
    *,
    cmd_channel: Callable,
    cmd_proxy: Callable,
    command_name: str = "channel",
) -> None:
    """Attach the local channel runtime and proxy subcommands."""
    # =========================================================================
    # channel command
    # =========================================================================
    gateway_parser = subparsers.add_parser(
        command_name,
        help="Messaging channel management",
        description="Manage messaging channels (Telegram, Discord, WhatsApp, Weixin, and more)",
    )
    gateway_subparsers = gateway_parser.add_subparsers(dest="channel_command")

    # channel run (default)
    gateway_run = gateway_subparsers.add_parser(
        "run", help="Run channels — selects agent interactively, starts in background"
    )
    gateway_run.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase stderr log verbosity (-v=INFO, -vv=DEBUG)",
    )
    gateway_run.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all stderr log output"
    )
    gateway_run.add_argument(
        "--agent", type=str, default=None,
        help="Agent name to run channels for (skips interactive selection).",
    )
    gateway_run.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground (default: background). Recommended for Docker/systemd.",
    )
    gateway_run.add_argument(
        "--replace",
        action="store_true",
        help="Replace any existing channel runtime (useful for systemd)",
    )
    gateway_run.add_argument(
        "--no-supervise",
        action="store_true",
        help=(
            "Inside the s6-overlay Docker image, normally `channel run` is "
            "automatically redirected to the supervised s6 service (so the "
            "channel gets auto-restart on crash, plus a supervised dashboard "
            "if ORCANIUM_DASHBOARD is set). Pass --no-supervise to opt out and "
            "get the historical pre-s6 foreground behavior: the channel is "
            "the container's main process and the container exits with the "
            "channel's exit code. No effect outside an s6 container."
        ),
    )
    add_accept_hooks_flag(gateway_run)
    add_accept_hooks_flag(gateway_parser)

    # channel start
    gateway_start = gateway_subparsers.add_parser(
        "start", help="Start the installed systemd/launchd background service"
    )
    gateway_start.add_argument(
        "--system",
        action="store_true",
        help="Target the Linux system-level channel service",
    )
    gateway_start.add_argument(
        "--all",
        action="store_true",
        help="Kill ALL stale channel processes across all profiles before starting",
    )
    _add_compat_platform_flag(gateway_start)

    # channel stop
    gateway_stop = gateway_subparsers.add_parser(
        "stop",
        help="Stop channel service",
        description="Stop the channel runtime. With --agent, stops channels for a specific agent only.",
    )
    gateway_stop.add_argument(
        "--agent", type=str, default=None,
        help="Agent name to stop channels for (default: all agents).",
    )
    gateway_stop.add_argument(
        "--system",
        action="store_true",
        help="Target the Linux system-level channel service",
    )
    gateway_stop.add_argument(
        "--all",
        action="store_true",
        help="Stop ALL channel processes across all profiles",
    )

    # channel restart
    gateway_restart = gateway_subparsers.add_parser(
        "restart", help="Restart channel service"
    )
    gateway_restart.add_argument(
        "--system",
        action="store_true",
        help="Target the Linux system-level channel service",
    )
    gateway_restart.add_argument(
        "--all",
        action="store_true",
        help="Kill ALL channel processes across all profiles before restarting",
    )
    _add_compat_platform_flag(gateway_restart)
    # channel install
    gateway_install = gateway_subparsers.add_parser(
        "install", help="Install channels as a systemd/launchd background service"
    )
    gateway_install.add_argument("--force", action="store_true", help="Force reinstall")
    gateway_install.add_argument(
        "--system",
        action="store_true",
        help="Install as a Linux system-level service (starts at boot)",
    )
    gateway_install.add_argument(
        "--run-as-user",
        dest="run_as_user",
        help="User account the Linux system service should run as",
    )
    gateway_install.add_argument(
        "--start-now",
        dest="start_now",
        action="store_true",
        default=None,
        help=argparse.SUPPRESS,
    )
    gateway_install.add_argument(
        "--no-start-now",
        dest="start_now",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    gateway_install.add_argument(
        "--start-on-login",
        dest="start_on_login",
        action="store_true",
        default=None,
        help=argparse.SUPPRESS,
    )
    gateway_install.add_argument(
        "--no-start-on-login",
        dest="start_on_login",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    gateway_install.add_argument(
        "--elevated-handoff",
        dest="elevated_handoff",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    # channel uninstall
    gateway_uninstall = gateway_subparsers.add_parser(
        "uninstall", help="Uninstall channel service"
    )
    gateway_uninstall.add_argument(
        "--system",
        action="store_true",
        help="Target the Linux system-level channel service",
    )

    # channel list
    gateway_subparsers.add_parser(
        "list",
        help="List channel profiles and their associated agents",
        description="Show all channel profiles (running status, PID) plus every configured agent (provider, model, status). A single-command overview for multi-agent deployments.",
    )

    # channel setup
    channel_setup_parser = gateway_subparsers.add_parser(
        "setup",
        help="Configure messaging platforms for an agent",
        description="Interactively configure messaging platforms (Telegram, Discord, etc.) for a specific agent. Creates a GatewayChannel record linked to the agent.",
    )
    channel_setup_parser.add_argument(
        "--agent", type=str, default=None,
        help="Agent name to configure channels for (default: interactive selection).",
    )

    # channel edit
    gateway_edit_parser = gateway_subparsers.add_parser(
        "edit",
        help="Edit a channel channel (change agent, update credentials, toggle, delete)",
        description="List all channel channels and interactively edit one: reassign agent, update platform credentials, toggle enable/disable, or delete the channel.",
    )
    gateway_edit_parser.set_defaults(channel_command="edit")

    # channel migrate-legacy
    gateway_migrate_legacy = gateway_subparsers.add_parser(
        "migrate-legacy",
        help="Remove legacy orcanium.service units from pre-rename installs",
        description=(
            "Stop, disable, and remove legacy orcanium channel unit files "
            "(e.g. orcanium.service) left over from older installs. Profile "
            "units (orcanium-channel-<profile>.service) and unrelated "
            "third-party services are never touched."
        ),
    )
    gateway_migrate_legacy.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="List what would be removed without doing it",
    )
    gateway_migrate_legacy.add_argument(
        "-y",
        "--yes",
        dest="yes",
        action="store_true",
        help="Skip the confirmation prompt",
    )

    # =========================================================================
    # proxy command — local OpenAI-compatible proxy that attaches the user's
    # OAuth-authenticated provider credentials to outbound requests. Lets
    # external apps (OpenViking, Karakeep, Open WebUI, ...) ride a logged-in
    # subscription without copy-pasting static API keys.
    # =========================================================================
    proxy_parser = subparsers.add_parser(
        "proxy",
        help="Local OpenAI-compatible proxy to OAuth providers",
        description=(
            "Run a local HTTP server that forwards OpenAI-compatible requests "
            "to an OAuth-authenticated provider (e.g. orcanium Portal). External "
            "apps can point at the proxy with any bearer token; the proxy "
            "attaches your real credentials."
        ),
    )
    proxy_subparsers = proxy_parser.add_subparsers(dest="proxy_command")

    proxy_start = proxy_subparsers.add_parser(
        "start", help="Run the proxy in the foreground"
    )
    proxy_start.add_argument(
        "--provider",
        default="orcanium",
        help="Upstream provider: orcanium or xai (default: orcanium). See `orcanium proxy providers`.",
    )
    proxy_start.add_argument(
        "--host",
        default=None,
        help="Bind address (default: 127.0.0.1). Use 0.0.0.0 to expose on LAN.",
    )
    proxy_start.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default: 8645)",
    )

    proxy_subparsers.add_parser(
        "status", help="Show which proxy upstreams are ready"
    )
    proxy_subparsers.add_parser(
        "providers", help="List available proxy upstream providers"
    )
    proxy_parser.set_defaults(func=cmd_proxy)
    gateway_parser.set_defaults(func=cmd_channel)
