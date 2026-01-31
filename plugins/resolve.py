"""DaVinci Resolve Plugin - Control Resolve via Python API."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


class ResolvePlugin(BasePlugin):
    """Plugin for DaVinci Resolve integration.

    Requires DaVinci Resolve to be running with scripting enabled.
    Uses the DaVinciResolveScript module from Resolve's installation.
    """

    name = "resolve"
    description = "DaVinci Resolve integration - media pool, timelines, projects"
    actions = ["add_to_media_pool", "create_timeline", "get_current_project", "ping"]

    @property
    def platform_supported(self) -> List[str]:
        return ["windows", "darwin"]

    def __init__(self):
        self._resolve = None
        self._connect()

    def _connect(self):
        """Connect to running Resolve instance."""
        try:
            import DaVinciResolveScript as dvr
            self._resolve = dvr.scriptapp("Resolve")
        except ImportError:
            self._resolve = None
        except Exception:
            self._resolve = None

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        schemas = {
            "add_to_media_pool": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to import",
                    },
                },
                "required": ["files"],
            },
            "create_timeline": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the new timeline",
                        "default": "New Timeline",
                    },
                },
            },
            "get_current_project": {
                "type": "object",
                "properties": {},
            },
            "ping": {
                "type": "object",
                "properties": {},
            },
        }
        return schemas.get(action)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Resolve action."""
        if action == "ping":
            return {"available": self._resolve is not None}

        if not self._resolve:
            # Try to reconnect
            self._connect()
            if not self._resolve:
                raise RuntimeError("DaVinci Resolve not available. Is it running?")

        if action == "add_to_media_pool":
            return await self._add_to_media_pool(params)
        elif action == "create_timeline":
            return await self._create_timeline(params)
        elif action == "get_current_project":
            return await self._get_current_project()
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _get_current_project(self) -> Dict[str, Any]:
        """Get info about current project."""
        pm = self._resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            raise RuntimeError("No project open")

        return {
            "name": project.GetName(),
            "timeline_count": project.GetTimelineCount(),
        }

    async def _add_to_media_pool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add files to the media pool."""
        files = params.get("files", [])
        if not files:
            raise ValueError("files list is required")

        pm = self._resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            raise RuntimeError("No project open")

        media_pool = project.GetMediaPool()

        # Import files
        imported = media_pool.ImportMedia(files)

        return {
            "imported_count": len(imported) if imported else 0,
            "files": files,
        }

    async def _create_timeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new timeline."""
        name = params.get("name", "New Timeline")

        pm = self._resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            raise RuntimeError("No project open")

        media_pool = project.GetMediaPool()
        timeline = media_pool.CreateEmptyTimeline(name)

        if not timeline:
            raise RuntimeError("Failed to create timeline")

        return {
            "name": timeline.GetName(),
            "created": True,
        }
