"""WebSocket client with auto-reconnection and heartbeat."""

import asyncio
import json
import logging
import platform
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class NodeClient:
    """WebSocket client that connects to the OpenClaw server."""

    def __init__(
        self,
        server_url: str,
        node_id: str,
        auth_token: str,
        plugins: Dict[str, Any],
        platform_name: Optional[str] = None,
        heartbeat_interval: int = 30,
    ):
        self.server_url = server_url
        self.node_id = node_id
        self.auth_token = auth_token
        self.plugins = plugins
        self.platform_name = platform_name or platform.system().lower()
        self.heartbeat_interval = heartbeat_interval

        self._reconnect_delay = 1  # seconds, with exponential backoff
        self._max_reconnect_delay = 60
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def run(self):
        """Main loop with auto-reconnection."""
        self._running = True

        while self._running:
            try:
                await self._connect_and_listen()
            except ConnectionClosed as e:
                logger.warning(f"Connection closed (code={e.code}): {e.reason}")
                if e.code == 4001:
                    logger.error("Authentication failed. Check your token.")
                    break
            except ConnectionRefusedError:
                logger.warning(f"Connection refused. Is the server running?")
            except Exception as e:
                logger.error(f"Connection error: {e}")

            if not self._running:
                break

            logger.info(f"Reconnecting in {self._reconnect_delay}s...")
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def stop(self):
        """Stop the client gracefully."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()

    async def _connect_and_listen(self):
        """Connect to server and handle messages."""
        # Build URL with node_id
        url = f"{self.server_url}/{self.node_id}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        async with websockets.connect(url, additional_headers=headers) as ws:
            self._ws = ws
            logger.info(f"Connected to {self.server_url}")
            self._reconnect_delay = 1  # Reset on successful connection

            # Send registration
            await ws.send(json.dumps({
                "type": "register",
                "node_id": self.node_id,
                "plugins": list(self.plugins.keys()),
                "platform": self.platform_name,
            }))

            # Wait for registration acknowledgment
            ack = await ws.recv()
            ack_data = json.loads(ack)
            if ack_data.get("type") == "registered":
                logger.info(f"Registration confirmed: {ack_data.get('node_id')}")
            else:
                logger.warning(f"Unexpected registration response: {ack_data}")

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

            try:
                # Listen for commands
                async for message in ws:
                    response = await self._handle_message(json.loads(message))
                    if response:
                        await ws.send(json.dumps(response))
            finally:
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    try:
                        await self._heartbeat_task
                    except asyncio.CancelledError:
                        pass

    async def _heartbeat_loop(self, ws: websockets.WebSocketClientProtocol):
        """Send periodic heartbeat messages."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await ws.send(json.dumps({"type": "heartbeat"}))
                logger.debug("Sent heartbeat")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _handle_message(self, msg: dict) -> Optional[dict]:
        """Handle incoming command and return response."""
        msg_type = msg.get("type")

        # Ignore non-command messages
        if msg_type in ("registered", "heartbeat_ack"):
            return None

        cmd_id = msg.get("id", "unknown")
        action = msg.get("action", "")
        params = msg.get("params", {})

        # Parse action: "plugin.action_name"
        if "." not in action:
            return {
                "id": cmd_id,
                "status": "error",
                "error": f"Invalid action format: {action}. Expected 'plugin.action'",
            }

        plugin_name, action_name = action.split(".", 1)

        if plugin_name not in self.plugins:
            return {
                "id": cmd_id,
                "status": "error",
                "error": f"Plugin not available: {plugin_name}",
            }

        plugin = self.plugins[plugin_name]

        if action_name not in plugin.actions:
            return {
                "id": cmd_id,
                "status": "error",
                "error": f"Action not available: {action_name}. Available: {plugin.actions}",
            }

        try:
            logger.info(f"Executing {action} with params: {params}")
            result = await plugin.execute(action_name, params)
            return {"id": cmd_id, "status": "success", "result": result}
        except Exception as e:
            logger.exception(f"Error executing {action}")
            return {"id": cmd_id, "status": "error", "error": str(e)}
