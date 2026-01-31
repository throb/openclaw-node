"""RV Viewer Plugin - Open playlists and media in RV."""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


class RvPlugin(BasePlugin):
    """Plugin for controlling RV media player."""

    name = "rv"
    description = "Control RV media player - open sessions and sources"
    actions = ["open_session", "open_sources", "ping"]

    @property
    def platform_supported(self) -> List[str]:
        return ["windows", "darwin", "linux"]

    def __init__(self):
        self._rv_path = self._find_rv()

    def _find_rv(self) -> str:
        """Find RV executable."""
        candidates = [
            "rv",  # In PATH
            "/usr/local/bin/rv",
            "/Applications/RV.app/Contents/MacOS/RV",
            r"C:\Program Files\RV\bin\rv.exe",
            r"C:\Program Files\Shotgun\RV-2024\bin\rv.exe",
        ]

        for path in candidates:
            if shutil.which(path):
                return path

        return "rv"  # Hope it's in PATH

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        schemas = {
            "open_session": {
                "type": "object",
                "properties": {
                    "session_file": {
                        "type": "string",
                        "description": "Path to .rv session file",
                    },
                },
                "required": ["session_file"],
            },
            "open_sources": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of media file paths to open",
                    },
                },
                "required": ["sources"],
            },
            "ping": {
                "type": "object",
                "properties": {},
            },
        }
        return schemas.get(action)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an RV action."""
        if action == "open_session":
            return await self._open_session(params)
        elif action == "open_sources":
            return await self._open_sources(params)
        elif action == "ping":
            return {"available": True, "rv_path": self._rv_path}
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _open_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open an RV session file (.rv)."""
        session_file = params.get("session_file")
        if not session_file:
            raise ValueError("session_file is required")

        path = Path(session_file)
        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")

        proc = subprocess.Popen([self._rv_path, str(path)])
        return {"pid": proc.pid, "session_file": str(path)}

    async def _open_sources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open multiple source files in RV."""
        sources = params.get("sources", [])
        if not sources:
            raise ValueError("sources list is required")

        # Validate paths exist
        valid_sources = []
        for src in sources:
            path = Path(src)
            if path.exists():
                valid_sources.append(str(path))

        if not valid_sources:
            raise ValueError("No valid source files found")

        proc = subprocess.Popen([self._rv_path] + valid_sources)
        return {"pid": proc.pid, "sources": valid_sources, "count": len(valid_sources)}
