# Plugin system — extensibility for Orcanium
from orcanium.app.domains.plugin.hooks import HookRegistry, hook_registry
from orcanium.app.domains.plugin.manager import PluginManager, plugin_manager

__all__ = ["PluginManager", "plugin_manager", "HookRegistry", "hook_registry"]
