"""Plugin Manager — lightweight plugin registration and lifecycle."""

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin registration, loading, and lifecycle."""

    def __init__(self):
        self._plugins: Dict[str, Dict[str, Any]] = {}
        self._plugin_dirs: List[Path] = []

    def register(self, name: str, plugin: Dict[str, Any]) -> None:
        """Register a plugin."""
        self._plugins[name] = plugin
        logger.info(f"Plugin registered: {name}")

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        self._plugins.pop(name, None)
        logger.info(f"Plugin unregistered: {name}")

    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def discover_plugins(self, directory: Optional[str] = None) -> int:
        """Discover and load plugins from a directory."""
        if directory:
            self._plugin_dirs.append(Path(directory))

        count = 0
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for f in plugin_dir.glob("*.py"):
                if f.name.startswith("_"):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(f.stem, f)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        count += 1
                except Exception as e:
                    logger.warning(f"Failed to load plugin {f.name}: {e}")

        return count

    @property
    def count(self) -> int:
        return len(self._plugins)


plugin_manager = PluginManager()
