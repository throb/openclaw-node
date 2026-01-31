"""Client registry for tracking connected nodes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class NodeInfo:
    """Information about a connected node."""
    node_id: str
    connected_at: datetime
    plugins: List[str] = field(default_factory=list)
    platform: str = "unknown"
    last_heartbeat: Optional[datetime] = None


class ClientRegistry:
    """Registry of connected OpenClaw nodes."""
    
    def __init__(self):
        self._nodes: Dict[str, NodeInfo] = {}
    
    def register(self, node_id: str, plugins: List[str], platform: str) -> NodeInfo:
        """Register a new node."""
        info = NodeInfo(
            node_id=node_id,
            connected_at=datetime.utcnow(),
            plugins=plugins,
            platform=platform,
        )
        self._nodes[node_id] = info
        return info
    
    def unregister(self, node_id: str):
        """Remove a node from registry."""
        self._nodes.pop(node_id, None)
    
    def get(self, node_id: str) -> Optional[NodeInfo]:
        """Get node info by ID."""
        return self._nodes.get(node_id)
    
    def list_all(self) -> List[NodeInfo]:
        """List all registered nodes."""
        return list(self._nodes.values())
    
    def find_by_plugin(self, plugin_name: str) -> List[NodeInfo]:
        """Find nodes that have a specific plugin."""
        return [n for n in self._nodes.values() if plugin_name in n.plugins]
