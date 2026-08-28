"""Agent subcommand — setup, list, info, and manage agents."""

from __future__ import annotations
import logging
import sys
from typing import Any, Callable

from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.core.db import AgentState, SessionLocal

logger = logging.getLogger(__name__)


def build_agent_parser(subparsers, *, cmd_agent: Callable) -> None:
    parser = subparsers.add_parser(
        "agent",
        help="Manage agents (setup, list, info, configure)",
        description="Setup, list, configure, and manage Orcanium agents.",
    )
    parser.set_defaults(func=cmd_agent)
    sub = parser.add_subparsers(dest="agent_command")

    # setup — multi-agent interactive setup (replaces old create)
    setup_parser = sub.add_parser(
        "setup",
        help="Interactively create or configure agents (supports multiple agents)",
        description="Walk through creating one or more agents with provider, model, and optional SOUL.md. After setup, optionally configure a gateway for each agent.",
    )
    setup_parser.add_argument(
        "--skip-gateway",
        action="store_true",
        help="Skip gateway configuration prompt after agent setup",
    )
    setup_parser.set_defaults(agent_func=_cmd_agent_setup)

    # list
    list_parser = sub.add_parser("list", help="List all configured agents")
    list_parser.set_defaults(agent_func=_cmd_agent_list)

    # info
    info_parser = sub.add_parser("info", help="Show agent details")
    info_parser.add_argument("name", nargs="?", default="", help="Agent name")
    info_parser.set_defaults(agent_func=_cmd_agent_info)

    # edit
    edit_parser = sub.add_parser("edit", help="Edit an agent's provider, model, or SOUL")
    edit_parser.add_argument("name", help="Agent name")
    edit_parser.add_argument("--provider", help="New provider")
    edit_parser.add_argument("--model", help="New model")
    edit_parser.add_argument("--soul", help="New SOUL.md content")
    edit_parser.set_defaults(agent_func=_cmd_agent_edit)

    # remove
    remove_parser = sub.add_parser("remove", aliases=["rm"], help="Remove an agent and all its data")
    remove_parser.add_argument("name", help="Agent name")
    remove_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    remove_parser.set_defaults(agent_func=_cmd_agent_remove)

    # start
    start_parser = sub.add_parser("start", help="Start an agent runtime")
    start_parser.add_argument("name", help="Agent name")
    start_parser.set_defaults(agent_func=_cmd_agent_start)

    # stop
    stop_parser = sub.add_parser("stop", help="Stop an agent runtime")
    stop_parser.add_argument("name", help="Agent name")
    stop_parser.set_defaults(agent_func=_cmd_agent_stop)


def cmd_agent(args: Any) -> None:
    """Dispatch to agent subcommand."""
    func = getattr(args, "agent_func", None)
    if func:
        func(args)
        return
    _cmd_agent_list(args)


# ── Provider & model helpers ─────────────────────────────────────────


