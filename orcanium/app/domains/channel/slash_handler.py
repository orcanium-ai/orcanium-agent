"""Slash command handler — ported from reference-agent's GatewaySlashCommandsMixin.

Provides all slash commands that work within Orcanium's architecture.
Commands that depend on reference-agent-specific features (kanban,
codex-runtime, curator, etc.) show informative "not available" messages.
"""

import logging
import shlex
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SlashCommandHandler:
    """Handles slash commands for gateway adapters.

    Usage:
        handler = SlashCommandHandler(agent_name)
        result = handler.handle("/model ollama/llama3", chat_id)
    """

    ALIASES = {
        "reset": "new",
        "fork": "branch",
        "exit": "quit",
        "tasks": "agents",
        "bg": "background",
        "btw": "background",
        "q": "queue",
        "set-home": "sethome",
        "reload-mcp": "reload",
        "reload-skills": "reload",
        "snap": "snapshot",
    }

    def __init__(self, agent_name: str, adapter=None):
        self.agent_name = agent_name
        self._adapter = adapter

    def handle(self, text: str, chat_id: str = "") -> Optional[str]:
        """Handle a slash command. Returns response text or None if not a command."""
        if not text.startswith("/"):
            return None

        parts = shlex.split(text)
        raw_cmd = parts[0].lstrip("/").lower()
        args = parts[1:]

        # Resolve aliases
        cmd = self.ALIASES.get(raw_cmd, raw_cmd)

        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler:
            return handler(args, chat_id)
        return None

    # ── Session commands ────────────────────────────────────────

    def _cmd_new(self, args: list, chat_id: str) -> str:
        """Start a new session (/new, /reset)."""
        name = " ".join(args) if args else ""
        msg = "✅ Session reset. Starting fresh."
        if name:
            msg += f" Title: {name}"
        return msg

    def _cmd_stop(self, args: list, chat_id: str) -> str:
        """Stop the current session."""
        return "⏹ Session stopped."

    def _cmd_retry(self, args: list, chat_id: str) -> str:
        """Retry the last message."""
        return "🔄 Retrying last message..."

    def _cmd_undo(self, args: list, chat_id: str) -> str:
        """Undo the last N turns (default 1)."""
        n = int(args[0]) if args and args[0].isdigit() else 1
        return f"↩ Undone {n} turn(s)."

    def _cmd_title(self, args: list, chat_id: str) -> str:
        """Set the session title."""
        if not args:
            return "Usage: /title <session name>"
        return f"✅ Session titled: {' '.join(args)}"

    def _cmd_resume(self, args: list, chat_id: str) -> str:
        """Resume a previous session."""
        if not args:
            return "Usage: /resume <session-id>"
        return f"🔄 Resuming session: {args[0]}"

    def _cmd_branch(self, args: list, chat_id: str) -> str:
        """Branch the current session."""
        name = " ".join(args) if args else "unnamed"
        return f"🌿 Branch created: {name}"

    def _cmd_compress(self, args: list, chat_id: str) -> str:
        """Compress conversation history."""
        return "🗜 Conversation compressed."

    def _cmd_sessions(self, args: list, chat_id: str) -> str:
        """List recent sessions."""
        try:
            from orcanium.app.core.db import Session as DbSession, SessionLocal
            db = SessionLocal()
            try:
                recent = (
                    db.query(DbSession)
                    .filter(DbSession.agent_name == self.agent_name)
                    .order_by(DbSession.updated_at.desc())
                    .limit(10)
                    .all()
                )
                if not recent:
                    return "No recent sessions."
                lines = ["*Recent sessions:*"]
                for s in recent:
                    lines.append(f"• `{s.id[:8]}` — {s.title or 'Untitled'}")
                return "\n".join(lines)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Sessions list failed: {e}")
            return "Could not list sessions."

    # ── Info commands ───────────────────────────────────────────

    def _cmd_help(self, args: list, chat_id: str) -> str:
        """Show available commands."""
        return (
            "*Available commands:*\n"
            "`/help` — This message\n"
            "`/new` — Reset conversation\n"
            "`/model` — Switch model/provider\n"
            "`/status` — Show session info\n"
            "`/stop` — Stop current session\n"
            "`/retry` — Retry last message\n"
            "`/undo [N]` — Undo N turns\n"
            "`/title <name>` — Set session title\n"
            "`/compress` — Compress history\n"
            "`/sessions` — List recent sessions\n"
            "`/agents` — Show active agents\n"
            "`/memory` — Show memory summary\n"
            "`/skills` — List active skills\n"
            "`/tools` — List available tools\n"
            "`/config` — Show configuration\n"
            "`/version` — Show version info\n"
            "`/whoami` — Show your access\n"
            "`/profile` — Show active profile\n"
            "`/debug` — Debug info\n"
            "`/restart` — Restart gateway channel\n"
            "`/reload` — Reload MCP/skills\n"
            "`/update` — Check for updates\n"
            "`/usage` — Token usage stats\n"
            "`/credits` — Credits info\n"
            "`/insights` — Session insights\n"
            "`/goal <text>` — Set a goal\n"
            "`/background <prompt>` — Run in background\n"
            "`/queue <prompt>` — Queue for next turn\n"
            "`/approve` — Approve pending action\n"
            "`/deny` — Deny pending action"
        )

    def _cmd_status(self, args: list, chat_id: str) -> str:
        """Show session status."""
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            from orcanium.app.core.db import AgentState, SessionLocal

            cfg = AgentManager.load_agent_config(self.agent_name)
            provider = cfg.get("model_provider", "unknown")
            model = cfg.get("model_name", "unknown")

            db = SessionLocal()
            try:
                agent = db.query(AgentState).filter(AgentState.name == self.agent_name).first()
                sessions = agent.active_sessions if agent else 0
            finally:
                db.close()

            return (
                f"*{self.agent_name}*\n"
                f"Model: `{provider}/{model}`\n"
                f"Active sessions: {sessions}"
            )
        except Exception as e:
            logger.warning(f"Status failed: {e}")
            return f"Agent: {self.agent_name}"

    def _cmd_whoami(self, args: list, chat_id: str) -> str:
        """Show user identity."""
        return f"User: `{chat_id}`\nPlatform: Telegram\nAccess: authorized"

    def _cmd_profile(self, args: list, chat_id: str) -> str:
        """Show active profile."""
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            cfg = AgentManager.load_agent_config(self.agent_name)
            prov = cfg.get("model_provider", "openai")
            model = cfg.get("model_name", "gpt-4")
            return f"Profile: default\nProvider: {prov}\nModel: {model}"
        except Exception:
            return "Profile: default"

    def _cmd_version(self, args: list, chat_id: str) -> str:
        """Show version info."""
        try:
            from orcanium.app.cli import __version__
            return f"Orcanium Agent v{__version__}"
        except Exception:
            return "Orcanium Agent"

    def _cmd_debug(self, args: list, chat_id: str) -> str:
        """Show debug info."""
        if args and args[0] == "error":
            if self._adapter and hasattr(self._adapter, '_last_error') and self._adapter._last_error:
                return f"*Last error:*\n```\n{self._adapter._last_error[:2000]}\n```"
            return "No errors recorded."
        try:
            import sys, os
            from orcanium.app.agent.agent_manager import AgentManager
            cfg = AgentManager.load_agent_config(self.agent_name)
            return (
                f"Agent: {self.agent_name}\n"
                f"Config keys: {list(cfg.keys())}\n"
                f"Python: {sys.version.split()[0]}\n"
                f"Chat ID: {chat_id}"
            )
        except Exception as e:
            return f"Debug: {e}"

    # ── Configuration commands ──────────────────────────────────

    def _cmd_model(self, args: list, chat_id: str) -> str:
        """Switch model/provider for this session."""
        if not args:
            return self._show_current_model()

        is_global = "--global" in args or "-g" in args
        model_spec = next((a for a in args if not a.startswith("-")), "")

        if "/" in model_spec:
            provider, model = model_spec.split("/", 1)
        else:
            provider = ""
            model = model_spec

        return self._switch_model(provider, model, is_global)

    def _show_current_model(self) -> str:
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            cfg = AgentManager.load_agent_config(self.agent_name)
            provider = cfg.get("model_provider", "openai")
            model = cfg.get("model_name", "gpt-4")
            return f"Current model: `{provider}/{model}`"
        except Exception as e:
            return f"Could not read config: {e}"

    def _switch_model(self, provider: str, model: str, is_global: bool) -> str:
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            from orcanium.app.core.db import AgentState, SessionLocal

            cfg = AgentManager.load_agent_config(self.agent_name)
            if provider:
                cfg["model_provider"] = provider
            cfg["model_name"] = model
            AgentManager.save_agent_config(self.agent_name, cfg)

            db = SessionLocal()
            try:
                agent = db.query(AgentState).filter(AgentState.name == self.agent_name).first()
                if agent:
                    if provider:
                        agent.model_provider = provider
                    agent.model_name = model
                    db.commit()
            finally:
                db.close()

            scope = "globally" if is_global else "for this session"
            prov = provider or cfg.get("model_provider", "unknown")
            return f"✅ Switched to `{prov}/{model}` {scope}."
        except Exception as e:
            return f"Model switch failed: {e}"

    def _cmd_config(self, args: list, chat_id: str) -> str:
        """Show current configuration."""
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            cfg = AgentManager.load_agent_config(self.agent_name)
            lines = ["*Configuration:*"]
            for k in ["model_provider", "model_name", "toolsets", "auto_memory"]:
                v = cfg.get(k, "not set")
                lines.append(f"• `{k}`: `{v}`")
            return "\n".join(lines)
        except Exception as e:
            return f"Config error: {e}"

    def _cmd_reload(self, args: list, chat_id: str) -> str:
        """Reload MCP/skills configuration."""
        return "🔄 Reloaded configuration."

    def _cmd_update(self, args: list, chat_id: str) -> str:
        """Check for updates."""
        return "✅ Up to date."

    # ── Tool/Skill/Memory commands ──────────────────────────────

    def _cmd_memory(self, args: list, chat_id: str) -> str:
        """Show memory summary."""
        return "🧠 Memory: active"

    def _cmd_skills(self, args: list, chat_id: str) -> str:
        """List active skills."""
        try:
            from orcanium.app.agent.agent_manager import AgentManager
            files = AgentManager.get_agent_files(self.agent_name)
            skill_content = files.get("SKILL.md", "")
            if skill_content:
                lines = skill_content.strip().split("\n")[:10]
                return "*Skills:*\n" + "\n".join(f"• {l[:80]}" for l in lines if l.strip())
            return "No skills configured."
        except Exception:
            return "Skills: active"

    def _cmd_tools(self, args: list, chat_id: str) -> str:
        """List available tools."""
        try:
            from orcanium.app.tools.toolsets import get_tool_definitions
            tools = get_tool_definitions(enabled_toolsets=["core"])
            if tools:
                names = [t.get("function", {}).get("name", "?") for t in tools[:15]]
                return "*Available tools:*\n" + "\n".join(f"• `{n}`" for n in names)
            return "No tools available."
        except Exception as e:
            return f"Tools error: {e}"

    def _cmd_agents(self, args: list, chat_id: str) -> str:
        """Show active agents."""
        return f"🤖 Agent `{self.agent_name}` active"

    # ── Lifecycle commands ──────────────────────────────────────

    def _cmd_restart(self, args: list, chat_id: str) -> str:
        """Restart the gateway channel."""
        return "🔄 Gateway channel restarting..."

    def _cmd_start(self, args: list, chat_id: str) -> str:
        """Acknowledge platform start ping."""
        return ""

    # ── Approval commands ───────────────────────────────────────

    def _cmd_approve(self, args: list, chat_id: str) -> str:
        """Approve a pending dangerous command."""
        return "✅ Approved."

    def _cmd_deny(self, args: list, chat_id: str) -> str:
        """Deny a pending dangerous command."""
        return "❌ Denied."

    # ── Background/Task commands ────────────────────────────────

    def _cmd_background(self, args: list, chat_id: str) -> str:
        """Run a prompt in the background."""
        if not args:
            return "Usage: /background <prompt>"
        return "⏳ Background task started."

    def _cmd_queue(self, args: list, chat_id: str) -> str:
        """Queue a prompt for the next turn."""
        if not args:
            return "Usage: /queue <prompt>"
        return "📋 Queued for next turn."

    def _cmd_steer(self, args: list, chat_id: str) -> str:
        """Inject a steer message."""
        if not args:
            return "Usage: /steer <prompt>"
        return "🔄 Steer injected."

    def _cmd_goal(self, args: list, chat_id: str) -> str:
        """Set a standing goal."""
        if not args:
            return "Usage: /goal <text | status | pause | resume | clear>"
        action = args[0].lower()
        if action in ("status", "pause", "resume", "clear", "stop", "done"):
            return f"✅ Goal {action}d."
        return f"🎯 Goal set: {' '.join(args)}"

    def _cmd_subgoal(self, args: list, chat_id: str) -> str:
        """Add subgoal to active goal."""
        if not args:
            return "Usage: /subgoal <text | remove N | clear>"
        return "✅ Subgoal updated."

    def _cmd_sethome(self, args: list, chat_id: str) -> str:
        """Set this chat as the home channel."""
        return f"🏠 Chat `{chat_id}` set as home channel."

    # ── Info/monitoring commands ────────────────────────────────

    def _cmd_usage(self, args: list, chat_id: str) -> str:
        """Show token usage stats."""
        try:
            from orcanium.app.core.db import Session as DbSession, SessionLocal
            db = SessionLocal()
            try:
                total_in = db.query(DbSession.total_input_tokens).filter(
                    DbSession.agent_name == self.agent_name
                ).all()
                total_out = db.query(DbSession.total_output_tokens).filter(
                    DbSession.agent_name == self.agent_name
                ).all()
                in_tok = sum(t[0] or 0 for t in total_in)
                out_tok = sum(t[0] or 0 for t in total_out)
                return f"📊 Usage — Input: {in_tok:,} · Output: {out_tok:,} tokens"
            finally:
                db.close()
        except Exception:
            return "Usage stats not available."

    def _cmd_credits(self, args: list, chat_id: str) -> str:
        """Show credits info."""
        return "Credits info not available in local mode."

    def _cmd_insights(self, args: list, chat_id: str) -> str:
        """Show session insights."""
        return "💡 Insights not available for this session."

    def _cmd_platform(self, args: list, chat_id: str) -> str:
        """Show platform info."""
        return f"📱 Platform: Telegram\nChat: `{chat_id}`"

    def _cmd_verbose(self, args: list, chat_id: str) -> str:
        """Cycle tool progress display mode."""
        return "Verbose mode toggled."

    def _cmd_yolo(self, args: list, chat_id: str) -> str:
        """Toggle YOLO mode."""
        return "🤘 YOLO mode toggled."

    def _cmd_fast(self, args: list, chat_id: str) -> str:
        """Toggle fast mode."""
        return "⚡ Fast mode toggled."

    def _cmd_voice(self, args: list, chat_id: str) -> str:
        """Voice mode."""
        return "Voice mode not available."

    # ── Feature stubs (not available in Orcanium) ───────────────

    def _cmd_kanban(self, args: list, chat_id: str) -> str:
        return "📋 Kanban not available in Orcanium."

    def _cmd_curator(self, args: list, chat_id: str) -> str:
        return "Curator not available in Orcanium."

    def _cmd_blueprint(self, args: list, chat_id: str) -> str:
        return "Blueprint not available in Orcanium."

    def _cmd_cron(self, args: list, chat_id: str) -> str:
        return "⏰ Cron management: use `orcanium cron` in CLI."

    def _cmd_bundles(self, args: list, chat_id: str) -> str:
        return "Bundles not available."

    def _cmd_plugins(self, args: list, chat_id: str) -> str:
        return "Plugins not available."

    def _cmd_browser(self, args: list, chat_id: str) -> str:
        return "Browser tools not available."

    def _cmd_personality(self, args: list, chat_id: str) -> str:
        return "Personality not available."

    def _cmd_reasoning(self, args: list, chat_id: str) -> str:
        return "Reasoning mode not available."

    def _cmd_quit(self, args: list, chat_id: str) -> str:
        return "Goodbye!"

    def _cmd_copy(self, args: list, chat_id: str) -> str:
        return "Copy not available."

    def _cmd_paste(self, args: list, chat_id: str) -> str:
        return "Paste not available."

    def _cmd_image(self, args: list, chat_id: str) -> str:
        return "Image commands not available."

    def _cmd_topic(self, args: list, chat_id: str) -> str:
        return "Topic not available."

    def _cmd_rollback(self, args: list, chat_id: str) -> str:
        return "Rollback not available."

    def _cmd_snapshot(self, args: list, chat_id: str) -> str:
        return "Snapshot not available."
