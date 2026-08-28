"""Compatibility shims — bridges reference-agent imports to Orcanium infrastructure.

Path functions delegate to ``orcanium.orcanium_constants`` so all code resolves
``get_orcanium_home()`` to ``~/.orcanium`` (or ``$ORCANIUM_HOME``) — never to a
repo-local ``data/`` directory.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

from orcanium.orcanium_constants import (
    display_orcanium_home,
    get_bundled_skills_dir,
    get_default_orcanium_root,
    get_optional_mcps_dir,
    get_optional_skills_dir,
    get_orcanium_dir,
    get_orcanium_home,
    get_orcanium_home_override,
    is_container,
    is_termux,
    is_wsl,
    reset_orcanium_home_override,
    set_orcanium_home_override,
    secure_parent_dir,
    OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)


# ── URL / proxy utilities ───────────────────────────────────────

_safe_schemes = {"http", "https", "ftp", "sftp", "git", "ssh"}
_TRUTHY_VALUES = {"true", "1", "yes", "y", "on", "enabled", "enable"}


def is_truthy_value(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in _TRUTHY_VALUES
    return bool(val)


def normalize_proxy_url(url: str) -> str:
    return url


def is_safe_url(url: str, allowed_domains: list = None) -> bool:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme and parsed.scheme not in _safe_schemes:
            return False
        if allowed_domains and parsed.hostname:
            return any(d in parsed.hostname for d in allowed_domains)
        return True
    except Exception:
        return False


def to_agent_visible_cache_path(path: str) -> str:
    return path


def atomic_replace(src: str, dst: str) -> None:
    import shutil
    shutil.move(src, dst)


def atomic_json_write(path, data, indent=None):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(str(path)) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


# ── Tool / Display stubs ────────────────────────────────────────


def mark_awaiting_text(agent_name, chat_id, clarify_id):
    pass


def get_tool_emoji(tool_name: str) -> str:
    emoji_map = {"web_search": "🌐", "fetch_url": "📄", "memory_tool": "🧠", "session_search": "🔍"}
    return emoji_map.get(tool_name, "🔧")


def text_to_speech_tool(text, **kwargs) -> str:
    return ""


def check_tts_requirements(**kwargs):
    return False, "TTS not configured"


def parse_reasoning_effort(effort: str) -> dict | None:
    """Parse reasoning effort level into a config dict."""
    if not effort or not effort.strip():
        return None
    effort = effort.strip().lower()
    valid = {"none", "minimal", "low", "medium", "high", "xhigh"}
    if effort not in valid:
        return None
    if effort == "none":
        return {"enabled": False}
    return {"enabled": True, "effort": effort}


# OpenRouter API endpoints used across CLI tools
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = f"{OPENROUTER_BASE_URL}/models"
