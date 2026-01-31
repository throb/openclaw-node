"""Service installation and management for OpenClaw Node client."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import get_config_dir, get_default_config_path


def get_service_name() -> str:
    """Get service name for current platform."""
    return "openclaw-node"


def get_python_path() -> str:
    """Get path to Python interpreter."""
    return sys.executable


def get_module_command() -> str:
    """Get command to run the client module."""
    return f"{get_python_path()} -m openclaw_node.client"


# ============================================================
# Linux systemd
# ============================================================

def _get_systemd_user_dir() -> Path:
    """Get systemd user unit directory."""
    return Path.home() / ".config" / "systemd" / "user"


def _get_systemd_unit_path() -> Path:
    """Get path to systemd unit file."""
    return _get_systemd_user_dir() / f"{get_service_name()}.service"


def _generate_systemd_unit() -> str:
    """Generate systemd unit file content."""
    config_path = get_default_config_path()

    return f"""[Unit]
Description=OpenClaw Node Client
After=network.target

[Service]
Type=simple
ExecStart={get_python_path()} -m client.main --config {config_path}
Restart=always
RestartSec=10
WorkingDirectory={Path(__file__).parent.parent}

[Install]
WantedBy=default.target
"""


def _install_systemd() -> bool:
    """Install systemd user service."""
    unit_dir = _get_systemd_user_dir()
    unit_dir.mkdir(parents=True, exist_ok=True)

    unit_path = _get_systemd_unit_path()
    unit_path.write_text(_generate_systemd_unit())

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

    print(f"Service installed: {unit_path}")
    print(f"Enable with: systemctl --user enable {get_service_name()}")
    print(f"Start with:  systemctl --user start {get_service_name()}")
    return True


def _uninstall_systemd() -> bool:
    """Uninstall systemd user service."""
    # Stop if running
    subprocess.run(
        ["systemctl", "--user", "stop", get_service_name()],
        capture_output=True,
    )

    # Disable
    subprocess.run(
        ["systemctl", "--user", "disable", get_service_name()],
        capture_output=True,
    )

    # Remove unit file
    unit_path = _get_systemd_unit_path()
    if unit_path.exists():
        unit_path.unlink()

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print("Service uninstalled")
    return True


def _status_systemd() -> dict:
    """Get systemd service status."""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", get_service_name()],
        capture_output=True,
        text=True,
    )
    is_active = result.stdout.strip() == "active"

    result = subprocess.run(
        ["systemctl", "--user", "is-enabled", get_service_name()],
        capture_output=True,
        text=True,
    )
    is_enabled = result.stdout.strip() == "enabled"

    return {
        "installed": _get_systemd_unit_path().exists(),
        "enabled": is_enabled,
        "running": is_active,
    }


def _start_systemd() -> bool:
    """Start systemd service."""
    subprocess.run(["systemctl", "--user", "start", get_service_name()], check=True)
    return True


def _stop_systemd() -> bool:
    """Stop systemd service."""
    subprocess.run(["systemctl", "--user", "stop", get_service_name()], check=True)
    return True


# ============================================================
# macOS launchd
# ============================================================

def _get_launchd_dir() -> Path:
    """Get LaunchAgents directory."""
    return Path.home() / "Library" / "LaunchAgents"


def _get_launchd_plist_path() -> Path:
    """Get path to launchd plist file."""
    return _get_launchd_dir() / f"com.openclaw.node.plist"


def _generate_launchd_plist() -> str:
    """Generate launchd plist content."""
    config_path = get_default_config_path()
    working_dir = Path(__file__).parent.parent

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.node</string>
    <key>ProgramArguments</key>
    <array>
        <string>{get_python_path()}</string>
        <string>-m</string>
        <string>client.main</string>
        <string>--config</string>
        <string>{config_path}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{get_config_dir()}/openclaw-node.log</string>
    <key>StandardErrorPath</key>
    <string>{get_config_dir()}/openclaw-node.error.log</string>
</dict>
</plist>
"""


def _install_launchd() -> bool:
    """Install launchd agent."""
    plist_dir = _get_launchd_dir()
    plist_dir.mkdir(parents=True, exist_ok=True)

    plist_path = _get_launchd_plist_path()
    plist_path.write_text(_generate_launchd_plist())

    print(f"Service installed: {plist_path}")
    print(f"Load with: launchctl load {plist_path}")
    return True


def _uninstall_launchd() -> bool:
    """Uninstall launchd agent."""
    plist_path = _get_launchd_plist_path()

    # Unload if loaded
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    if plist_path.exists():
        plist_path.unlink()

    print("Service uninstalled")
    return True


