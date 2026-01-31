"""REST API endpoints for OpenClaw Node server."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .client_registry import ClientRegistry, NodeInfo
from .command_router import CommandError, CommandRouter, CommandTimeout, serialize_error
from .websocket_server import NodeWebSocketServer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# These will be set by main.py during initialization
_ws_server: Optional[NodeWebSocketServer] = None
_registry: Optional[ClientRegistry] = None
_command_router: Optional[CommandRouter] = None


def init_api(
    ws_server: NodeWebSocketServer,
    registry: ClientRegistry,
    command_router: CommandRouter,
) -> None:
    """Initialize API with server components."""
    global _ws_server, _registry, _command_router
    _ws_server = ws_server
    _registry = registry
    _command_router = command_router


# Request/Response models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    nodes_connected: int
    pending_commands: int


class NodeSummary(BaseModel):
    node_id: str
    connected_at: str
    plugins: List[str]
    platform: str


class NodeDetail(BaseModel):
    node_id: str
    connected_at: str
    plugins: List[str]
    platform: str
    last_heartbeat: Optional[str]
    pending_commands: int


class ExecRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}
    timeout: Optional[float] = None


class ExecResponse(BaseModel):
    status: str
    command_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


# Endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        nodes_connected=_ws_server.connection_count if _ws_server else 0,
        pending_commands=_command_router.pending_count if _command_router else 0,
    )


@router.get("/nodes", response_model=List[NodeSummary])
async def list_nodes():
    """List all connected nodes."""
    if not _registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    nodes = _registry.list_all()
    return [
        NodeSummary(
            node_id=n.node_id,
            connected_at=n.connected_at.isoformat() + "Z",
            plugins=n.plugins,
            platform=n.platform,
        )
        for n in nodes
    ]


@router.get("/nodes/{node_id}", response_model=NodeDetail)
async def get_node(node_id: str):
    """Get details for a specific node."""
    if not _registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    node = _registry.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    pending = (
        _command_router.get_pending_for_node(node_id) if _command_router else []
    )

    return NodeDetail(
        node_id=node.node_id,
        connected_at=node.connected_at.isoformat() + "Z",
        plugins=node.plugins,
        platform=node.platform,
        last_heartbeat=node.last_heartbeat.isoformat() + "Z" if node.last_heartbeat else None,
        pending_commands=len(pending),
    )


@router.post("/nodes/{node_id}/exec", response_model=ExecResponse)
async def execute_command(node_id: str, request: ExecRequest):
    """Execute a command on a specific node."""
    if not _command_router or not _registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Verify node exists
    node = _registry.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    # Parse and validate action
    if "." not in request.action:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action format: {request.action}. Expected 'plugin.action'",
        )

    plugin_name = request.action.split(".")[0]
    if plugin_name not in node.plugins:
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{plugin_name}' not available on node '{node_id}'. "
                   f"Available: {node.plugins}",
        )

    try:
        result = await _command_router.dispatch(
            node_id=node_id,
            action=request.action,
            params=request.params,
            timeout=request.timeout,
        )

        return ExecResponse(
            status="success",
            command_id=result.get("id"),
            result=result.get("result"),
        )

    except CommandTimeout as e:
        logger.warning(f"Command timeout: {e}")
        return ExecResponse(
            status="timeout",
            command_id=e.command_id,
            error=serialize_error(e),
        )

    except CommandError as e:
        logger.warning(f"Command error: {e}")
        return ExecResponse(
            status="error",
            command_id=e.command_id,
            error=serialize_error(e),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error executing command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins")
async def list_plugins():
    """List all available plugins across all nodes."""
    if not _registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    plugins: Dict[str, List[str]] = {}
    for node in _registry.list_all():
        for plugin in node.plugins:
            if plugin not in plugins:
                plugins[plugin] = []
            plugins[plugin].append(node.node_id)

    return {"plugins": plugins}
