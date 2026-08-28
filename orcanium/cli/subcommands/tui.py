"""TUI subcommand — launch the orcanium terminal UI via rpc."""

from __future__ import annotations
import logging
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)


def build_tui_parser(subparsers, *, cmd_tui: Callable) -> None:
    parser = subparsers.add_parser(
        "tui",
        help="Launch the terminal user interface",
        description="Starts the orcanium TUI gateway for an interactive terminal experience.",
    )
    parser.set_defaults(func=cmd_tui)


def cmd_tui(args: Any) -> None:
    """Launch the TUI channel."""
    try:
        from orcanium.rpc.entry import main as tui_main
        tui_main()
    except ImportError as e:
        print(f"Error: TUI gateway not available — {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(0)