def _status_launchd() -> dict:
    """Get launchd service status."""
    plist_path = _get_launchd_plist_path()
    installed = plist_path.exists()

    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True,
    )
    running = "com.openclaw.node" in result.stdout

    return {
        "installed": installed,
        "enabled": installed,  # launchd agents are enabled when installed
        "running": running,
    }


def _start_launchd() -> bool:
    """Start launchd service."""
    plist_path = _get_launchd_plist_path()
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    return True


def _stop_launchd() -> bool:
    """Stop launchd service."""
    plist_path = _get_launchd_plist_path()
    subprocess.run(["launchctl", "unload", str(plist_path)], check=True)
    return True


# ============================================================
# Windows Service (via NSSM or Task Scheduler)
# ============================================================

def _get_windows_task_name() -> str:
    """Get Windows Task Scheduler task name."""
    return "OpenClawNode"


def _install_windows() -> bool:
    """Install Windows scheduled task (runs at login)."""
    config_path = get_default_config_path()
    working_dir = Path(__file__).parent.parent

    # Create a VBS wrapper to run without console window
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{get_python_path()}"" -m client.main --config ""{config_path}""", 0, False
'''
    vbs_path = get_config_dir() / "openclaw-node.vbs"
    get_config_dir().mkdir(parents=True, exist_ok=True)
    vbs_path.write_text(vbs_content)

    # Create scheduled task
    cmd = [
        "schtasks", "/create",
        "/tn", _get_windows_task_name(),
        "/tr", f'wscript.exe "{vbs_path}"',
        "/sc", "onlogon",
        "/rl", "highest",
        "/f",  # Force overwrite
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to create task: {result.stderr}")
        return False

    print(f"Service installed as scheduled task: {_get_windows_task_name()}")
    print("Start with: schtasks /run /tn OpenClawNode")
    return True


def _uninstall_windows() -> bool:
    """Uninstall Windows scheduled task."""
    # Stop if running
    subprocess.run(
        ["schtasks", "/end", "/tn", _get_windows_task_name()],
        capture_output=True,
    )

    # Delete task
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", _get_windows_task_name(), "/f"],
        capture_output=True,
        text=True,
    )

    # Remove VBS wrapper
    vbs_path = get_config_dir() / "openclaw-node.vbs"
    if vbs_path.exists():
        vbs_path.unlink()

    print("Service uninstalled")
    return True


def _status_windows() -> dict:
    """Get Windows service status."""
    result = subprocess.run(
        ["schtasks", "/query", "/tn", _get_windows_task_name()],
        capture_output=True,
        text=True,
    )
    installed = result.returncode == 0
    running = "Running" in result.stdout if installed else False

    return {
        "installed": installed,
        "enabled": installed,
        "running": running,
    }


def _start_windows() -> bool:
    """Start Windows service."""
    subprocess.run(
        ["schtasks", "/run", "/tn", _get_windows_task_name()],
        check=True,
    )
    return True


def _stop_windows() -> bool:
    """Stop Windows service."""
    subprocess.run(
        ["schtasks", "/end", "/tn", _get_windows_task_name()],
        check=True,
    )
    return True


# ============================================================
# Cross-platform interface
# ============================================================

def install_service() -> bool:
    """Install the service for the current platform."""
    system = platform.system()

    if system == "Linux":
        return _install_systemd()
    elif system == "Darwin":
        return _install_launchd()
    elif system == "Windows":
        return _install_windows()
    else:
        print(f"Unsupported platform: {system}")
        return False


def uninstall_service() -> bool:
    """Uninstall the service for the current platform."""
    system = platform.system()

    if system == "Linux":
        return _uninstall_systemd()
    elif system == "Darwin":
        return _uninstall_launchd()
    elif system == "Windows":
        return _uninstall_windows()
    else:
        print(f"Unsupported platform: {system}")
        return False


def get_service_status() -> dict:
    """Get service status for the current platform."""
    system = platform.system()

    if system == "Linux":
        return _status_systemd()
    elif system == "Darwin":
        return _status_launchd()
    elif system == "Windows":
        return _status_windows()
    else:
        return {"installed": False, "enabled": False, "running": False}


def start_service() -> bool:
    """Start the service."""
    system = platform.system()

    if system == "Linux":
        return _start_systemd()
    elif system == "Darwin":
        return _start_launchd()
    elif system == "Windows":
        return _start_windows()
    else:
        print(f"Unsupported platform: {system}")
        return False


def stop_service() -> bool:
    """Stop the service."""
    system = platform.system()

    if system == "Linux":
        return _stop_systemd()
    elif system == "Darwin":
        return _stop_launchd()
    elif system == "Windows":
        return _stop_windows()
    else:
        print(f"Unsupported platform: {system}")
        return False
