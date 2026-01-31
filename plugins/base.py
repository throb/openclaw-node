"""Base plugin class for OpenClaw Node."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BasePlugin(ABC):
    """Base class for all OpenClaw Node plugins.

    Subclass this to create a new plugin:

        class MyPlugin(BasePlugin):
            name = "myplugin"
            description = "My plugin description"
            actions = ["do_thing", "do_other"]

            async def execute(self, action: str, params: dict) -> dict:
                if action == "do_thing":
                    return {"result": "done"}
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier (e.g., 'rv', 'resolve').

        Used in action routing: "plugin_name.action_name"
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for UI/docs."""
        ...

    @property
    @abstractmethod
    def actions(self) -> List[str]:
        """List of available action names.

        Only actions listed here can be executed.
        """
        ...

    @property
    def platform_supported(self) -> List[str]:
        """Platforms this plugin works on.

        Returns list of: 'windows', 'darwin', 'linux'
        Default: all platforms.
        """
        return ["windows", "darwin", "linux"]

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        """Return JSON Schema for action parameters.

        Override to provide schema for specific actions.
        Used for validation and documentation generation.

        Args:
            action: Action name

        Returns:
            JSON Schema dict, or None if no schema defined

        Example:
            def get_action_schema(self, action: str) -> dict:
                if action == "open_file":
                    return {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to open"},
                        },
                        "required": ["path"],
                    }
                return None
        """
        return None

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action with given parameters.

        Args:
            action: Action name (will be in self.actions)
            params: Parameters from the command

        Returns:
            Result dict to send back to server

        Raises:
            Exception: On execution error (will be caught and sent as error response)
        """
        ...

    def validate_params(self, action: str, params: Dict[str, Any]) -> bool:
        """Optional: Validate parameters before execution.

        Override to add custom validation.
        """
        return True

    def get_info(self) -> Dict[str, Any]:
        """Get plugin info for registration/discovery."""
        return {
            "name": self.name,
            "description": self.description,
            "actions": self.actions,
            "platform_supported": self.platform_supported,
        }
