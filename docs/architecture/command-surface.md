# Orcanium Agent command surface

## Product boundary

`orcanium-agent` is a local-first, independently installable agent.  It has
four distinct surfaces.  A surface must not own another surface's work.

| Surface | Responsibility | Entry point |
| --- | --- | --- |
| Interactive agent | Local conversational work, session navigation, approvals, attachments, streamed tool progress | `orcanium` / `orcanium chat` (TUI) |
| Command line | Configuration, inspection, lifecycle operations and automation | `orcanium <command>` |
| Channel runtime | Headless delivery over messaging platforms | `orcanium channel run` |
| Local admin | Optional browser-based administration only | `orcanium admin` |

The private managed API product is named **Orcanium Gateway**.  The local
messaging runtime must not be called "gateway" in code, configuration, logs,
or user documentation.

## Stable command contract

```text
orcanium                         Launch TUI when stdin and stdout are TTYs
orcanium chat                    Launch TUI explicitly
orcanium run "task"              Run once; suitable for scripts and CI
orcanium config …                Read or update local configuration
orcanium setup                   Configure the local installation
orcanium model …                 Inspect or choose local model configuration
orcanium tools …                 Inspect or configure local tools
orcanium plugin …                Manage local plugins
orcanium auth …                  Configure BYOK credentials or managed Gateway access
orcanium doctor [--fix]          Diagnose and safely repair local installation issues
orcanium update [--check]        Update this local application and its TUI assets
orcanium channel run …           Start the headless messaging runtime
orcanium admin                   Start the optional local administration UI
```

Bare `orcanium` in a non-interactive context must exit without starting an
agent and explain that the caller should use `orcanium run "task"`.  Automation
must never depend on terminal UI, Node rendering, or interactive prompts.

## Current inventory (2026-07)

| Current component | Current location | Target disposition |
| --- | --- | --- |
| Main command parser and dispatch | `orcanium/cli/main.py`, `orcanium/cli/_parser.py` | Reduce to dispatch and focused lifecycle calls |
| Classic prompt-toolkit interactive REPL | `orcanium/cli/repl_full.py` | Delete after TUI parity |
| React/Ink interactive UI | `orcanium/tui/` | Sole interactive agent surface |
| TUI Python JSON-RPC bridge | `orcanium/rpc/` | Rename to `interactive_rpc/` |
| Local messaging daemon | `orcanium/gateway/` | Rename to `channel_runtime/` |
| One-shot automation | `orcanium/cli/oneshot.py`, `--oneshot` | Evolve into `orcanium run` |
| Doctor | `orcanium/cli/doctor.py` | Retain as lifecycle command |
| Update implementation | `orcanium/cli/main.py` | Extract to dedicated lifecycle modules |
| Local browser dashboard | `orcanium/cli/web_server.py`, `frontend/` | Retain as optional `admin`; no chat runtime ownership |

## Required parity before deleting the classic REPL

The TUI must support the following through the shared runtime, not copied REPL
logic:

- create, resume, and browse sessions;
- model/provider/toolset and working-directory overrides;
- streamed tool progress and approval decisions;
- local file/image attachments;
- configuration errors with a direct route to `orcanium doctor` or `setup`;
- update handoff to `orcanium update`.

## Implementation sequence

1. Introduce the command contract and tests without changing execution.
2. Extract a shared agent execution service used by TUI, `run`, and channels.
3. Make TUI the interactive default and add `run` as the canonical automation command.
4. Extract lifecycle code from `main.py`; keep `doctor` and `update` CLI-only.
5. Rename local runtime modules and their user-visible configuration.
6. Delete the classic REPL and all obsolete `--cli` / `--tui` switching logic.
7. Run fresh-install, update-recovery, TTY, non-TTY, and channel-runtime release tests.
