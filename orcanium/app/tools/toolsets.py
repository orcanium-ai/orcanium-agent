"""Toolset definitions — named groups of tools for the Orcanium agent.

Each toolset is a named list of tool names that the agent can use.
Tools are registered via ``registry.register()`` in their respective modules.
"""

from typing import Dict, List, Optional

from orcanium.app.tools.registry import registry

# ── Core tools (always available) ───────────────────────────────

_CORE_TOOLS = [
    "read_file",
    "write_file",
    "fetch_url",
    "web_search",
    "web_extract",
    "calculator",
    "memory",
    "session_search",
]

# ── File operations ─────────────────────────────────────────────

_FILE_TOOLS = [
    "read_file",
    "write_file",
    "patch",
    "search_files",
]

# ── Web / Browser ───────────────────────────────────────────────

_WEB_TOOLS = [
    "fetch_url",
    "web_search",
    "web_extract",
]
_BROWSER_TOOLS = [
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_scroll",
    "browser_back",
    "browser_press",
    "browser_get_images",
    "browser_vision",
    "browser_console",
    "browser_cdp",
    "browser_dialog",
]

# ── Terminal / Code ─────────────────────────────────────────────

_TERMINAL_TOOLS = [
    "terminal",
    "execute_code",
    "process",
    "read_terminal",
]

# ── Skills ──────────────────────────────────────────────────────

_SKILL_TOOLS = [
    "skill_manage",
    "skills_list",
    "skill_view",
]

# ── Memory / Knowledge ──────────────────────────────────────────

_MEMORY_TOOLS = [
    "memory",
    "session_search",
]

# ── Communication ───────────────────────────────────────────────

_COMM_TOOLS = [
    "send_message",
    "discord",
    "discord_admin",
]

# ── Vision / Media ──────────────────────────────────────────────

_VISION_TOOLS = [
    "vision_analyze",
    "video_analyze",
]

_GENERATION_TOOLS = [
    "image_generate",
    "video_generate",
    "text_to_speech",
]

# ── Task / Productivity ─────────────────────────────────────────

_TASK_TOOLS = [
    "todo",
    "cronjob",
    "delegate_task",
    "cross_talk",
    "clarify",
    "kanban_show",
    "kanban_list",
    "kanban_complete",
    "kanban_block",
    "kanban_heartbeat",
    "kanban_comment",
    "kanban_create",
    "kanban_unblock",
    "kanban_link",
]

# ── Full toolset registry ───────────────────────────────────────

_TOOLSETS: Dict[str, List[str]] = {
    "core": _CORE_TOOLS,
    "files": _FILE_TOOLS,
    "web": _WEB_TOOLS,
    "browser": _BROWSER_TOOLS,
    "terminal": _TERMINAL_TOOLS,
    "code": _TERMINAL_TOOLS,
    "memory": _MEMORY_TOOLS,
    "skills": _SKILL_TOOLS,
    "communication": _COMM_TOOLS,
    "vision": _VISION_TOOLS,
    "media": _VISION_TOOLS + _GENERATION_TOOLS,
    "generation": _GENERATION_TOOLS,
    "tasks": _TASK_TOOLS,
    "kanban": [n for n in sum([v for k, v in _TOOLSETS.items()], []) if n.startswith("kanban_")] if False else _TASK_TOOLS,
    # Composite toolsets
    "editor": _FILE_TOOLS + _TERMINAL_TOOLS + ["web_search", "web_extract"],
    "developer": _FILE_TOOLS + _TERMINAL_TOOLS + _WEB_TOOLS + _SKILL_TOOLS,
    "all": sorted(set(
        _CORE_TOOLS + _FILE_TOOLS + _WEB_TOOLS + _BROWSER_TOOLS +
        _TERMINAL_TOOLS + _SKILL_TOOLS + _MEMORY_TOOLS +
        _COMM_TOOLS + _VISION_TOOLS + _GENERATION_TOOLS +
        _TASK_TOOLS + ["mixture_of_agents", "computer_use", "x_search",
                       "ha_list_entities", "ha_get_state", "ha_list_services", "ha_call_service",
                       "discord", "discord_admin", "todo", "cronjob"]
    )),
}

# Fix kanban toolset properly
_TOOLSETS["kanban"] = [
    "kanban_show", "kanban_list", "kanban_complete", "kanban_block",
    "kanban_heartbeat", "kanban_comment", "kanban_create", "kanban_unblock", "kanban_link",
]


# ── Resolution ──────────────────────────────────────────────────


def resolve_toolset(name: str) -> List[str]:
    """Resolve a toolset name to its list of tool names."""
    if name in _TOOLSETS:
        return _TOOLSETS[name]
    if name in registry.tool_names:
        return [name]
    return []


def get_tool_definitions(
    enabled_toolsets: Optional[List[str]] = None,
    disabled_toolsets: Optional[List[str]] = None,
) -> List[Dict]:
    """Get OpenAI-format tool definitions for enabled toolsets minus disabled ones."""
    enabled = enabled_toolsets or ["core"]
    disabled = disabled_toolsets or []

    tool_names: List[str] = []
    for ts in enabled:
        tool_names.extend(resolve_toolset(ts))

    for ts in disabled:
        for name in resolve_toolset(ts):
            if name in tool_names:
                tool_names.remove(name)

    tool_names = list(dict.fromkeys(tool_names))
    return registry.get_definitions(tool_names)
