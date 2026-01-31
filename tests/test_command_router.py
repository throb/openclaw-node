"""Tests for command router."""

import asyncio
import pytest

from server.command_router import (
    CommandRouter,
    CommandTimeout,
    CommandError,
    serialize_error,
)


class TestCommandRouter:
    """Tests for CommandRouter."""

    def test_init(self):
        """Router initializes with empty pending dict."""
        router = CommandRouter()
        assert router.pending_count == 0

    def test_set_send_func(self):
        """Can set send function."""
        router = CommandRouter()
        router.set_send_func(lambda x, y: None)
        # No assertion needed, just verify no error

    @pytest.mark.asyncio
    async def test_dispatch_no_send_func(self):
        """Dispatch raises error without send function."""
        router = CommandRouter()
        with pytest.raises(ValueError, match="Send function not configured"):
            await router.dispatch("node", "action", {})

    @pytest.mark.asyncio
    async def test_dispatch_and_response(self):
        """Dispatch sends command and awaits response."""
        router = CommandRouter()
        sent_messages = []

        async def mock_send(node_id, message):
            sent_messages.append((node_id, message))
            # Simulate response
            await asyncio.sleep(0.01)
            await router.handle_response({
                "id": message["id"],
                "status": "success",
                "result": {"data": "test"},
            })

        router.set_send_func(mock_send)

        result = await router.dispatch("test-node", "plugin.action", {"param": 1})

        assert len(sent_messages) == 1
        assert sent_messages[0][0] == "test-node"
        assert sent_messages[0][1]["action"] == "plugin.action"
        assert result["status"] == "success"
        assert result["result"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_dispatch_timeout(self):
        """Dispatch raises timeout when no response."""
        router = CommandRouter(default_timeout=0.1)

        async def mock_send(node_id, message):
            pass  # Don't respond

        router.set_send_func(mock_send)

        with pytest.raises(CommandTimeout):
            await router.dispatch("test-node", "plugin.action", {})

    @pytest.mark.asyncio
    async def test_dispatch_error_response(self):
        """Dispatch raises CommandError on error response."""
        router = CommandRouter()

        async def mock_send(node_id, message):
            await asyncio.sleep(0.01)
            await router.handle_response({
                "id": message["id"],
                "status": "error",
                "error": "Something failed",
            })

        router.set_send_func(mock_send)

        with pytest.raises(CommandError, match="Something failed"):
            await router.dispatch("test-node", "plugin.action", {})

    @pytest.mark.asyncio
    async def test_handle_response_unknown_id(self):
        """Handle response returns False for unknown command ID."""
        router = CommandRouter()
        result = await router.handle_response({"id": "unknown-id"})
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_response_no_id(self):
        """Handle response returns False for missing ID."""
        router = CommandRouter()
        result = await router.handle_response({"status": "success"})
        assert result is False

    def test_cancel_pending(self):
        """Cancel pending cancels all commands for a node."""
        router = CommandRouter()

        # Create some pending commands manually
        loop = asyncio.new_event_loop()
        future1 = loop.create_future()
        future2 = loop.create_future()

        from server.command_router import PendingCommand
        from datetime import datetime

        router._pending["cmd1"] = PendingCommand(
            id="cmd1", action="a.b", node_id="node1", future=future1
        )
        router._pending["cmd2"] = PendingCommand(
            id="cmd2", action="c.d", node_id="node1", future=future2
        )

        cancelled = router.cancel_pending("node1")
        assert cancelled == 2
        assert router.pending_count == 0

        loop.close()

    def test_get_pending_for_node(self):
        """Get pending returns commands for specific node."""
        router = CommandRouter()

        loop = asyncio.new_event_loop()
        future = loop.create_future()

        from server.command_router import PendingCommand

        router._pending["cmd1"] = PendingCommand(
            id="cmd1", action="a.b", node_id="node1", future=future
        )

        pending = router.get_pending_for_node("node1")
        assert len(pending) == 1
        assert pending[0].id == "cmd1"

        pending_other = router.get_pending_for_node("node2")
        assert len(pending_other) == 0

        loop.close()


class TestSerializeError:
    """Tests for error serialization."""

    def test_serialize_generic_error(self):
        """Serialize generic exception."""
        error = ValueError("Test error")
        result = serialize_error(error)
        assert result["type"] == "ValueError"
        assert result["message"] == "Test error"

    def test_serialize_command_timeout(self):
        """Serialize CommandTimeout with extra fields."""
        error = CommandTimeout("cmd-123", "plugin.action", 30.0)
        result = serialize_error(error)
        assert result["type"] == "CommandTimeout"
        assert result["command_id"] == "cmd-123"
        assert result["action"] == "plugin.action"
        assert result["timeout"] == 30.0

    def test_serialize_command_error(self):
        """Serialize CommandError with extra fields."""
        error = CommandError("cmd-456", "plugin.action", "Node error")
        result = serialize_error(error)
        assert result["type"] == "CommandError"
        assert result["command_id"] == "cmd-456"
        assert result["client_error"] == "Node error"
