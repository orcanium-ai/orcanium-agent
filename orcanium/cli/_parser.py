"""
Top-level argparse construction for the orcanium CLI.

Lives in its own module so other modules (e.g. ``relaunch.py``) can
introspect the parser to discover which flags exist without running the
``main`` fn.

Only the top-level parser and the ``chat`` subparser live here. Every other
subparser (model, gateway, sessions, …) is built inline in ``main.py``
because its dispatch is tightly coupled to module-level ``cmd_*`` functions.
"""

import argparse


# `--profile` / `-p` is consumed by ``main._apply_profile_override`` before
# argparse runs (it sets ``ORCANIUM_HOME`` and strips itself from ``sys.argv``),
# so it isn't on the parser. Listed here so all "carry over on relaunch"
# metadata lives in one file.
PRE_ARGPARSE_INHERITED_FLAGS: list[tuple[str, bool]] = [
    ("--profile", True),
    ("-p", True),
]


def _inherited_flag(parser, *args, **kwargs):
    """Register a flag that ``orcanium.cli.relaunch`` should carry over when
    the CLI re-execs itself (e.g. after ``sessions browse`` picks a session,
    or after the setup wizard launches chat).

    Equivalent to ``parser.add_argument(...)`` plus tagging the resulting
    Action with ``inherit_on_relaunch = True`` so the relaunch table builder
    can find it via introspection.
    """
    action = parser.add_argument(*args, **kwargs)
    action.inherit_on_relaunch = True
    return action


_EPILOGUE = """
Examples:
    orcanium                        Start the interactive terminal UI
    orcanium chat                   Start the interactive terminal UI explicitly
    orcanium run "Hello"            Run one task for a script, pipe, or CI job
    orcanium channel run             Run configured messaging channels
    orcanium admin                   Start the optional local admin UI
    orcanium -c                     Resume the most recent session
    orcanium -c "my project"        Resume a session by name (latest in lineage)
    orcanium --resume <session_id>  Resume a specific session by ID
    orcanium setup                  Run setup wizard
    orcanium logout                 Clear stored authentication
    orcanium auth setup             Configure providers and default models
    orcanium auth add <provider>    Add a pooled credential
    orcanium auth list              List pooled credentials
    orcanium auth remove <p> <t>    Remove pooled credential by index, id, or label
    orcanium auth reset <provider>  Clear exhaustion status for a provider
    orcanium agent setup            Create and configure agents
    orcanium agent list             List all agents
    orcanium fallback list          Show fallback provider chain
    orcanium fallback add           Add a fallback provider
    orcanium fallback remove        Remove a fallback provider
    orcanium config                 View configuration
    orcanium config edit            Edit config in $EDITOR
    orcanium gateway                Run messaging gateway
    orcanium gateway setup          Configure messaging platforms for an agent
    orcanium gateway list           Show all gateway profiles and agents
    orcanium gateway status         Show running gateways (like docker ps)
    orcanium gateway stop           Stop gateway service
    orcanium gateway install        Install gateway background service
    orcanium -s orcanium-agent-dev,github-auth
    orcanium -w                     Start in isolated git worktree
    orcanium sessions list          List past sessions
    orcanium sessions browse        Interactive session picker
    orcanium sessions rename ID T   Rename/title a session
    orcanium logs                   View agent.log (last 50 lines)
    orcanium logs -f                Follow agent.log in real time
    orcanium logs errors            View errors.log
    orcanium logs --since 1h        Lines from the last hour
    orcanium debug share            Upload debug report for support
    orcanium update                 Update to latest version
    orcanium dashboard start        Start web UI dashboard (port 9119)
    orcanium dashboard stop         Stop running dashboard processes
    orcanium dashboard status       List running dashboard processes

For more help on a command:
    orcanium <command> --help
"""


