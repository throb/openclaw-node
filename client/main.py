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


def _parse_server_url(url: str) -> tuple[str, str]:
    """Parse server URL into (host, port)."""
    # ws://host:port/ws -> (host, port)
    import re
    match = re.match(r'wss?://([^:/]+):?(\d+)?', url)
    if match:
        host = match.group(1)
        port = match.group(2) or "8765"
        return host, port
    return "", "8765"


def first_run_wizard() -> dict:
    """Interactive first-run setup wizard."""
    print_banner()

    # Try to load existing config
    config_path = get_default_config_path()
    existing_config = {}
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                existing_config = yaml.safe_load(f) or {}
            print("Updating existing configuration\n")
        except Exception:
            pass

    if not existing_config:
        print("First Time Setup\n")

    # Start with defaults, overlay existing
    config = generate_default_config()
    config.update(existing_config)

    # Parse existing server URL for defaults
    existing_host, existing_port = "", "8765"
    if existing_config.get("server_url"):
        existing_host, existing_port = _parse_server_url(existing_config["server_url"])

    # Node ID
    default_id = config.get("node_id", "")
    node_id = input(f"Node ID [{default_id}]: ").strip() or default_id
    config["node_id"] = node_id

    # Server - just IP/hostname
    prompt = f"Server IP or hostname [{existing_host}]: " if existing_host else "Server IP or hostname: "
    while True:
        server = input(prompt).strip() or existing_host
        if not server:
            print("  Required.")
            continue
        break

    # Port with default
    port_input = input(f"Port [{existing_port}]: ").strip()
    port = port_input if port_input else existing_port

    # Build URL
    config["server_url"] = f"ws://{server}:{port}/ws"

    # Auth token
    existing_token = config.get("auth_token", "")
    masked_token = f"{existing_token[:8]}..." if len(existing_token) > 8 else existing_token
    prompt = f"Auth token [{masked_token}]: " if existing_token else "Auth token: "
    while True:
        auth_token = input(prompt).strip()
        if not auth_token and existing_token:
            auth_token = existing_token
            break
        if not auth_token:
            print("  Required.")
            continue
        break
    config["auth_token"] = auth_token

    # Plugin configuration
    print("\n-- Plugins --")
    available_plugins = [
        ("explorer", "File Explorer - open folders, reveal files"),
        ("rv", "RV - media player"),
        ("nuke", "Nuke - compositing"),
        ("resolve", "DaVinci Resolve - editing/color"),
        ("shotgrid", "ShotGrid - production tracking"),
    ]

    existing_plugins = config.get("plugins", [])
    existing_plugin_config = config.get("plugin_config", {})

    enabled_plugins = []
    plugin_config = {}

    for plugin_name, description in available_plugins:
        was_enabled = plugin_name in existing_plugins
        default = "Y" if was_enabled else "n"
        prompt_suffix = f"[{default}]" if was_enabled else "[y/N]"
        enable = input(f"Enable {plugin_name}? ({description}) {prompt_suffix}: ").strip().lower()

        # Determine if enabled
        if was_enabled:
            is_enabled = enable != "n"
        else:
            is_enabled = enable == "y"

        if is_enabled:
            enabled_plugins.append(plugin_name)

            # Ask for custom path for plugins that need executables
            if plugin_name in ("rv", "nuke"):
                existing_path = existing_plugin_config.get(plugin_name, {}).get("path", "")
                if existing_path:
                    custom_path = input(f"  {plugin_name} path [{existing_path}]: ").strip() or existing_path
                else:
                    custom_path = input(f"  {plugin_name} path (blank to auto-detect): ").strip()
                if custom_path:
                    plugin_config[plugin_name] = {"path": custom_path}

    config["plugins"] = enabled_plugins
    if plugin_config:
        config["plugin_config"] = plugin_config

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

    # Load plugins with config
    plugin_config = config.get("plugin_config", {})
    loader = PluginLoader(plugin_config=plugin_config)
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
