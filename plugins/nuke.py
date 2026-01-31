"""Nuke Plugin - Control Nuke compositing software."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


class NukePlugin(BasePlugin):
    """Plugin for controlling Nuke compositing software.

    Supports rendering, opening scripts, and querying Nuke info.
    Works in both GUI and command-line modes.
    """

    name = "nuke"
    description = "Control Nuke - render, open scripts, get info"
    actions = ["render_write", "open_script", "get_info", "ping"]

    @property
    def platform_supported(self) -> List[str]:
        return ["windows", "darwin", "linux"]

    def __init__(self):
        self._nuke_path = self._find_nuke()

    def _find_nuke(self) -> Optional[str]:
        """Find Nuke executable."""
        candidates = [
            "nuke",  # In PATH
            "Nuke15.0",
            "Nuke14.0",
            "Nuke13.0",
        ]

        # Platform-specific paths
        import platform
        system = platform.system()

        if system == "Windows":
            candidates.extend([
                r"C:\Program Files\Nuke15.0v1\Nuke15.0.exe",
                r"C:\Program Files\Nuke14.0v6\Nuke14.0.exe",
                r"C:\Program Files\Nuke13.2v8\Nuke13.2.exe",
            ])
        elif system == "Darwin":
            candidates.extend([
                "/Applications/Nuke15.0v1/Nuke15.0v1.app/Contents/MacOS/Nuke15.0",
                "/Applications/Nuke14.0v6/Nuke14.0v6.app/Contents/MacOS/Nuke14.0",
            ])
        else:  # Linux
            candidates.extend([
                "/usr/local/Nuke15.0v1/Nuke15.0",
                "/usr/local/Nuke14.0v6/Nuke14.0",
                "/opt/Nuke15.0v1/Nuke15.0",
            ])

        for path in candidates:
            found = shutil.which(path)
            if found:
                return found
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return None

    def get_action_schema(self, action: str) -> Optional[Dict[str, Any]]:
        schemas = {
            "render_write": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Path to Nuke script (.nk file)",
                    },
                    "write_node": {
                        "type": "string",
                        "description": "Name of Write node to render (optional, renders all if not specified)",
                    },
                    "frame_range": {
                        "type": "string",
                        "description": "Frame range to render (e.g., '1-100' or '1,10,20')",
                    },
                    "threads": {
                        "type": "integer",
                        "description": "Number of render threads",
                        "default": 0,
                    },
                },
                "required": ["script"],
            },
            "open_script": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Path to Nuke script (.nk file)",
                    },
                    "gui": {
                        "type": "boolean",
                        "description": "Open in GUI mode (default: true)",
                        "default": True,
                    },
                },
                "required": ["script"],
            },
            "get_info": {
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
        """Execute a Nuke action."""
        if action == "ping":
            return {
                "available": self._nuke_path is not None,
                "nuke_path": self._nuke_path,
            }
        elif action == "get_info":
            return await self._get_info()
        elif action == "render_write":
            return await self._render_write(params)
        elif action == "open_script":
            return await self._open_script(params)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _get_info(self) -> Dict[str, Any]:
        """Get Nuke installation info."""
        if not self._nuke_path:
            return {
                "installed": False,
                "error": "Nuke not found",
            }

        # Try to get version
        try:
            result = subprocess.run(
                [self._nuke_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_output = result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            version_output = f"Error getting version: {e}"

        return {
            "installed": True,
            "path": self._nuke_path,
            "version": version_output,
        }

    async def _render_write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Render a Write node from a Nuke script."""
        if not self._nuke_path:
            raise RuntimeError("Nuke not found")

        script = params.get("script")
        if not script:
            raise ValueError("script path is required")

        script_path = Path(script)
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script}")

        if not script_path.suffix.lower() == ".nk":
            raise ValueError(f"Not a Nuke script: {script}")

        # Build command
        cmd = [self._nuke_path, "-x"]  # -x = execute (render) mode

        # Add Write node if specified
        write_node = params.get("write_node")
        if write_node:
            cmd.extend(["-X", write_node])

        # Add frame range if specified
        frame_range = params.get("frame_range")
        if frame_range:
            cmd.extend(["-F", frame_range])

        # Add thread count if specified
        threads = params.get("threads", 0)
        if threads > 0:
            cmd.extend(["-m", str(threads)])

        cmd.append(str(script_path))

        # Run render
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return {
            "pid": proc.pid,
            "script": str(script_path),
            "write_node": write_node,
            "frame_range": frame_range,
            "command": " ".join(cmd),
        }

    async def _open_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open a Nuke script in the GUI."""
        if not self._nuke_path:
            raise RuntimeError("Nuke not found")

        script = params.get("script")
        if not script:
            raise ValueError("script path is required")

        script_path = Path(script)
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script}")

        gui = params.get("gui", True)

        cmd = [self._nuke_path]
        if not gui:
            cmd.append("-t")  # Terminal mode

        cmd.append(str(script_path))

        proc = subprocess.Popen(cmd)

        return {
            "pid": proc.pid,
            "script": str(script_path),
            "gui": gui,
        }
