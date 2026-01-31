# OpenClaw Node - Client

Python agent that runs on local Windows/Mac workstations, connecting to the VPS and executing plugin actions.

## Tasks

- `clawd-p1u.2.1` - WebSocket client with auto-reconnection
- `clawd-p1u.2.2` - Plugin system architecture
- `clawd-p1u.2.3` - Action whitelist and security
- `clawd-p1u.2.4` - Configuration management
- `clawd-p1u.2.5` - Action executor and response handling
- `clawd-p1u.2.6` - Client CLI and service mode

## Tech Stack

- Python 3.10+
- websockets (async client)
- PyYAML for config

## Installation

```bash
cd client
pip install -r requirements.txt

# Copy and edit config
cp node_config.example.yaml node_config.yaml
```

## Running

```bash
# Foreground
python main.py

# As service (future)
python main.py --service
```
