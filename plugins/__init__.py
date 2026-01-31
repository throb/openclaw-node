"""OpenClaw Node Plugins.

Available plugins:
- explorer: File system navigation
- rv: RV media player control
- resolve: DaVinci Resolve integration
- nuke: Nuke compositing software control
- shotgrid: ShotGrid/Shotgun integration
"""

from .base import BasePlugin
from .explorer import ExplorerPlugin
from .rv import RvPlugin
from .resolve import ResolvePlugin
from .nuke import NukePlugin
from .shotgrid import ShotgridPlugin

__all__ = [
    "BasePlugin",
    "ExplorerPlugin",
    "RvPlugin",
    "ResolvePlugin",
    "NukePlugin",
    "ShotgridPlugin",
]

# Plugin registry for easy discovery
PLUGINS = {
    "explorer": ExplorerPlugin,
    "rv": RvPlugin,
    "resolve": ResolvePlugin,
    "nuke": NukePlugin,
    "shotgrid": ShotgridPlugin,
}