def build_top_level_parser():
    """Build the top-level parser, the subparsers action, and the ``chat`` subparser.

    Returns ``(parser, subparsers, chat_parser)``. The caller wires
    ``chat_parser.set_defaults(func=cmd_chat)`` and continues registering
    other subparsers via ``subparsers.add_parser(...)``.
    """
    parser = argparse.ArgumentParser(
        prog="orcanium",
        description="orcanium Agent - AI assistant with tool-calling capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOGUE,
    )

    parser.add_argument(
        "--version", "-V", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "-z",
        "--oneshot",
        metavar="PROMPT",
        default=None,
        help=(
            "One-shot mode: send a single prompt and print ONLY the final "
            "response text to stdout. No banner, no spinner, no tool "
            "previews, no session_id line. Tools, memory, rules, and "
            "AGENTS.md in the CWD are loaded as normal; approvals are "
            "auto-bypassed. Intended for scripts / pipes."
        ),
    )
    # --model / --provider are accepted at the top level so they can pair
    # with -z without needing the `chat` subcommand.  If neither -z nor a
    # subcommand consumes them, they fall through harmlessly as None.
    # Mirrors `orcanium chat --model ... --provider ...` semantics.
    _inherited_flag(
        parser,
        "-m",
        "--model",
        default=None,
        help=(
            "Model override for this invocation (e.g. anthropic/claude-sonnet-4.6). "
            "Applies to -z/--oneshot and --tui. Also settable via ORCANIUM_INFERENCE_MODEL env var."
        ),
    )
    _inherited_flag(
        parser,
        "--agent",
        default=None,
        help="Agent name for this invocation (default: auto). Selects which agent configuration to use.",
    )
    _inherited_flag(
        parser,
        "--provider",
        default=None,
        help=(
            "Provider override for this invocation (e.g. openrouter, anthropic). "
            "Applies to -z/--oneshot and --tui. The persistent provider lives in config.yaml "
            "under model.provider — use `orcanium setup` or edit the file to change it."
        ),
    )
    parser.add_argument(
        "-t",
        "--toolsets",
        default=None,
        help="Comma-separated toolsets to enable for this invocation. Applies to -z/--oneshot and --tui.",
    )
    parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION",
        default=None,
        help="Resume a previous session by ID or title",
    )
    parser.add_argument(
        "--continue",
        "-c",
        dest="continue_last",
        nargs="?",
        const=True,
        default=None,
        metavar="SESSION_NAME",
        help="Resume a session by name, or the most recent if no name given",
    )
    parser.add_argument(
        "--worktree",
        "-w",
        action="store_true",
        default=False,
        help="Run in an isolated git worktree (for parallel agents)",
    )
    _inherited_flag(
        parser,
        "--accept-hooks",
        action="store_true",
        default=False,
        help=(
            "Auto-approve any unseen shell hooks declared in config.yaml "
            "without a TTY prompt.  Equivalent to ORCANIUM_ACCEPT_HOOKS=1 or "
            "hooks_auto_accept: true in config.yaml.  Use on CI / headless "
            "runs that can't prompt."
        ),
    )
    _inherited_flag(
        parser,
        "--skills",
        "-s",
        action="append",
        default=None,
        help="Preload one or more skills for the session (repeat flag or comma-separate)",
    )
    _inherited_flag(
        parser,
        "--yolo",
        action="store_true",
        default=False,
        help="Bypass all dangerous command approval prompts (use at your own risk)",
    )
    _inherited_flag(
        parser,
        "--pass-session-id",
        action="store_true",
        default=False,
        help="Include the session ID in the agent's system prompt",
    )
    _inherited_flag(
        parser,
        "--ignore-user-config",
        action="store_true",
        default=False,
        help="Ignore ~/.orcanium/config.yaml and fall back to built-in defaults (credentials in .env are still loaded)",
    )
    _inherited_flag(
        parser,
        "--ignore-rules",
        action="store_true",
        default=False,
        help="Skip auto-injection of AGENTS.md, SOUL.md, .cursorrules, memory, and preloaded skills",
    )
    _inherited_flag(
        parser,
        "--safe-mode",
        action="store_true",
        default=False,
        help="Troubleshooting mode: disable ALL customizations — user config, AGENTS.md/memory injection, plugins, and MCP servers (implies --ignore-user-config and --ignore-rules)",
    )
    _inherited_flag(
        parser,
        "--tui",
        action="store_true",
        default=False,
        help="Launch the terminal UI explicitly",
    )
    _inherited_flag(
        parser,
        "--dev",
        dest="tui_dev",
        action="store_true",
        default=False,
        help="With --tui: run TypeScript sources via tsx (skip dist build)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # =========================================================================
    # chat command
    # =========================================================================
    chat_parser = subparsers.add_parser(
        "chat",
        help="Interactive chat with the agent",
        description="Start an interactive chat session with orcanium Agent",
    )
    chat_parser.add_argument(
        "-q", "--query", help="Single query (non-interactive mode)"
    )
    chat_parser.add_argument(
        "--image", help="Optional local image path to attach to a single query"
    )
    _inherited_flag(
        chat_parser,
        "-m", "--model", help="Model to use (e.g., anthropic/claude-sonnet-4)",
    )
    chat_parser.add_argument(
        "-t", "--toolsets", help="Comma-separated toolsets to enable"
    )
    _inherited_flag(
        chat_parser,
        "-s",
        "--skills",
        action="append",
        default=argparse.SUPPRESS,
        help="Preload one or more skills for the session (repeat flag or comma-separate)",
    )
    _inherited_flag(
        chat_parser,
        "--provider",
        # No `choices=` here: user-defined providers from config.yaml `providers:`
        # are also valid values, and runtime resolution (resolve_runtime_provider)
        # handles validation/error reporting consistently with the top-level
        # `--provider` flag.
        default=None,
        help="Inference provider (default: auto). Built-in or a user-defined name from `providers:` in config.yaml.",
    )
    _inherited_flag(
        chat_parser,
        "--agent",
        default=None,
        help="Agent name for this chat session (default: auto).",
    )
    chat_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Verbose output",
    )
    chat_parser.add_argument(
        "-Q",
        "--quiet",
        action="store_true",
        help="Quiet mode for programmatic use: suppress banner, spinner, and tool previews. Only output the final response and session info.",
    )
    chat_parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION_ID",
        default=argparse.SUPPRESS,
        help="Resume a previous session by ID (shown on exit)",
    )
    chat_parser.add_argument(
        "--continue",
        "-c",
        dest="continue_last",
        nargs="?",
        const=True,
        default=argparse.SUPPRESS,
        metavar="SESSION_NAME",
        help="Resume a session by name, or the most recent if no name given",
    )
    chat_parser.add_argument(
        "--worktree",
        "-w",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Run in an isolated git worktree (for parallel agents on the same repo)",
    )
    _inherited_flag(
        chat_parser,
        "--accept-hooks",
        action="store_true",
        default=argparse.SUPPRESS,
        help=(
            "Auto-approve any unseen shell hooks declared in config.yaml "
            "without a TTY prompt (see also ORCANIUM_ACCEPT_HOOKS env var and "
            "hooks_auto_accept: in config.yaml)."
        ),
    )
    chat_parser.add_argument(
        "--checkpoints",
        action="store_true",
        default=False,
        help="Enable filesystem checkpoints before destructive file operations (use /rollback to restore)",
    )
    chat_parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        metavar="N",
        help="Maximum tool-calling iterations per conversation turn (default: 90, or agent.max_turns in config)",
    )
    _inherited_flag(
        chat_parser,
        "--yolo",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Bypass all dangerous command approval prompts (use at your own risk)",
    )
    _inherited_flag(
        chat_parser,
        "--pass-session-id",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Include the session ID in the agent's system prompt",
    )
    _inherited_flag(
        chat_parser,
        "--ignore-user-config",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Ignore ~/.orcanium/config.yaml and fall back to built-in defaults (credentials in .env are still loaded). Useful for isolated CI runs, reproduction, and third-party integrations.",
    )
    _inherited_flag(
        chat_parser,
        "--ignore-rules",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Skip auto-injection of AGENTS.md, SOUL.md, .cursorrules, memory, and preloaded skills. Combine with --ignore-user-config for a fully isolated run.",
    )
    _inherited_flag(
        chat_parser,
        "--safe-mode",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Troubleshooting mode: disable ALL customizations — user config, AGENTS.md/memory injection, plugins, and MCP servers (implies --ignore-user-config and --ignore-rules). Use to isolate whether a problem comes from your setup or from orcanium itself.",
    )
    chat_parser.add_argument(
        "--source",
        default=None,
        help="Session source tag for filtering (default: cli). Use 'tool' for third-party integrations that should not appear in user session lists.",
    )
    _inherited_flag(
        chat_parser,
        "--tui",
        action="store_true",
        default=False,
        help="Launch the terminal UI explicitly",
    )
    _inherited_flag(
        chat_parser,
        "--dev",
        dest="tui_dev",
        action="store_true",
        default=False,
        help="With --tui: run TypeScript sources via tsx (skip dist build)",
    )

    return parser, subparsers, chat_parser
