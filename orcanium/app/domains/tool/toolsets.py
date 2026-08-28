"""Toolset definitions — named groups of tools for the agent."""

from typing import Dict, List, Optional

from orcanium.app.tools.registry import registry

# ── Core built-in toolsets ─────────────────────────────────────

_CORE_TOOLS = [
    "read_file",
    "write_file",
    "fetch_url",
    "calculator",
]

_MEMORY_TOOLS = [
    "memory_read",
    "memory_add",
    "memory_replace",
    "memory_remove",
]

_TOOLSETS: Dict[str, List[str]] = {
    "core": _CORE_TOOLS,
    "memory": _MEMORY_TOOLS,
    "files": ["read_file", "write_file"],
    "web": ["fetch_url"],
    "all": _CORE_TOOLS + _MEMORY_TOOLS,
}

# ── Resolution ─────────────────────────────────────────────────


def resolve_toolset(name: str) -> List[str]:
    """Resolve a toolset name to its list of tool names."""
    if name in _TOOLSETS:
        return _TOOLSETS[name]
    # If it's a single tool name, return as-is
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

    # Collect all enabled tool names
    tool_names: List[str] = []
    for ts in enabled:
        tool_names.extend(resolve_toolset(ts))

    # Remove disabled
    for ts in disabled:
        for name in resolve_toolset(ts):
            if name in tool_names:
                tool_names.remove(name)

    # Deduplicate
    tool_names = list(dict.fromkeys(tool_names))

    return registry.get_definitions(tool_names)
