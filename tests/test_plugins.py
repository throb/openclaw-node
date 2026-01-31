"""Tests for plugins."""

import pytest

from plugins.base import BasePlugin
from plugins.explorer import ExplorerPlugin


class TestBasePlugin:
    """Tests for BasePlugin interface."""

    def test_cannot_instantiate(self):
        """Cannot instantiate abstract BasePlugin."""
        with pytest.raises(TypeError):
            BasePlugin()


class TestExplorerPlugin:
    """Tests for ExplorerPlugin."""

    @pytest.fixture
    def plugin(self):
        """Create plugin instance."""
        return ExplorerPlugin()

    def test_name(self, plugin):
        """Plugin has correct name."""
        assert plugin.name == "explorer"

    def test_description(self, plugin):
        """Plugin has description."""
        assert plugin.description
        assert len(plugin.description) > 0

    def test_actions(self, plugin):
        """Plugin has expected actions."""
        assert "open_folder" in plugin.actions
        assert "reveal_file" in plugin.actions
        assert "ping" in plugin.actions

    def test_platform_supported(self, plugin):
        """Plugin supports all platforms."""
        assert "windows" in plugin.platform_supported
        assert "darwin" in plugin.platform_supported
        assert "linux" in plugin.platform_supported

    def test_get_action_schema(self, plugin):
        """Plugin returns schemas for actions."""
        schema = plugin.get_action_schema("open_folder")
        assert schema is not None
        assert schema["type"] == "object"
        assert "path" in schema["properties"]

        # Unknown action returns None
        assert plugin.get_action_schema("unknown") is None

    def test_get_info(self, plugin):
        """Plugin get_info returns correct data."""
        info = plugin.get_info()
        assert info["name"] == "explorer"
        assert info["description"]
        assert info["actions"] == plugin.actions
        assert info["platform_supported"] == plugin.platform_supported

    @pytest.mark.asyncio
    async def test_ping(self, plugin):
        """Ping action returns availability."""
        result = await plugin.execute("ping", {})
        assert result["available"] is True
        assert "platform" in result

    @pytest.mark.asyncio
    async def test_open_folder_missing_path(self, plugin):
        """open_folder raises on missing path."""
        with pytest.raises(ValueError, match="path is required"):
            await plugin.execute("open_folder", {})

    @pytest.mark.asyncio
    async def test_reveal_file_missing_path(self, plugin):
        """reveal_file raises on missing path."""
        with pytest.raises(ValueError, match="path is required"):
            await plugin.execute("reveal_file", {})

    @pytest.mark.asyncio
    async def test_reveal_file_not_found(self, plugin):
        """reveal_file raises on non-existent file."""
        with pytest.raises(FileNotFoundError):
            await plugin.execute("reveal_file", {"path": "/nonexistent/file.txt"})

    @pytest.mark.asyncio
    async def test_unknown_action(self, plugin):
        """Unknown action raises ValueError."""
        with pytest.raises(ValueError, match="Unknown action"):
            await plugin.execute("unknown_action", {})


class TestPluginRegistry:
    """Tests for plugin registry."""

    def test_all_plugins_registered(self):
        """All plugins are in the registry."""
        from plugins import PLUGINS

        assert "explorer" in PLUGINS
        assert "rv" in PLUGINS
        assert "resolve" in PLUGINS
        assert "nuke" in PLUGINS
        assert "shotgrid" in PLUGINS

    def test_plugins_are_classes(self):
        """Registry contains plugin classes."""
        from plugins import PLUGINS
        from plugins.base import BasePlugin

        for name, cls in PLUGINS.items():
            assert issubclass(cls, BasePlugin), f"{name} is not a BasePlugin subclass"
