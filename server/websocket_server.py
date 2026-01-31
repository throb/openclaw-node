"""WebSocket server for node connections."""

import asyncio
import logging
from typing import Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NodeWebSocketServer:
    """Manages WebSocket connections from OpenClaw nodes."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, node_id: str) -> None:
        """Register a new node connection.

        Note: websocket.accept() should be called before this.
        """
        async with self._lock:
            # Disconnect existing connection with same ID
            if node_id in self._connections:
                old_ws = self._connections[node_id]
                try:
                    await old_ws.close(code=4000, reason="Replaced by new connection")
                except Exception:
                    pass
                logger.warning(f"Replaced existing connection for node: {node_id}")

            self._connections[node_id] = websocket
            logger.info(f"Node connected: {node_id}")

    async def disconnect(self, node_id: str) -> None:
        """Remove a node connection."""
        async with self._lock:
            if node_id in self._connections:
                del self._connections[node_id]
                logger.info(f"Node disconnected: {node_id}")

    async def send(self, node_id: str, message: dict) -> None:
        """Send a message to a specific node.

        Args:
            node_id: Target node identifier
            message: Message dict to send as JSON

        Raises:
            ValueError: If node is not connected
        """
        ws = self._connections.get(node_id)
        if not ws:
            raise ValueError(f"Node not connected: {node_id}")

        await ws.send_json(message)

    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> int:
        """Send a message to all connected nodes.

        Args:
            message: Message to broadcast
            exclude: Optional node_id to exclude from broadcast

        Returns:
            Number of nodes message was sent to
        """
        sent = 0
        for node_id, ws in list(self._connections.items()):
            if node_id == exclude:
                continue
            try:
                await ws.send_json(message)
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send to {node_id}: {e}")
        return sent

    def is_connected(self, node_id: str) -> bool:
        """Check if a node is connected."""
        return node_id in self._connections

    def list_nodes(self) -> list:
        """Return list of connected node IDs."""
        return list(self._connections.keys())

    @property
    def connection_count(self) -> int:
        """Number of connected nodes."""
        return len(self._connections)
