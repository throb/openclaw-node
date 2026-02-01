"""Configuration management with auto-generation and validation."""

import os
import platform
import secrets
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(Exception):
    """Configuration error with helpful message."""

    def __init__(self, field: str, message: str, hint: Optional[str] = None):
        self.field = field
        self.hint = hint
        full_msg = f"Config error in '{field}': {message}"
        if hint:
            full_msg += f"\n  Hint: {hint}"
        super().__init__(full_msg)


def get_config_dir() -> Path:
    """Get platform-appropriate config directory."""
    system = platform.system()

    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "OpenClaw"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "OpenClaw"
    else:
        # Linux/Unix - use XDG
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(xdg_config) / "openclaw"


def get_default_config_path() -> Path:
    """Get default config file path."""
    return get_config_dir() / "node_config.yaml"


def get_default_node_id() -> str:
    """Generate default node ID from hostname."""
    hostname = socket.gethostname()
    # Clean up hostname for use as ID
    node_id = hostname.lower().replace(" ", "-").replace(".", "-")
    return node_id


def get_platform_defaults() -> Dict[str, Any]:
    """Get platform-specific default settings."""
    system = platform.system().lower()

    defaults = {
        "platform": system,
        "plugins": ["explorer"],  # Always available
    }

    if system == "windows":
        defaults["plugins"].extend(["rv", "resolve", "nuke"])
    elif system == "darwin":
        defaults["plugins"].extend(["rv", "resolve"])
    else:
        defaults["plugins"].extend(["rv"])

    return defaults


def generate_default_config() -> Dict[str, Any]:
    """Generate a default configuration."""
    defaults = get_platform_defaults()

    return {
        "node_id": get_default_node_id(),
        "server_url": "wss://your-server.com:8765/ws",
        "auth_token": f"ocn_{secrets.token_urlsafe(32)}",
        "platform": defaults["platform"],
        "plugins": defaults["plugins"],
        "allowed_paths": [],
        "heartbeat_interval": 30,
    }


def create_config_file(path: Path, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new config file with defaults.

    Args:
        path: Where to write the config
        config: Optional config dict, uses defaults if not provided

    Returns:
        The config dict that was written
    """
    if config is None:
        config = generate_default_config()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write config with comments
    content = f"""# OpenClaw Node Configuration
# Generated automatically - customize as needed

# Unique identifier for this workstation
node_id: {config['node_id']}

# WebSocket server URL (update with your server address)
server_url: {config['server_url']}

# Authentication token (keep this secret!)
# You can also use: ${{OPENCLAW_NODE_TOKEN}}
auth_token: {config['auth_token']}

# Platform (auto-detected)
platform: {config['platform']}

# Enabled plugins
plugins:
{chr(10).join(f'  - {p}' for p in config['plugins'])}
"""

    # Add plugin_config if present
    if config.get('plugin_config'):
        content += "\n# Plugin-specific configuration\nplugin_config:\n"
        for plugin_name, plugin_cfg in config['plugin_config'].items():
            content += f"  {plugin_name}:\n"
            for key, value in plugin_cfg.items():
                # Quote strings that contain backslashes (Windows paths) or special chars
                if isinstance(value, str) and ('\\' in value or ':' in value or ' ' in value):
                    # Use single quotes to avoid backslash escape interpretation
                    content += f"    {key}: '{value}'\n"
                else:
                    content += f"    {key}: {value}\n"

    content += """
# Allowed paths for file operations (security whitelist)
# Leave empty to allow all paths (not recommended for production)
allowed_paths: []

# Heartbeat interval in seconds
heartbeat_interval: {heartbeat}
""".format(heartbeat=config.get('heartbeat_interval', 30))

    with open(path, "w") as f:
        f.write(content)

    return config


def validate_config(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate configuration and return list of errors.

    Returns:
        List of ConfigError objects (empty if valid)
    """
    errors = []

    # Required fields
    required = {
        "node_id": "Unique identifier for this node",
        "server_url": "WebSocket server URL",
        "auth_token": "Authentication token",
    }

    for field, description in required.items():
        if field not in config:
            errors.append(ConfigError(
                field,
                f"Missing required field",
                f"Add '{field}' to your config ({description})",
            ))
        elif not config[field]:
            errors.append(ConfigError(
                field,
                f"Field cannot be empty",
                f"Provide a value for '{field}' ({description})",
            ))

    # Validate server_url format
    if "server_url" in config and config["server_url"]:
        url = config["server_url"]
        if not (url.startswith("ws://") or url.startswith("wss://")):
            errors.append(ConfigError(
                "server_url",
                f"Must start with ws:// or wss://",
                f"Example: wss://your-server.com:8765/ws",
            ))

    # Validate plugins list
    if "plugins" in config:
        if not isinstance(config["plugins"], list):
            errors.append(ConfigError(
                "plugins",
                "Must be a list",
                "plugins:\n  - explorer\n  - rv",
            ))

    # Validate allowed_paths
    if "allowed_paths" in config:
        paths = config["allowed_paths"]
        if paths and not isinstance(paths, list):
            errors.append(ConfigError(
                "allowed_paths",
                "Must be a list of paths",
                "allowed_paths:\n  - /path/to/projects",
            ))
        elif paths:
            for p in paths:
                path = Path(p)
                if not path.is_absolute():
                    errors.append(ConfigError(
                        "allowed_paths",
                        f"Path must be absolute: {p}",
                        "Use full paths like /home/user/projects",
                    ))

    return errors


def _expand_env_vars(obj: Any) -> Any:
    """Recursively expand ${VAR} patterns in strings."""
    if isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            return os.environ.get(var_name, obj)
        return obj
    elif isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    return obj


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file.

    If config doesn't exist and path is the default location,
    creates a new config with defaults.

    Args:
        config_path: Path to config file, or None for default

    Returns:
        Validated configuration dict

    Raises:
        FileNotFoundError: If config file not found (non-default path)
        ConfigError: If validation fails
    """
    if config_path:
        path = Path(config_path)
    else:
        path = get_default_config_path()

    # Check if file exists
    if not path.exists():
        if config_path:
            # Explicit path provided, don't auto-create
            raise FileNotFoundError(f"Config file not found: {config_path}")
        else:
            # Default path, create new config
            return create_config_file(path)

    # Load existing config
    with open(path) as f:
        config = yaml.safe_load(f) or {}

    # Expand environment variables
    config = _expand_env_vars(config)

    # Validate
    errors = validate_config(config)
    if errors:
        # Raise first error
        raise errors[0]

    # Apply platform defaults for missing optional fields
    defaults = get_platform_defaults()
    config.setdefault("platform", defaults["platform"])
    config.setdefault("plugins", defaults["plugins"])
    config.setdefault("heartbeat_interval", 30)
    config.setdefault("allowed_paths", [])

    return config
