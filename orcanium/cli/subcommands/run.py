"""Non-interactive single-task command for Orcanium Agent."""

from __future__ import annotations

from typing import Any, Callable


def build_run_parser(subparsers, *, cmd_run: Callable[[Any], None]) -> None:
    """Attach the automation-safe ``orcanium run`` command."""
    parser = subparsers.add_parser(
        "run",
        help="Run one agent task without an interactive terminal",
        description=(
            "Run a single task and write only its final response to stdout. "
            "Use this command in scripts, CI, pipes, and scheduled jobs."
        ),
    )
    parser.add_argument("prompt", help="Task for the agent to execute")
    parser.add_argument("--agent", default=None, help="Configured agent name")
    parser.add_argument("-m", "--model", default=None, help="Model override")
    parser.add_argument("--provider", default=None, help="Provider override")
    parser.add_argument("-t", "--toolsets", default=None, help="Comma-separated toolsets to enable")
    parser.set_defaults(func=cmd_run)
