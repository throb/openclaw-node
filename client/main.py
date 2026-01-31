#!/usr/bin/env python3
"""OpenClaw Node - Client Entry Point"""

import asyncio
import logging
import platform
import sys
from pathlib import Path

from .config import (
    ConfigError,
    create_config_file,
    generate_default_config,
    get_config_dir,
    get_default_config_path,
    load_config,
)
from .plugin_loader import PluginLoader
from .service import (
    get_service_status,
    install_service,
    start_service,
    stop_service,
    uninstall_service,
)
from .websocket_client import NodeClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner."""
    print("""
╭─────────────────────────────────────────╮
│        OpenClaw Node Client             │
╰─────────────────────────────────────────╯
""")


def test_server_connection(server_url: str, auth_token: str) -> tuple[bool, str]:
    """Test connection to server. Returns (success, message)."""
    import websockets
    import json

    async def _test():
        url = f"{server_url}/test-connection"
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                # Send registration
                await ws.send(json.dumps({
                    "type": "register",
                    "node_id": "test-connection",
                    "plugins": [],
                    "platform": "test",
                }))
                # Wait for ack
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get("type") == "registered":
                    return True, "Connection successful!"
                return False, f"Unexpected response: {data}"
        except asyncio.TimeoutError:
            return False, "Connection timed out"
        except ConnectionRefusedError:
            return False, "Connection refused - is the server running?"
        except Exception as e:
            error_msg = str(e)
            if "4001" in error_msg or "Unauthorized" in error_msg.lower():
                return False, "Authentication failed - check your token"
            return False, f"Connection failed: {error_msg}"

    return asyncio.run(_test())


def first_run_wizard() -> dict:
    """Interactive first-run setup wizard."""
    print_banner()
    print("First Time Setup\n")

    # Generate defaults
    config = generate_default_config()

    # Node ID
    default_id = config["node_id"]
    node_id = input(f"Node ID [{default_id}]: ").strip() or default_id
    config["node_id"] = node_id

    # Server - just IP/hostname
    while True:
        server = input("Server IP or hostname: ").strip()
        if not server:
            print("  Required.")
            continue
        break

    # Port with default
    port_input = input("Port [8765]: ").strip()
    port = port_input if port_input else "8765"

    # Build URL
    config["server_url"] = f"ws://{server}:{port}/ws"

    # Auth token
    while True:
        auth_token = input("Auth token: ").strip()
        if not auth_token:
            print("  Required.")
            continue
        break
    config["auth_token"] = auth_token

    # Test connection
    print(f"\nTesting connection to {config['server_url']}...")
    success, message = test_server_connection(config["server_url"], config["auth_token"])

    if success:
        print(f"  {message}")
    else:
        print(f"  {message}")
        retry = input("\nSave config anyway? [y/N]: ").strip().lower()
        if retry != "y":
            print("Setup cancelled. Run setup again to retry.")
            return config

    # Save config
    config_path = get_default_config_path()
    create_config_file(config_path, config)

    print(f"\nConfig saved to: {config_path}")
    if success:
        print("Run 'openclaw-node' to connect.\n")
    else:
        print("Fix the connection issue and run 'openclaw-node' to connect.\n")

    return config


async def run_client(config: dict):
    """Run the client with given configuration."""
    logger.info(f"Starting node: {config['node_id']}")

    # Load plugins
    loader = PluginLoader()
    plugins = loader.load_all(config.get("plugins", []))
    logger.info(f"Loaded plugins: {list(plugins.keys())}")

    # Create and run client
    client = NodeClient(
        server_url=config["server_url"],
        node_id=config["node_id"],
        auth_token=config["auth_token"],
        plugins=plugins,
        platform_name=config.get("platform", platform.system().lower()),
        heartbeat_interval=config.get("heartbeat_interval", 30),
    )

    await client.run()


def cmd_status():
    """Show service status."""
    status = get_service_status()
    print(f"Service installed: {status['installed']}")
    print(f"Service enabled:   {status['enabled']}")
    print(f"Service running:   {status['running']}")

    config_path = get_default_config_path()
    print(f"\nConfig file: {config_path}")
    print(f"Config exists: {config_path.exists()}")


def cmd_install():
    """Install as system service."""
    config_path = get_default_config_path()
    if not config_path.exists():
        print("No config file found. Running first-time setup...")
        first_run_wizard()

    if install_service():
        print("\nService installed successfully.")
        print("Use 'openclaw-node start' to start the service.")


def cmd_uninstall():
    """Uninstall system service."""
    if uninstall_service():
        print("Service uninstalled successfully.")


def cmd_start():
    """Start the service."""
    if start_service():
        print("Service started.")


def cmd_stop():
    """Stop the service."""
    if stop_service():
        print("Service stopped.")


def main_cli():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenClaw Node Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  (default)   Run client in foreground
  status      Show service status
  install     Install as system service
  uninstall   Remove system service
  start       Start the service
  stop        Stop the service
  setup       Run first-time setup wizard

Examples:
  openclaw-node                    # Run in foreground
  openclaw-node --config my.yaml   # Use custom config
  openclaw-node install            # Install as service
  openclaw-node status             # Check status
""",
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["status", "install", "uninstall", "start", "stop", "setup"],
        help="Service command",
    )
    parser.add_argument(
        "--config", "-c",
        help="Config file path (default: auto-detect)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle commands
    if args.command == "status":
        cmd_status()
        return

    if args.command == "install":
        cmd_install()
        return

    if args.command == "uninstall":
        cmd_uninstall()
        return

    if args.command == "start":
        cmd_start()
        return

    if args.command == "stop":
        cmd_stop()
        return

    if args.command == "setup":
        first_run_wizard()
        return

    # Default: run client
    try:
        config_path = args.config
        config = load_config(config_path)
    except FileNotFoundError:
        if args.config:
            print(f"Error: Config file not found: {args.config}")
            sys.exit(1)
        else:
            # First run - show wizard
            first_run_wizard()
            return
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Run the client
    print_banner()
    print(f"Node ID: {config['node_id']}")
    print(f"Server:  {config['server_url']}")
    print(f"Plugins: {', '.join(config.get('plugins', []))}")
    print()

    try:
        asyncio.run(run_client(config))
    except KeyboardInterrupt:
        print("\nShutting down...")


async def main():
    """Async entry point (for backwards compatibility)."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw Node Client")
    parser.add_argument("--config", "-c", default=None, help="Config file path")
    parser.add_argument("--service", action="store_true", help="Run as background service")
    args = parser.parse_args()

    config = load_config(args.config)
    await run_client(config)


if __name__ == "__main__":
    main_cli()
