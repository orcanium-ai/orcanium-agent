"""Telegram adapter — sync polling with streaming, model picker, and interactive UIs."""

import json
import logging
import threading
import traceback
import time
from typing import Any, Dict, Optional

import requests

from orcanium.app.agent.agent_runtime import AgentRuntime
from orcanium.app.core.db import SessionLocal
from orcanium.app.domains.channel.slash_handler import SlashCommandHandler
from orcanium.channel.stream_consumer import GatewayStreamConsumer, StreamConsumerConfig

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S = 1.0
_LONG_POLL_TIMEOUT = 25
_MAX_POLL_ERRORS = 5
_TYPING_REFRESH_INTERVAL = 4.0
_MODEL_PAGE_SIZE = 8


class TelegramAdapter:
    """Telegram adapter with sync polling, streaming, and interactive UIs."""

    def __init__(self, channel_id: str, config: Dict[str, Any]):
        self.channel_id = channel_id
        self.agent_name = config.get("agent_name", "")
        self.token = config.get("TELEGRAM_BOT_TOKEN") or config.get("token", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._slash_handler = SlashCommandHandler(self.agent_name, adapter=self) if self.agent_name else None
        # Interactive state
        self._model_picker_state: Dict[str, dict] = {}
        self._session_overrides: Dict[str, dict] = {}
        self._confirm_state: Dict[str, dict] = {}
        self._approval_state: Dict[str, dict] = {}
        self._clarify_state: Dict[str, dict] = {}
        self._last_error: Optional[str] = None

    def start(self) -> None:
        if self._running:
            return
        if not self.token or not self.agent_name:
            logger.error(f"TelegramAdapter {self.channel_id}: missing token or agent_name")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True,
            name=f"tg-{self.agent_name[:8]}",
        )
        self._thread.start()
        self._running = True
        logger.info(f"Telegram {self.agent_name} started (channel: {self.channel_id})")

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"Telegram {self.agent_name} stopped")

    # ── Message delivery ────────────────────────────────────────

    def send_message(self, chat_id: str, text: str) -> dict:
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    return {"message_id": data.get("result", {}).get("message_id")}
            return {}
        except Exception as e:
            logger.error(f"Telegram send_message failed: {e}")
            return {}

    def edit_message(self, chat_id: str, message_id: int, text: str,
                     finalize: bool = False) -> dict:
        try:
            resp = requests.post(
                f"{self.base_url}/editMessageText",
                json={"chat_id": chat_id, "message_id": message_id, "text": text},
                timeout=10,
            )
            if resp.status_code in (200, 429):
                return {"success": resp.status_code == 200}
            return {"success": False}
        except Exception as e:
            logger.debug(f"Telegram edit_message failed: {e}")
            return {"success": False}

    def _send_inline_keyboard(self, chat_id: str, text: str, buttons: list) -> bool:
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": {"inline_keyboard": buttons},
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Inline keyboard failed: {e}")
            return False

    def _edit_message_text(self, chat_id: str, message_id: int, text: str,
                           buttons: list = None):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if buttons is not None:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        else:
            payload["reply_markup"] = {"inline_keyboard": []}
        try:
            requests.post(f"{self.base_url}/editMessageText", json=payload, timeout=10)
        except Exception as e:
            logger.debug(f"Edit message failed: {e}")

    def _answer_callback(self, cq_id: str):
        try:
            requests.post(
                f"{self.base_url}/answerCallbackQuery",
                json={"callback_query_id": cq_id},
                timeout=5,
            )
        except Exception:
            pass



    # ── Async wrappers for stream consumer ──────────────────────
    # The reference-agent's GatewayStreamConsumer is async and calls
    # adapter.send(), adapter.edit_message(), adapter.send_draft() with await.
    # These async wrappers run the sync HTTP calls via asyncio.to_thread().

    async def send(self, chat_id: str, content: str, reply_to=None, metadata=None) -> Any:
        """Async wrapper for stream consumer.

        Returns a SendResult-like object with .success and .message_id.
        """
        import asyncio
        result = await asyncio.to_thread(self.send_message, chat_id, content)
        success = bool(result and result.get("message_id"))
        class _SendResult:
            def __init__(s, success, message_id=None):
                s.success = success
                s.message_id = message_id
        return _SendResult(success=success, message_id=result.get("message_id") if result else None)

    async def edit_message(self, chat_id: str, message_id: int, content: str, **kwargs) -> Any:
        """Async wrapper for stream consumer edit_message calls."""
        import asyncio
        result = await asyncio.to_thread(self.edit_message, chat_id, message_id, content, finalize=kwargs.get("finalize", False))
        success = result.get("success", False) if isinstance(result, dict) else False
        class _SendResult:
            def __init__(s, success=False):
                s.success = success
                s.message_id = None
        return _SendResult(success=success)

    def _keep_typing(self, chat_id: str, interval: float = _TYPING_REFRESH_INTERVAL) -> threading.Event:
        stop_event = threading.Event()
        def _refresh():
            while not stop_event.wait(interval):
                try:
                    requests.post(
                        f"{self.base_url}/sendChatAction",
                        json={"chat_id": chat_id, "action": "typing"},
                        timeout=5,
                    )
                except requests.RequestException:
                    pass
        threading.Thread(target=_refresh, daemon=True, name=f"typing-{chat_id[:8]}").start()
        return stop_event

    # ── Interactive: Confirm / Approve / Clarify ────────────────

    def send_slash_confirm(self, chat_id: str, title: str, message: str, confirm_id: str) -> bool:
        """Send a slash confirmation with Approve Once / Always Approve / Cancel."""
        text = f"*{title}*\n\n{message}" if title else message
        buttons = [
            [
                {"text": "✅ Approve Once", "callback_data": f"sc:once:{confirm_id}"},
                {"text": "🔒 Always Approve", "callback_data": f"sc:always:{confirm_id}"},
                {"text": "❌ Cancel", "callback_data": f"sc:cancel:{confirm_id}"},
            ]
        ]
        self._confirm_state[confirm_id] = {"chat_id": chat_id, "title": title, "message": message}
        return self._send_inline_keyboard(chat_id, text, buttons)

    def send_exec_approval(self, chat_id: str, tool_name: str, approval_id: str) -> bool:
        """Send an execution approval prompt with Allow/Deny buttons."""
        text = f"⚠️ *Tool Execution Request*\n\nTool: `{tool_name}`\n\nAllow?"
        buttons = [
            [
                {"text": "✅ Allow Once", "callback_data": f"ea:once:{approval_id}"},
                {"text": "✅ Session", "callback_data": f"ea:session:{approval_id}"},
                {"text": "✅ Always", "callback_data": f"ea:always:{approval_id}"},
                {"text": "❌ Deny", "callback_data": f"ea:deny:{approval_id}"},
            ]
        ]
        self._approval_state[approval_id] = {"chat_id": chat_id, "tool_name": tool_name}
        return self._send_inline_keyboard(chat_id, text, buttons)

    def send_clarify(self, chat_id: str, question: str, choices: list, clarify_id: str) -> bool:
        """Send a clarification prompt with numbered choice buttons."""
        lines = [f"*Clarification:* {question}"]
        for i, choice in enumerate(choices, 1):
            lines.append(f"  {i}. {choice}")
        text = "\n".join(lines)
        buttons = []
        row = []
        for i in range(len(choices)):
            row.append({"text": str(i + 1), "callback_data": f"cl:{clarify_id}:{i}"})
            if len(row) == 5 or i == len(choices) - 1:
                buttons.append(row)
                row = []
        buttons.append([{"text": "✏️ Other", "callback_data": f"cl:{clarify_id}:other"}])
        self._clarify_state[clarify_id] = {"chat_id": chat_id, "question": question, "choices": choices}
        return self._send_inline_keyboard(chat_id, text, buttons)

    # ── Interactive: Model Picker ───────────────────────────────

    def send_model_picker(self, chat_id: str):
        """Interactive provider → model drill-down picker."""
        from orcanium.app.api.keys import list_providers_and_keys
        from orcanium.app.api.models import list_provider_profiles
        from orcanium.app.agent.agent_manager import AgentManager

        db = SessionLocal()
        try:
            keys_data = list_providers_and_keys(db)
            profiles = list_provider_profiles()
        finally:
            db.close()

        configured_providers = {e["provider_id"] for e in keys_data if e.get("configured")}
        cfg = AgentManager.load_agent_config(self.agent_name)
        current_provider = (self._session_overrides.get(chat_id) or {}).get(
            "provider", cfg.get("model_provider", "openai")
        )
        current_model = (self._session_overrides.get(chat_id) or {}).get(
            "model", cfg.get("model_name", "gpt-4o")
        )

        filtered = [(pid, pdata) for pid, pdata in profiles.items() if pid in configured_providers]
        sorted_profiles = sorted(
            filtered,
            key=lambda kv: (0 if kv[0] == current_provider else 1, kv[1].get("name", "")),
        )

        if not sorted_profiles:
            self._send_sync(chat_id, "❌ No configured providers found.")
            return

        from orcanium.app.domains.model.registry import discover_models
        providers_data = []
        for pid, pdata in sorted_profiles:
            discovered = discover_models(pid)
            models_list = (
                discovered if discovered
                else [{"id": m, "name": m} for m in pdata.get("fallback_models", [])]
            )
            providers_data.append({
                "slug": pid,
                "name": pdata.get("display_name", pdata.get("name", pid)),
                "is_current": pid == current_provider,
                "models": models_list,
                "total_models": len(models_list),
            })

        self._model_picker_state[chat_id] = {"providers": providers_data}
        keyboard = self._build_provider_keyboard(providers_data)
        self._send_inline_keyboard(
            chat_id,
            f"*Model Configuration*\n\n"
            f"Current: `{current_provider}/{current_model}`\n\n"
            f"Select a provider:",
            keyboard,
        )

    def _build_provider_keyboard(self, providers: list) -> list:
        buttons = []
        for p in providers:
            count = p.get("total_models", len(p.get("models", [])))
            label = f"{p['name']} ({count})"
            if p.get("is_current"):
                label = f"✓ {label}"
            buttons.append({"text": label, "callback_data": f"mp:{p['slug']}"})
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows.append([{"text": "✗ Cancel", "callback_data": "mx"}])
        return rows

    def _build_model_keyboard(self, models: list, page: int = 0) -> tuple:
        total = len(models)
        total_pages = max(1, (total + _MODEL_PAGE_SIZE - 1) // _MODEL_PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        start = page * _MODEL_PAGE_SIZE
        end = min(start + _MODEL_PAGE_SIZE, total)
        page_models = models[start:end]
        buttons = []
        for i, m in enumerate(page_models):
            abs_idx = start + i
            short = m["name"].split("/")[-1] if "/" in m["name"] else m["name"]
            if len(short) > 38:
                short = short[:35] + "..."
            buttons.append({"text": short, "callback_data": f"mm:{abs_idx}"})
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append({"text": "◀ Prev", "callback_data": f"mg:{page - 1}"})
            nav.append({"text": f"{page + 1}/{total_pages}", "callback_data": "mx:noop"})
            if page < total_pages - 1:
                nav.append({"text": "Next ▶", "callback_data": f"mg:{page + 1}"})
            rows.append(nav)
        rows.append([
            {"text": "← Back", "callback_data": "mb"},
            {"text": "✗ Cancel", "callback_data": "mx"},
        ])
        page_info = f" ({start + 1}–{end} of {total})" if total_pages > 1 else ""
        return rows, page_info

    # ── Polling loop ────────────────────────────────────────────

    def _poll_loop(self):
        offset = 0
        errors = 0
        while not self._stop_event.is_set():
            try:
                url = f"{self.base_url}/getUpdates?offset={offset}&timeout={_LONG_POLL_TIMEOUT}"
                resp = requests.get(url, timeout=_LONG_POLL_TIMEOUT + 10)
                errors = 0
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            offset = update["update_id"] + 1
                            self._handle_update(update)
                elif resp.status_code == 401:
                    logger.error(f"Unauthorized token for {self.agent_name}")
                    break
            except requests.Timeout:
                pass
            except requests.ConnectionError as e:
                errors += 1
                if errors >= _MAX_POLL_ERRORS:
                    logger.warning(f"Telegram {errors}x connection errors, waiting 30s")
                    self._stop_event.wait(30)
                    errors = 0
                else:
                    self._stop_event.wait(2 ** errors)
                continue
            except Exception as e:
                logger.error(f"Telegram poll error: {e}")
                self._stop_event.wait(5)
                continue
            self._stop_event.wait(_POLL_INTERVAL_S)

    def _handle_update(self, update: dict):
        # ── Callback query (inline keyboard interaction) ────────
        callback_query = update.get("callback_query")
        if callback_query:
            self._handle_callback_query(callback_query)
            return

        # ── Regular message ─────────────────────────────────────
        message = update.get("message")
        if not message:
            return
        chat_id = str(message["chat"]["id"])
        text = message.get("text")
        if not text:
            return

        logger.info(f"Telegram message from {chat_id}: '{text[:50]}...' for agent '{self.agent_name}'")
        session_id = f"telegram_{self.agent_name}_{chat_id}"

        # ── Slash commands ──────────────────────────────────────
        if text.startswith("/"):
            if text.strip().lower() == "/model":
                self.send_model_picker(chat_id)
                return
            if self._slash_handler:
                response = self._slash_handler.handle(text, chat_id)
                if response:
                    self._send_sync(chat_id, response)
                    return
            self._send_sync(chat_id, f"Unknown command: {text}")
            return

        # ── Streaming pipeline ──────────────────────────────────
        typing_stop = self._keep_typing(chat_id)
        consumer = GatewayStreamConsumer(
            adapter=self, chat_id=chat_id,
            config=StreamConsumerConfig(edit_interval=0.4, buffer_threshold=10, cursor=" ▉"),
        )
        consumer.start()

        db = SessionLocal()
        try:
            runtime = AgentRuntime(self.agent_name, db)

            def on_delta(text):
                if text is None:
                    consumer.on_segment_break()
                else:
                    consumer.on_delta(text)

            def on_tool(name, action, **kw):
                if action == "start":
                    preview = kw.get("preview", "")
                    line = f"🔧 Using {name}"
                    if preview:
                        line += f": {preview[:40]}"
                    line += "..."
                    consumer.on_commentary(line)

            res = runtime.process_message(
                user_content=text, session_id=session_id,
                delta_callback=on_delta, tool_callback=on_tool,
                thinking_callback=lambda t: consumer.on_commentary(f"💭 {t}"),
                interim_callback=lambda t: consumer.on_commentary(t),
                clarify_callback=lambda q, c: self.send_clarify(chat_id, q, c, str(hash(q))[:8]),
            )
            reply = res.get("agent_response", "I could not generate a response.")
            consumer.finish()
            consumer.join(timeout=5.0)
            self._send_sync(chat_id, reply)

        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"Error: {e}\n{traceback.format_exc()}")
            try:
                self._send_sync(chat_id, "Sorry, I encountered an error.")
            except Exception:
                pass
        finally:
            typing_stop.set()
            db.close()

    def _handle_callback_query(self, cq: dict):
        """Handle inline keyboard callback queries."""
        cq_id = cq.get("id", "")
        chat_id = str(cq.get("message", {}).get("chat", {}).get("id", ""))
        msg_id = cq.get("message", {}).get("message_id")
        data = cq.get("data", "")
        if not chat_id or not data:
            self._answer_callback(cq_id)
            return

        self._answer_callback(cq_id)

        # ── Model picker callbacks ──────────────────────────
        if data.startswith("mp:") or data.startswith("mm:") or data.startswith("mg:") or data in ("mb", "mx"):
            self._handle_model_picker_callback(cq_id, chat_id, msg_id, data)
            return

        # ── Slash confirm callbacks ─────────────────────────
        if data.startswith("sc:"):
            parts = data.split(":", 2)
            action, cid = parts[1], parts[2]
            state = self._confirm_state.pop(cid, None)
            if state:
                labels = {"once": "✅ Approved (once)", "always": "🔒 Always Approved", "cancel": "❌ Cancelled"}
                self._edit_message_text(chat_id, msg_id, labels.get(action, action))
            else:
                self._edit_message_text(chat_id, msg_id, "❌ Confirmation expired.")
            return

        # ── Exec approval callbacks ─────────────────────────
        if data.startswith("ea:"):
            parts = data.split(":", 2)
            action, aid = parts[1], parts[2]
            state = self._approval_state.pop(aid, None)
            if state:
                labels = {"once": "✅ Allowed once", "session": "✅ Allowed for session",
                          "always": "✅ Always allowed", "deny": "❌ Denied"}
                self._edit_message_text(chat_id, msg_id, labels.get(action, action))
            else:
                self._edit_message_text(chat_id, msg_id, "❌ Approval expired.")
            return

        # ── Clarify callbacks ──────────────────────────────
        if data.startswith("cl:"):
            parts = data.split(":", 2)
            cid, choice_str = parts[1], parts[2]
            state = self._clarify_state.pop(cid, None)
            if state:
                if choice_str == "other":
                    label = "✏️ Other (please type your answer)"
                else:
                    idx = int(choice_str)
                    choices = state["choices"]
                    label = f"{idx + 1}. {choices[idx]}" if 0 <= idx < len(choices) else "Unknown"
                self._edit_message_text(chat_id, msg_id, f"*Your choice:* {label}")
            else:
                self._edit_message_text(chat_id, msg_id, "❌ Clarification expired.")
            return

    def _handle_model_picker_callback(self, cq_id: str, chat_id: str, msg_id: int, data: str):
        state = self._model_picker_state.get(chat_id)
        if not state:
            return

        if data == "mx":
            self._edit_message_text(chat_id, msg_id, "❌ Model selection cancelled.")
            self._model_picker_state.pop(chat_id, None)
            return

        if data == "mb":
            keyboard = self._build_provider_keyboard(state["providers"])
            self._edit_message_text(chat_id, msg_id, "*Model Configuration* — select a provider:", keyboard)
            return

        if data.startswith("mp:"):
            slug = data[3:]
            pd = next((p for p in state["providers"] if p["slug"] == slug), None)
            if not pd:
                return
            models = pd.get("models", [])
            state["selected_provider"] = slug
            state["selected_models"] = models
            state["model_page"] = 0
            if not models:
                self._edit_message_text(chat_id, msg_id, f"❌ No models for *{pd['name']}*.")
                return
            keyboard, info = self._build_model_keyboard(models, 0)
            self._edit_message_text(chat_id, msg_id, f"*{pd['name']}*{info} — select a model:", keyboard)
            return

        if data.startswith("mg:"):
            page = int(data[3:])
            models = state.get("selected_models", [])
            state["model_page"] = page
            slug = state.get("selected_provider", "")
            pd = next((p for p in state["providers"] if p["slug"] == slug), None)
            name = pd["name"] if pd else slug
            keyboard, info = self._build_model_keyboard(models, page)
            self._edit_message_text(chat_id, msg_id, f"*{name}*{info} — select a model:", keyboard)
            return

        if data.startswith("mm:"):
            idx = int(data[3:])
            models = state.get("selected_models", [])
            slug = state.get("selected_provider", "")
            pd = next((p for p in state["providers"] if p["slug"] == slug), None)
            if idx < 0 or idx >= len(models):
                return
            sel = models[idx]["name"]
            pname = pd["name"] if pd else slug
            from orcanium.app.agent.agent_manager import AgentManager
            from orcanium.app.core.db import AgentState, SessionLocal
            try:
                cfg = AgentManager.load_agent_config(self.agent_name)
                cfg["model_provider"] = slug
                cfg["model_name"] = sel
                AgentManager.save_agent_config(self.agent_name, cfg)
                db = SessionLocal()
                try:
                    agent = db.query(AgentState).filter(AgentState.name == self.agent_name).first()
                    if agent:
                        agent.model_provider = slug
                        agent.model_name = sel
                        db.commit()
                finally:
                    db.close()
                self._session_overrides[chat_id] = {"provider": slug, "model": sel}
                self._edit_message_text(chat_id, msg_id, f"✅ Switched to `{slug}/{sel}`")
            except Exception as e:
                self._edit_message_text(chat_id, msg_id, f"❌ Switch failed: {e}")
            finally:
                self._model_picker_state.pop(chat_id, None)

    def _send_sync(self, chat_id: str, text: str):
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
