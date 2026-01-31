"""File Explorer Plugin - Open folders and reveal files (Windows/macOS/Linux)."""

import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


class ExplorerPlugin(BasePlugin):
    """Plugin for file system navigation."""

    name = "explorer"
    description = "File system navigation - open folders and reveal files"
    actions = ["open_folder", "reveal_file", "ping"]

    @property
    def platform_supported(self) -> List[str]:
        return ["windows", "darwin", "linux"]

    def __init__(self):
        self._platform = platform.system().lower()

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        schemas = {
            "open_folder": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Folder path to open",
                    },
                },
                "required": ["path"],
            },
            "reveal_file": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to reveal in file manager",
                    },
                },
                "required": ["path"],
            },
            "ping": {
                "type": "object",
                "properties": {},
            },
        }
        return schemas.get(action)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file explorer action."""
        if action == "open_folder":
            return await self._open_folder(params)
        elif action == "reveal_file":
            return await self._reveal_file(params)
        elif action == "ping":
            return {"available": True, "platform": self._platform}
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _open_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open a folder in the file manager."""
        folder = params.get("path")
        if not folder:
            raise ValueError("path is required")

        path = Path(folder)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {folder}")

        if self._platform == "windows":
            subprocess.Popen(["explorer", str(path)])
        elif self._platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

        return {"opened": str(path)}

    async def _reveal_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reveal a file in the file manager (select it)."""
        file_path = params.get("path")
        if not file_path:
            raise ValueError("path is required")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self._platform == "windows":
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif self._platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            # Linux: open parent folder
            subprocess.Popen(["xdg-open", str(path.parent)])

        return {"revealed": str(path)}