def _fetch_providers() -> list[dict]:
    """Fetch available providers from the API or fall back to CLI detection.

    Returns list of dicts with keys: provider_id, provider_name, configured, type.
    """
    import json
    import urllib.request

    # Try the local API first (same as frontend)
    try:
        req = urllib.request.Request("http://localhost:8000/api/v1/providers/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                return data
    except Exception:
        pass

    # Fallback: use CLI built-in provider list + env var detection
    try:
        from orcanium.cli.model_switch import list_authenticated_providers
        raw = list_authenticated_providers()
        results = []
        for p in raw:
            results.append({
                "provider_id": p.get("slug", ""),
                "provider_name": p.get("name", p.get("slug", "")),
                "configured": True,
                "type": "provider",
                "models": p.get("models", []),
            })
        if results:
            return results
    except Exception:
        pass

    # Last fallback: PREDEFINED_PROVIDERS from the API module
    try:
        from orcanium.app.api.keys import PREDEFINED_PROVIDERS
        import os
        results = []
        for pid, info in PREDEFINED_PROVIDERS.items():
            env_val = os.environ.get(info["env_var"], "")
            results.append({
                "provider_id": pid,
                "provider_name": info["name"],
                "configured": bool(env_val),
                "type": info.get("type", "provider"),
                "env_var": info["env_var"],
            })
        return results
    except Exception:
        pass

    return []


def _fetch_models_for_provider(provider_id: str) -> list[str]:
    """Fetch available models for a given provider.

    Tries multiple sources in order:
    1. Local API ``/api/v1/models?provider=...``
    2. CLI curated model lists (``_PROVIDER_MODELS``, ``OPENROUTER_MODELS``)
    3. ``list_authenticated_providers()`` which queries provider's /v1/models
    """
    import json
    import urllib.request

    # 1. Local API
    try:
        url = f"http://localhost:8000/api/v1/models?provider={provider_id}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                return [m.get("id", m) if isinstance(m, dict) else m for m in data]
            if isinstance(data, dict) and "models" in data:
                return data["models"]
    except Exception:
        pass

    # 2. CLI curated model lists
    try:
        from orcanium.cli.models import _PROVIDER_MODELS, OPENROUTER_MODELS
        # Check provider-specific models first
        if provider_id in _PROVIDER_MODELS:
            curated = _PROVIDER_MODELS[provider_id]
            if isinstance(curated, dict):
                return list(curated.keys())[:30]
            if isinstance(curated, list):
                return curated[:30]
        # OpenRouter models (openrouter provider uses OPENROUTER_MODELS)
        if provider_id == "openrouter" and OPENROUTER_MODELS:
            return [m["id"] for m in OPENROUTER_MODELS if "id" in m][:30]
    except Exception:
        pass

    # 3. list_authenticated_providers — queries provider's /v1/models endpoint
    try:
        from orcanium.cli.model_switch import list_authenticated_providers
        for p in list_authenticated_providers():
            if p.get("slug") == provider_id:
                models = p.get("models", [])
                if models:
                    return models[:30]
    except Exception:
        pass

    return []


def _prompt_numbered(options: list[str], title: str, default: int = 0) -> int:
    """Numbered-list selection. Press Enter for default, or type a number."""
    print()
    for idx, opt in enumerate(options, start=1):
        marker = "→" if idx == default + 1 else " "
        print(f"     {marker} {idx}. {opt}")
    print()
    prompt = f"  {title} [{default+1}]: "
    try:
        choice = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return -1
    if not choice:
        return default
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    print(f"  Invalid choice. Enter 1-{len(options)}.")
    return _prompt_numbered(options, title, default)


def _prompt_agent_details(existing_names: set) -> tuple[str, str, str, str] | None:
    """Prompt for a single agent's name, provider (interactive), model, and SOUL.

    Returns (name, provider, model, soul) or None if the user wants to stop.
    """
    print()
    try:
        name = input("  1. Enter agent name [or blank to finish]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not name:
        return None
    if name in existing_names:
        print(f"  ✗ Agent '{name}' already exists. Choose a different name.")
        return _prompt_agent_details(existing_names)

    # ── Provider selection ─────────────────────────────────────────
    print()
    providers = _fetch_providers()

    # Filter to only configured providers
    configured = [p for p in providers if p.get("configured")]

    if not configured:
        print("  2. Provider:")
        print()
        print("     No providers configured.")
        print()
        try:
            answer = input("     Set up a provider now? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return None

        if answer in ("y", "yes"):
            print()
            print("  → Launching provider setup...")
            print()
            import subprocess
            import sys as _sys
            ret = subprocess.run([_sys.executable, "-m", "orcanium.cli", "model"])
            if ret.returncode != 0:
                print("  Provider setup did not complete.")
                return None
            # Re-fetch providers after setup
            providers = _fetch_providers()
            configured = [p for p in providers if p.get("configured")]

        if not configured:
            print("  No provider configured. Agent creation cancelled.")
            return None

    provider_names = [f"{p['provider_name']:<20} ({p['provider_id']})"
                      for p in configured]
    print("  2. Provider:")
    default_idx = 0
    for i, p in enumerate(configured):
        if p["provider_id"] in ("openai", "openrouter") and p.get("configured"):
            default_idx = i
            break

    sel = _prompt_numbered(provider_names, "Select provider", default_idx)
    if sel < 0:
        return None
    provider_id = configured[sel]["provider_id"]

    # ── Model selection ────────────────────────────────────────────
    models = _fetch_models_for_provider(provider_id)
    if not models:
        # Fallback: try fetching via the provider's /v1/models endpoint
        # or ask user to type model name
        print(f"     (no models listed for {provider_id})")
        print()
        model = input(f"  3. Model (type model name, e.g. deepseek-chat): ").strip()
        if not model:
            print("     Model name is required.")
            return _prompt_agent_details(existing_names)
    else:
        print(f"  3. Model:")
        sel_model = _prompt_numbered(models, "Select model", 0)
        if sel_model < 0:
            return None
        model = models[sel_model]

    # ── SOUL.md ────────────────────────────────────────────────────
    print()
    print("  4. SOUL.md (optional, press Enter twice to skip):")
    soul_lines = []
    try:
        first = input("     > ").strip()
        if first:
            soul_lines.append(first)
            while True:
                line = input("     > ")
                if line == "" and soul_lines and soul_lines[-1] == "":
                    soul_lines.pop()
                    break
                if not soul_lines:
                    break
                soul_lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()

    soul = "\n".join(soul_lines).strip()
    return (name, provider_id, model, soul)


def _create_single_agent(name: str, provider: str, model: str, soul: str = "") -> bool:
    """Create one agent via the backend API (same as frontend)."""
    import urllib.request
    import urllib.parse

    try:
        params = urllib.parse.urlencode({
            "name": name,
            "model_provider": provider,
            "model_name": model,
        })
        if soul.strip():
            params += "&soul=" + urllib.parse.quote(soul)
        url = f"http://localhost:8000/api/v1/agents/create?{params}"
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    except Exception:
        pass

    # Fallback: direct DB + filesystem
    try:
        db = SessionLocal()
        try:
            config = {"model_provider": provider, "model_name": model}
            AgentManager.create_agent(db=db, name=name, soul=soul, config=config)
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"  ✗ Failed to create agent '{name}': {e}")
        return False


def _cmd_agent_setup(args: Any) -> None:
    """Multi-agent interactive setup flow."""
    print()
    print("  Agent Setup ──────────────────────────────────────────────")
    print()

    created = []
    existing_names = set()

    try:
        db = SessionLocal()
        try:
            AgentManager.sync_all_agents(db)
            for a in db.query(AgentState).all():
                existing_names.add(a.name)
        finally:
            db.close()
    except Exception:
        pass

    while True:
        result = _prompt_agent_details(existing_names)
        if result is None:
            break
        name, provider, model, soul = result

        if _create_single_agent(name, provider, model, soul):
            print(f"  ✓ Agent '{name}' created ({provider}/{model})")
            created.append(name)
            existing_names.add(name)
        print()

    if not created:
        print("  No agents configured.")
        return

    print(f"  ✓ {len(created)} agent(s) configured.")
    print()

    # Offer gateway setup unless --skip-gateway
    if getattr(args, "skip_gateway", False):
        return

    try:
        answer = input("  Would you like to set up a gateway for any of these agents? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer in ("y", "yes"):
        print()
        print("  Select agent to configure gateway for:")
        for idx, name in enumerate(created, start=1):
            print(f"    {idx}. {name}")
        print()
        try:
            choice = input("  Enter number [1]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not choice:
            choice = "1"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(created):
                agent_name = created[idx]
                print(f"\n  → Launching gateway setup for '{agent_name}'...\n")
                import subprocess
                import sys as _sys
                subprocess.run([
                    _sys.executable, "-m", "orcanium.cli",
                    "gateway", "setup", "--agent", agent_name,
                ])
        except (ValueError, IndexError):
            print("  Invalid choice.")


def _cmd_agent_list(args: Any) -> None:
    """List all configured agents."""
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agents = db.query(AgentState).order_by(AgentState.name).all()

        if not agents:
            print("  No agents configured.")
            print("  Create one with: orcanium agent setup")
            return

        print(f"  {'Agent':<20} {'Provider':<15} {'Model':<20} {'Status':<10}")
        print(f"  {'─'*20} {'─'*15} {'─'*20} {'─'*10}")
        for a in agents:
            prov = a.model_provider or "—"
            model = a.model_name or "—"
            status = a.status or "stopped"
            status_dot = "●" if status == "running" else "○"
            print(f"  {a.name:<20} {prov:<15} {model:<20} {status_dot} {status}")
        print()
        print(f"  {len(agents)} agent(s)")
        print("  orcanium agent setup          — Create new agents")
        print("  orcanium agent info <name>    — Show agent details")
    finally:
        db.close()


def _cmd_agent_info(args: Any) -> None:
    """Show agent details."""
    name = args.name

    db = SessionLocal()
    try:
        if name:
            agents = db.query(AgentState).filter(AgentState.name == name).all()
        else:
            agents = db.query(AgentState).order_by(AgentState.name).all()

        if not agents:
            print("  No agents found.")
            return

        for a in agents:
            print(f"  Agent:     {a.name}")
            print(f"  Status:    {a.status or 'stopped'}")
            print(f"  Provider:  {a.model_provider or '—'}")
            print(f"  Model:     {a.model_name or '—'}")
            print(f"  Sessions:  {a.active_sessions or 0}")
            print()
    finally:
        db.close()


def _cmd_agent_edit(args: Any) -> None:
    """Edit an agent's provider, model, or SOUL."""
    name = args.name
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            print(f"  ✗ Agent '{name}' not found.")
            return
        provider = getattr(args, "provider", None)
        model = getattr(args, "model", None)
        soul = getattr(args, "soul", None)
        if provider:
            agent.model_provider = provider
        if model:
            agent.model_name = model
        if soul:
            cfg_path = AgentManager.get_agent_dir(name) / "SOUL.md"
            cfg_path.write_text(soul, encoding="utf-8")
        db.commit()
        changes = []
        if provider: changes.append(f"provider={provider}")
        if model: changes.append(f"model={model}")
        if soul: changes.append("soul=updated")
        print(f"  ✓ Agent '{name}' updated: {', '.join(changes)}")
    finally:
        db.close()


def _cmd_agent_remove(args: Any) -> None:
    """Remove an agent and all its data."""
    name = args.name
    force = getattr(args, "force", False)
    if not force:
        try:
            ok = input(f"  Remove agent '{name}' and all its data? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ok not in ("y", "yes"):
            print("  Cancelled.")
            return
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            print(f"  ✗ Agent '{name}' not found.")
            return
        import shutil
        agent_dir = AgentManager.get_agent_dir(name)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        db.delete(agent)
        db.commit()
        print(f"  ✓ Agent '{name}' removed.")
    finally:
        db.close()


def _cmd_agent_start(args: Any) -> None:
    """Start an agent runtime."""
    name = args.name
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            print(f"  ✗ Agent '{name}' not found.")
            return
        agent.status = "running"
        db.commit()
        print(f"  ✓ Agent '{name}' started.")
    finally:
        db.close()


def _cmd_agent_stop(args: Any) -> None:
    """Stop an agent runtime."""
    name = args.name
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            print(f"  ✗ Agent '{name}' not found.")
            return
        agent.status = "stopped"
        db.commit()
        print(f"  ✓ Agent '{name}' stopped.")
    finally:
        db.close()
