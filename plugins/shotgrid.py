"""ShotGrid Plugin - Integration with Autodesk ShotGrid (formerly Shotgun)."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


class ShotgridPlugin(BasePlugin):
    """Plugin for ShotGrid/Shotgun integration.

    Requires shotgun_api3 package and valid credentials.
    Credentials can be configured via environment variables:
    - SHOTGRID_URL: Site URL (e.g., https://studio.shotgunstudio.com)
    - SHOTGRID_SCRIPT_NAME: API script name
    - SHOTGRID_API_KEY: API key

    Or via config file at ~/.shotgrid/credentials.yaml
    """

    name = "shotgrid"
    description = "ShotGrid integration - publish, status updates, queries"
    actions = ["publish_version", "update_task_status", "get_shot_info", "ping"]

    @property
    def platform_supported(self) -> List[str]:
        return ["windows", "darwin", "linux"]

    def __init__(self):
        self._sg = None
        self._connect()

    def _connect(self) -> None:
        """Connect to ShotGrid using credentials."""
        try:
            import shotgun_api3
        except ImportError:
            return

        # Try environment variables first
        url = os.environ.get("SHOTGRID_URL")
        script_name = os.environ.get("SHOTGRID_SCRIPT_NAME")
        api_key = os.environ.get("SHOTGRID_API_KEY")

        # Try config file if env vars not set
        if not all([url, script_name, api_key]):
            creds = self._load_credentials_file()
            if creds:
                url = url or creds.get("url")
                script_name = script_name or creds.get("script_name")
                api_key = api_key or creds.get("api_key")

        if not all([url, script_name, api_key]):
            return

        try:
            self._sg = shotgun_api3.Shotgun(
                url,
                script_name=script_name,
                api_key=api_key,
            )
        except Exception:
            self._sg = None

    def _load_credentials_file(self) -> Optional[Dict[str, str]]:
        """Load credentials from config file."""
        config_paths = [
            Path.home() / ".shotgrid" / "credentials.yaml",
            Path.home() / ".shotgun" / "credentials.yaml",
        ]

        for path in config_paths:
            if path.exists():
                try:
                    import yaml
                    with open(path) as f:
                        return yaml.safe_load(f)
                except Exception:
                    continue

        return None

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        schemas = {
            "publish_version": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "ShotGrid project ID",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (Shot, Asset, etc.)",
                        "default": "Shot",
                    },
                    "entity_id": {
                        "type": "integer",
                        "description": "Entity ID",
                    },
                    "code": {
                        "type": "string",
                        "description": "Version code/name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Version description",
                    },
                    "path_to_movie": {
                        "type": "string",
                        "description": "Path to media file for upload",
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID to link version to (optional)",
                    },
                },
                "required": ["project_id", "entity_id", "code"],
            },
            "update_task_status": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID to update",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status code (e.g., 'ip', 'fin', 'wtg')",
                    },
                },
                "required": ["task_id", "status"],
            },
            "get_shot_info": {
                "type": "object",
                "properties": {
                    "shot_id": {
                        "type": "integer",
                        "description": "Shot ID",
                    },
                    "shot_code": {
                        "type": "string",
                        "description": "Shot code (alternative to shot_id)",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID (required if using shot_code)",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to return (optional)",
                    },
                },
            },
            "ping": {
                "type": "object",
                "properties": {},
            },
        }
        return schemas.get(action)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a ShotGrid action."""
        if action == "ping":
            return {
                "available": self._sg is not None,
                "connected": self._sg is not None,
            }

        if not self._sg:
            # Try to reconnect
            self._connect()
            if not self._sg:
                raise RuntimeError(
                    "ShotGrid not connected. Check credentials in environment "
                    "variables (SHOTGRID_URL, SHOTGRID_SCRIPT_NAME, SHOTGRID_API_KEY) "
                    "or config file (~/.shotgrid/credentials.yaml)"
                )

        if action == "publish_version":
            return await self._publish_version(params)
        elif action == "update_task_status":
            return await self._update_task_status(params)
        elif action == "get_shot_info":
            return await self._get_shot_info(params)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _publish_version(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Version in ShotGrid."""
        project_id = params.get("project_id")
        entity_type = params.get("entity_type", "Shot")
        entity_id = params.get("entity_id")
        code = params.get("code")
        description = params.get("description", "")
        path_to_movie = params.get("path_to_movie")
        task_id = params.get("task_id")

        if not all([project_id, entity_id, code]):
            raise ValueError("project_id, entity_id, and code are required")

        # Build version data
        data = {
            "project": {"type": "Project", "id": project_id},
            "code": code,
            "description": description,
            "entity": {"type": entity_type, "id": entity_id},
        }

        if task_id:
            data["sg_task"] = {"type": "Task", "id": task_id}

        # Create the version
        version = self._sg.create("Version", data)

        # Upload media if provided
        if path_to_movie and Path(path_to_movie).exists():
            self._sg.upload(
                "Version",
                version["id"],
                path_to_movie,
                field_name="sg_uploaded_movie",
            )
            version["uploaded_movie"] = path_to_movie

        return {
            "version_id": version["id"],
            "code": version["code"],
            "entity": {"type": entity_type, "id": entity_id},
            "created": True,
        }

    async def _update_task_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update a Task's status."""
        task_id = params.get("task_id")
        status = params.get("status")

        if not task_id or not status:
            raise ValueError("task_id and status are required")

        # Update the task
        self._sg.update("Task", task_id, {"sg_status_list": status})

        # Get updated task info
        task = self._sg.find_one(
            "Task",
            [["id", "is", task_id]],
            ["content", "sg_status_list", "entity"],
        )

        return {
            "task_id": task_id,
            "status": status,
            "task_name": task.get("content") if task else None,
            "updated": True,
        }

    async def _get_shot_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a Shot."""
        shot_id = params.get("shot_id")
        shot_code = params.get("shot_code")
        project_id = params.get("project_id")
        fields = params.get("fields", [
            "code",
            "description",
            "sg_status_list",
            "sg_cut_in",
            "sg_cut_out",
            "sg_sequence",
            "tasks",
        ])

        if not shot_id and not shot_code:
            raise ValueError("Either shot_id or shot_code is required")

        # Build filters
        filters = []
        if shot_id:
            filters.append(["id", "is", shot_id])
        else:
            if not project_id:
                raise ValueError("project_id is required when using shot_code")
            filters.append(["code", "is", shot_code])
            filters.append(["project", "is", {"type": "Project", "id": project_id}])

        shot = self._sg.find_one("Shot", filters, fields)

        if not shot:
            raise ValueError(f"Shot not found: {shot_id or shot_code}")

        return {
            "shot": shot,
            "found": True,
        }
