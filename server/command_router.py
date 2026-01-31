"""Command routing with UUID tracking and timeout handling."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CommandTimeout(Exception):
    """Raised when a command times out waiting for response."""

    def __init__(self, command_id: str, action: str, timeout: float):
        self.command_id = command_id
        self.action = action
        self.timeout = timeout
        super().__init__(f"Command {action} (id={command_id}) timed out after {timeout}s")


class CommandError(Exception):
    """Raised when a command fails on the client."""

    def __init__(self, command_id: str, action: str, error: str):
        self.command_id = command_id
        self.action = action
        self.error = error
        super().__init__(f"Command {action} failed: {error}")


@dataclass
class PendingCommand:
    """Tracks a command awaiting response."""

    id: str
    action: str
    node_id: str
    future: asyncio.Future
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CommandRouter:
    """Routes commands to nodes and correlates responses.

    Handles:
    - UUID generation for command tracking
    - Response correlation using command IDs
    - Timeout handling for unresponsive nodes
    - Error serialization for client feedback
    """

    def __init__(self, default_timeout: float = 30.0):
        self._pending: Dict[str, PendingCommand] = {}
        self._default_timeout = default_timeout
        # Callback to send messages to nodes (set by websocket server)
        self._send_func: Optional[Callable] = None

    def set_send_func(self, func: Callable[[str, dict], Any]) -> None:
        """Set the function used to send messages to nodes.

        Args:
            func: Async function that takes (node_id, message_dict)
        """
        self._send_func = func

    async def dispatch(
        self,
        node_id: str,
        action: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a command to a node and await the response.

        Args:
            node_id: Target node identifier
            action: Action name (e.g., "rv.open_session")
            params: Action parameters
            timeout: Override default timeout (seconds)

        Returns:
            Response dict from the node

        Raises:
            CommandTimeout: If response not received within timeout
            CommandError: If the node returns an error
            ValueError: If node not connected or send function not set
        """
        if not self._send_func:
            raise ValueError("Send function not configured")

        timeout = timeout or self._default_timeout
        cmd_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        pending = PendingCommand(
            id=cmd_id,
            action=action,
            node_id=node_id,
            future=future,
        )
        self._pending[cmd_id] = pending

        try:
            # Send command to node
            await self._send_func(node_id, {
                "id": cmd_id,
                "action": action,
                "params": params,
            })

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)

            # Check for error response
            if result.get("status") == "error":
                raise CommandError(cmd_id, action, result.get("error", "Unknown error"))

            return result

        except asyncio.TimeoutError:
            raise CommandTimeout(cmd_id, action, timeout)

        finally:
            self._pending.pop(cmd_id, None)

    async def handle_response(self, message: Dict[str, Any]) -> bool:
        """Handle an incoming response message from a node.

        Args:
            message: Response message with 'id' field

        Returns:
            True if response was matched to a pending command
        """
        cmd_id = message.get("id")
        if not cmd_id:
            logger.warning("Received response without command ID")
            return False

        pending = self._pending.get(cmd_id)
        if not pending:
            logger.warning(f"Received response for unknown command: {cmd_id}")
            return False

        if not pending.future.done():
            pending.future.set_result(message)
            return True

        return False

    def cancel_pending(self, node_id: str) -> int:
        """Cancel all pending commands for a disconnected node.

        Args:
            node_id: The disconnected node's ID

        Returns:
            Number of commands cancelled
        """
        cancelled = 0
        to_remove = []

        for cmd_id, pending in self._pending.items():
            if pending.node_id == node_id:
                if not pending.future.done():
                    pending.future.set_exception(
                        ConnectionError(f"Node {node_id} disconnected")
                    )
                to_remove.append(cmd_id)
                cancelled += 1

        for cmd_id in to_remove:
            self._pending.pop(cmd_id, None)

        return cancelled

    @property
    def pending_count(self) -> int:
        """Number of commands awaiting response."""
        return len(self._pending)

    def get_pending_for_node(self, node_id: str) -> list:
        """Get pending commands for a specific node."""
        return [p for p in self._pending.values() if p.node_id == node_id]


def serialize_error(exc: Exception) -> Dict[str, Any]:
    """Serialize an exception for client feedback.

    Args:
        exc: The exception to serialize

    Returns:
        Dict with error details suitable for JSON response
    """
    error_data = {
        "type": type(exc).__name__,
        "message": str(exc),
    }

    if isinstance(exc, CommandTimeout):
        error_data["command_id"] = exc.command_id
        error_data["action"] = exc.action
        error_data["timeout"] = exc.timeout
    elif isinstance(exc, CommandError):
        error_data["command_id"] = exc.command_id
        error_data["action"] = exc.action
        error_data["client_error"] = exc.error

    return error_data
