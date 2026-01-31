#!/usr/bin/env python3
"""OpenClaw Node - WebSocket Server Entry Point"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .api import init_api, router as api_router
from .auth_providers import TokenAuthProvider
from .client_registry import ClientRegistry
from .command_router import CommandRouter
from .websocket_server import NodeWebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Server components (initialized in lifespan)
ws_server: Optional[NodeWebSocketServer] = None
registry: Optional[ClientRegistry] = None
command_router: Optional[CommandRouter] = None
auth_provider: Optional[TokenAuthProvider] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup server components."""
    global ws_server, registry, command_router, auth_provider

    # Initialize components
    ws_server = NodeWebSocketServer()
    registry = ClientRegistry()
    command_router = CommandRouter()
    auth_provider = TokenAuthProvider(
        tokens_file=os.environ.get("OPENCLAW_TOKENS_FILE")
    )

    # Wire up command router to send via websocket server
    command_router.set_send_func(ws_server.send)

    # Initialize API with components
    init_api(ws_server, registry, command_router)

    logger.info("OpenClaw Node server initialized")
    logger.info(f"Auth provider: {auth_provider.name} ({auth_provider.token_count} tokens)")

    yield

    # Cleanup
    logger.info("OpenClaw Node server shutting down")


app = FastAPI(
    title="OpenClaw Node Server",
    description="Remote execution server for VFX pipeline automation",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount API routes
app.include_router(api_router)


@app.websocket("/ws/{node_id}")
async def node_websocket(websocket: WebSocket, node_id: str):
    """WebSocket endpoint for node connections."""
    # 1. Extract token from Authorization header
    auth_header = websocket.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

    # 2. Validate with auth provider
    if not token or not await auth_provider.validate(token):
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning(f"Rejected unauthorized connection for node: {node_id}")
        return

    # 3. Accept and register connection
    await websocket.accept()
    await ws_server.connect(websocket, node_id)

    try:
        # 4. Wait for registration message
        reg_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        if reg_msg.get("type") != "register":
            logger.warning(f"Expected register message, got: {reg_msg.get('type')}")
            await websocket.close(code=4002, reason="Expected register message")
            return

        # 5. Register node info
        plugins = reg_msg.get("plugins", [])
        platform = reg_msg.get("platform", "unknown")
        registry.register(node_id, plugins, platform)

        logger.info(f"Node registered: {node_id} (plugins: {plugins}, platform: {platform})")

        # Send acknowledgment
        await websocket.send_json({
            "type": "registered",
            "node_id": node_id,
        })

        # 6. Message loop - handle responses to commands
        async for message in websocket.iter_json():
            msg_type = message.get("type")

            if msg_type == "heartbeat":
                # Update heartbeat timestamp
                node = registry.get(node_id)
                if node:
                    from datetime import datetime, timezone
                    node.last_heartbeat = datetime.now(timezone.utc)
                continue

            # Assume it's a response to a command
            if "id" in message:
                await command_router.handle_response(message)

    except asyncio.TimeoutError:
        logger.warning(f"Node {node_id} timed out waiting for registration")
        await websocket.close(code=4003, reason="Registration timeout")

    except WebSocketDisconnect:
        logger.info(f"Node {node_id} disconnected")

    except Exception as e:
        logger.exception(f"Error in WebSocket handler for {node_id}: {e}")

    finally:
        await ws_server.disconnect(node_id)
        registry.unregister(node_id)
        cancelled = command_router.cancel_pending(node_id)
        if cancelled:
            logger.info(f"Cancelled {cancelled} pending commands for {node_id}")


def main_cli():
    """CLI entry point."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="OpenClaw Node Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", "-p", type=int, default=8765, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main_cli()
