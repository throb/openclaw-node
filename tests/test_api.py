"""Tests for REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.api import init_api
from server.client_registry import ClientRegistry
from server.command_router import CommandRouter
from server.websocket_server import NodeWebSocketServer


@pytest.fixture
def test_components():
    """Create test server components."""
    ws_server = NodeWebSocketServer()
    registry = ClientRegistry()
    command_router = CommandRouter()
    command_router.set_send_func(ws_server.send)
    init_api(ws_server, registry, command_router)
    return ws_server, registry, command_router


@pytest.fixture
def client(test_components):
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint returns ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "nodes_connected" in data
        assert "pending_commands" in data


class TestNodesEndpoint:
    """Tests for /api/nodes endpoints."""

    def test_list_nodes_empty(self, client):
        """List nodes returns empty list when no nodes connected."""
        response = client.get("/api/nodes")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_nodes_with_node(self, client, test_components):
        """List nodes returns connected nodes."""
        _, registry, _ = test_components
        registry.register("test-node", ["explorer"], "linux")

        response = client.get("/api/nodes")
        assert response.status_code == 200
        nodes = response.json()
        assert len(nodes) == 1
        assert nodes[0]["node_id"] == "test-node"
        assert nodes[0]["plugins"] == ["explorer"]
        assert nodes[0]["platform"] == "linux"

    def test_get_node_not_found(self, client):
        """Get node returns 404 for unknown node."""
        response = client.get("/api/nodes/unknown-node")
        assert response.status_code == 404

    def test_get_node_found(self, client, test_components):
        """Get node returns node details."""
        _, registry, _ = test_components
        registry.register("test-node", ["explorer", "rv"], "darwin")

        response = client.get("/api/nodes/test-node")
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "test-node"
        assert data["plugins"] == ["explorer", "rv"]
        assert data["platform"] == "darwin"


class TestExecEndpoint:
    """Tests for /api/nodes/{id}/exec endpoint."""

    def test_exec_node_not_found(self, client):
        """Exec returns 404 for unknown node."""
        response = client.post(
            "/api/nodes/unknown/exec",
            json={"action": "explorer.ping", "params": {}},
        )
        assert response.status_code == 404

    def test_exec_invalid_action_format(self, client, test_components):
        """Exec returns 400 for invalid action format."""
        _, registry, _ = test_components
        registry.register("test-node", ["explorer"], "linux")

        response = client.post(
            "/api/nodes/test-node/exec",
            json={"action": "invalid_action", "params": {}},
        )
        assert response.status_code == 400
        assert "plugin.action" in response.json()["detail"]

    def test_exec_plugin_not_available(self, client, test_components):
        """Exec returns 400 for unavailable plugin."""
        _, registry, _ = test_components
        registry.register("test-node", ["explorer"], "linux")

        response = client.post(
            "/api/nodes/test-node/exec",
            json={"action": "nuke.render", "params": {}},
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]


class TestPluginsEndpoint:
    """Tests for /api/plugins endpoint."""

    def test_list_plugins_empty(self, client):
        """List plugins returns empty when no nodes connected."""
        response = client.get("/api/plugins")
        assert response.status_code == 200
        assert response.json()["plugins"] == {}

    def test_list_plugins_with_nodes(self, client, test_components):
        """List plugins aggregates from all nodes."""
        _, registry, _ = test_components
        registry.register("node1", ["explorer", "rv"], "linux")
        registry.register("node2", ["explorer", "nuke"], "windows")

        response = client.get("/api/plugins")
        assert response.status_code == 200
        plugins = response.json()["plugins"]
        assert "explorer" in plugins
        assert set(plugins["explorer"]) == {"node1", "node2"}
        assert "rv" in plugins
        assert plugins["rv"] == ["node1"]
        assert "nuke" in plugins
        assert plugins["nuke"] == ["node2"]
