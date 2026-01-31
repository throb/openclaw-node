"""Plugin discovery and loading."""

import importlib
import logging
import platform
from typing import Dict, List, Optional

from plugins import PLUGINS
from plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers and loads plugins from the plugins package."""

    def __init__(self):
        self._platform = platform.system().lower()

    def load_all(self, enabled_plugins: List[str]) -> Dict[str, BasePlugin]:
        """Load all enabled plugins.

        Args:
            enabled_plugins: List of plugin names to load

        Returns:
            Dict mapping plugin names to plugin instances
        """
        loaded = {}

        for plugin_name in enabled_plugins:
            try:
                plugin = self._load_plugin(plugin_name)
                if plugin:
                    # Check platform support
                    if self._platform not in plugin.platform_supported:
                        logger.warning(
                            f"Plugin {plugin_name} does not support {self._platform}, skipping"
                        )
                        continue

                    loaded[plugin_name] = plugin
                    logger.info(
                        f"Loaded plugin: {plugin_name} "
                        f"(actions: {plugin.actions})"
                    )
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")

        return loaded

    def _load_plugin(self, name: str) -> Optional[BasePlugin]:
        """Load a single plugin by name.

        Args:
            name: Plugin name (e.g., 'explorer', 'rv')

        Returns:
            Plugin instance or None if not found
        """
        # Try the registry first
        if name in PLUGINS:
            plugin_class = PLUGINS[name]
            return plugin_class()

        # Fallback: try to import dynamically
        try:
            module = importlib.import_module(f"plugins.{name}")

            # Find the plugin class (convention: NamePlugin)
            class_name = f"{name.title()}Plugin"
            if hasattr(module, class_name):
                plugin_class = getattr(module, class_name)
                return plugin_class()

            # Fallback: look for any BasePlugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr != BasePlugin
                ):
                    return attr()

            logger.warning(f"No plugin class found in {name}")
            return None

        except ImportError as e:
            logger.error(f"Could not import plugin {name}: {e}")
            return None

    def list_available(self) -> List[str]:
        """List all available plugin names."""
        return list(PLUGINS.keys())

    def get_plugin_info(self, name: str) -> Optional[Dict]:
        """Get info about a plugin without loading it.

        Args:
            name: Plugin name

        Returns:
            Plugin info dict or None if not found
        """
        if name not in PLUGINS:
            return None

        plugin_class = PLUGINS[name]

        # Create temporary instance to get info
        try:
            plugin = plugin_class()
            return plugin.get_info()
        except Exception as e:
            logger.error(f"Error getting plugin info for {name}: {e}")
            return None
